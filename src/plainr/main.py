"""
A command line tool to calculate the readability of Plain License licenses compared to their original counterparts.
"""

# sourcery skip: avoid-global-variables
import contextlib
import json
import os
import sys

from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import Enum, StrEnum
from pathlib import Path
from typing import Annotated, Any, Literal, NamedTuple, TypedDict, TypeGuard

import nltk
import readability.scorers as scorers

from cyclopts import App, Parameter, Token
from readability import Readability
from readability.exceptions import ReadabilityException
from rich.console import Console
from rich.json import JSON
from rich.padding import Padding
from rich.table import Table
from rich.text import Text

from plainr.license_content import LicenseContent, LicensePageData, parse_license_file

from plainr._data import get_nltk_data

get_nltk_data()

__version__ = "0.1.0"

IS_CI = bool(os.environ.get("GITHUB_RUN_ID")) or os.environ.get("CI") == "true"

PRINT_PARAMS = {} if IS_CI else {"overflow": "fold", "new_line_start": True, "emoji": True}

console = Console(
    color_system=None if IS_CI else "auto",
    markup=IS_CI,
    highlight=IS_CI,
    force_terminal=not IS_CI,
    no_color=IS_CI,
)

app = App(
    name="plainr",
    help="Calculate the readability of licenses",
    console=console,
    version=__version__,
    version_flags=["--version", "-v"],
    help_on_error=True,
)

def convert_metric_iterable(type_: Any, tokens: Sequence[Token]) -> tuple[ReadabilityMetric, ...]:
    """Convert a list of tokens into a tuple of ReadabilityMetric."""
    assert type_ == tuple[ReadabilityMetric, ...], "Type must be a tuple of ReadabilityMetric."  # noqa: S101
    metrics = []
    if len(tokens) == 1 and tokens[0].value.lower() == "all":
        return tuple(
            v for v in ReadabilityMetric.__members__.values() if v != ReadabilityMetric.ALL
        )  # type: ignore
    for token in tokens:
        if " " in token.value or "," in token.value:
            values = token.value.replace(",", " ").split()
            metrics.extend(
                tuple(ReadabilityMetric.from_name(v.strip()) for v in values if v.strip())
            )
        else:
            metrics.append(ReadabilityMetric.from_name(token.value))
    return tuple(metrics)

class ScoredMetric(NamedTuple):
    """NamedTuple for scored metrics."""
    metric: ReadabilityMetric
    result: IndividualScoreResponseType

    @property
    def normalized_grade(self) -> int | None:
        """Get the normalized grade level from the result."""
        if self.result:
            grade_level = None
            with contextlib.suppress(AttributeError):
                # Some are grade level, others are grade_levels...
                grade_level = self.result.grade_level # type: ignore
                # I know pylance, you hate me for this
            return grade_level or min(*self.result.grade_levels) # type: ignore
        raise ValueError("We don't seem to have anything like 'grade_level' here: ", self.result)


class ReadabilityStats(TypedDict):
    """TypedDict for readability statistics."""
    num_letters: int
    num_words: int
    num_sentences: int
    num_polysyllabic_words: int
    avg_words_per_sentence: float
    avg_syllables_per_word: float

@dataclass(order=True, slots=True)
class Scorer:
    """Dataclass for readability scorer results."""
    # Text to evaluate. If this is not set, the readability object must be set.
    text: Annotated[str, field(default=None, init=True)]
    text_type: TextType
    # if text_type is not TextType.UNKNOWN, this must be set or will raise ValueError
    license_scored: Annotated[LicenseType, field(default=None, compare=True, repr=True)]

    metrics: Annotated[Sequence[ReadabilityMetric], field(default_factory=list, compare=True, repr=True)]

    readability: Annotated[Readability, field(compare=True)]

    results: Annotated[Sequence[ScoredMetric], field(default=None, compare=True, repr=False)]

    _statistics: Annotated[ReadabilityStats, field(default_factory=dict, compare=True, repr=False)]

    _unscored: Annotated[tuple[tuple[ReadabilityMetric, str], ...], field(default_factory=tuple, compare=False, repr=False)]


    def __post_init__(self) -> None:
        """Post-initialization to calculate results."""
        if not self.text and not self.readability:
            raise ValueError(
                "We minimally need text to evaluate or a readability object to evaluate"
            )
        self.text_type = self.text_type or TextType.UNKNOWN
        if self.text_type != TextType.UNKNOWN and not self.license_scored:
            raise ValueError(
                "You need to identify the license scored."
            )
        self.readability = self.readability or Readability(self.text)
        if (_statistics := self.readability.statistics()) and self._is_readabilitystats(_statistics):  # raises if isn't valid, so will not be None
            self._statistics = _statistics
        self.metrics = self._filter_metrics(self.metrics) if self.metrics else [v for v in ReadabilityMetric.__members__.values() if v != ReadabilityMetric.ALL]
        _results = [(metric, self._get_score(metric)) for metric in self.metrics]
        self.results = tuple(
            ScoredMetric(metric, result) for metric, result in _results if result
        )

    def _is_readabilitystats(self, statistics: Any) -> TypeGuard[ReadabilityStats]:
        if all(key for key in statistics if key in ReadabilityStats) and all(
            (
                isinstance(value, float) if key in ("avg_words_per_sentence", "avg_syllables_per_word") else isinstance(value, int)  # type: ignore
            )
            for key, value in statistics.items()
            if key in ReadabilityStats
        ):
            return True
        raise TypeError("Statistic object failed type checking, it isn't a valid `ReadabilityStats` dictionary.")

    def _filter_metrics(self, metrics: Sequence[ReadabilityMetric]) -> tuple[ReadabilityMetric, ...]:
        """Filter out any metrics that are not relevant."""
        words, sentences = self._statistics["num_words"], self._statistics["num_sentences"]
        filtered_metrics = []
        unscored = []
        for metric in metrics:
            match metric.test_minimums:
                case "num_words", min_words if words < min_words:
                    unscored += (metric, f"Minimum words: {min_words} < {words}",)
                case "num_sentences", min_sentences if sentences < min_sentences:
                    unscored += (metric, f"Minimum sentences: {min_sentences} < {sentences}",)
        if not filtered_metrics:
            raise ValueError(
                f"No valid readability metrics for the provided text with {words} words and {sentences} sentences. "
                f"Ensure the text meets the minimum requirements for at least one metric: {', '.join(f'{set(metric.test_minimums[0])} >= {metric.test_minimums[1]}' for metric in metrics)}."
            )
        self._unscored = tuple(sorted(unscored))
        return tuple(filtered_metrics)

    def _get_score(self, metric) -> IndividualScoreResponseType | None:
        """Get the score for a given metric."""
        with contextlib.suppress(ReadabilityException):
            if hasattr(self.readability, metric):
                return getattr(self.readability, metric)()
        return None


def _create_page(license_path: Path) -> LicensePageData:
    """Create a license page data from a license file."""
    return parse_license_file(license_path)


def _get_license(license_name: LicenseType) -> LicenseContent:
    """Get the LicenseContent object for a given license name."""
    try:
        license_path = license_name.path
    except KeyError as e:
        raise ValueError(
            f"License {license_name} not found in available licenses. Must be one of {LicenseType.licenses()}."
        ) from e
    if not license_path:
        raise ValueError(f"License {license_name} not found in available licenses.")
    page = _create_page(license_path)
    return LicenseContent(page)


def _get_license_data(license_name: LicenseType) -> LicenseData:
    """Get the license data for a given license name."""
    license_content = _get_license(license_name)
    plain_text = license_content.plaintext_content
    original_text = license_content.original_plaintext_content
    return LicenseData(
        license=license_content, plain_license_text=plain_text, original_text=original_text
    )


def validate_scores(scores: dict[Any, Any]) -> TypeGuard[Scores]:
    """Validate that all scores are either float or None."""

    def is_value_result_class(key: Metric, value: Any) -> Any:
        """Get the score attribute from a result object."""
        module_type = getattr(scorers, key, None)
        if module_type and (result_type := getattr(module_type, "Result", None)):
            return result_type is type(value)
        return False

    return all((v for k, v in scores.items() if is_value_result_class(k, v)))


def get_score(readability_obj: Readability, metric_name: str) -> IndividualScoreResponseType | None:
    """Get the readability score for a given metric name."""
    if hasattr(readability_obj, metric_name):
        try:
            return getattr(readability_obj, metric_name)()
        except Exception:
            # Some metrics may fail (e.g., SMOG requires 30+ sentences)
            return None
    return None


def format_for_ci(
    pl_scores: Scores, pl_title: str, original_scores: Scores, original_title: str
) -> None:
    """Format the scores for CI output."""
    score_book = {}
    for metric, result in pl_scores.items():
        result_attrs = ReadabilityMetric(metric).result_attrs
        score_book[pl_title][metric] = {attr: getattr(result, attr, None) for attr in result_attrs}
    for metric, result in original_scores.items():
        result_attrs = ReadabilityMetric(metric).result_attrs
        score_book[original_title][metric] = {
            attr: getattr(result, attr, None) for attr in result_attrs
        }
    JSON(json.dumps(score_book))


def _normalize_to_grade_level(scores: Scores, metric: str) -> int | str:
    """Normalize any metric to a simple grade level."""
    result = scores[metric]
    if not result:
        return "N/A"

    # Try to get grade level info in order of preference
    grade_level = None

    # Check for single grade_level first
    if hasattr(result, 'grade_level') and result.grade_level is not None:
        grade_level = result.grade_level
    # Check for multiple grade_levels
    elif hasattr(result, 'grade_levels') and result.grade_levels is not None:
        if isinstance(result.grade_levels, list | tuple) and result.grade_levels:
            # Take the minimum grade level
            grade_level = min(result.grade_levels)
        else:
            grade_level = result.grade_levels

    if grade_level is None:
        return "N/A"

    # Convert to integer, rounding down
    try:
        grade_int = int(float(grade_level)) # type: ignore
        # Cap at college level
        return "college" if grade_int > 12 else grade_int
    except (ValueError, TypeError):
        # Handle string values like "college"
        if isinstance(grade_level, str) and "college" in grade_level.lower():
            return "college"
        return "N/A"

def _get_grade_emoji(grade: int | str) -> str:
    """Get emoji for grade level ranges."""
    if grade == "N/A":
        return "❓"
    if grade == "college":
        return "🎓"
    if isinstance(grade, int):
        if grade <= 5:
            return "🎒"  # Elementary
        if grade <= 8:
            return "📚"  # Middle school
        if grade <= 12:
            return "🏫"  # High school
        return "🎓"  # College
    return "❓"

def _format_grade_display(grade: int | str, *, is_winner: bool = False) -> Text:
    """Format grade level with emoji for display."""
    emoji = _get_grade_emoji(grade)

    if grade == "N/A":
        return Text("❓ N/A", style="dim")
    grade_text = f"{emoji} college" if grade == "college" else f"{emoji} {grade}"
    if is_winner:
        return Text.from_markup(f"[bold green]{grade_text} ⭐[/bold green]")
    return Text(grade_text)


def _determine_winner(
    metric: str, pl_scores: Scores, original_scores: Scores
) -> tuple[str, bool, bool]:
    """Helper to determine the winner for a metric."""
    pl_score = getattr(pl_scores[metric], "score", None)
    original_score = getattr(original_scores[metric], "score", None)

    if pl_score is None or original_score is None:
        return "N/A", False, False

    if metric == "flesch":
        # Higher is better for Flesch
        plain_wins = pl_score > original_score
    else:
        # Lower is better for most metrics
        plain_wins = pl_score < original_score
    winner = "plain" if plain_wins else "original"
    return winner, plain_wins, not plain_wins


def _calculate_grade_difference(metric: str, pl_scores: Scores, original_scores: Scores) -> Text:
    """Calculate the difference in grade levels between plain and original."""
    pl_grade = _normalize_to_grade_level(pl_scores, metric)
    original_grade = _normalize_to_grade_level(original_scores, metric)

    if pl_grade == "N/A" or original_grade == "N/A":
        return Text.from_markup("[dim]N/A[/dim]")

    # Convert to numbers for calculation
    def grade_to_num(grade):
        if grade == "college":
            return 16  # Treat college as grade 16 for calculations
        return grade

    pl_num = grade_to_num(pl_grade)
    orig_num = grade_to_num(original_grade)

    diff = int(pl_num) - int(orig_num)

    if diff == 0:
        return Text.from_markup("[yellow]tie[/yellow]")
    if diff < 0:
        # Plain is better (lower grade level needed)
        grades_better = abs(diff)
        plural = "grade" if grades_better == 1 else "grades"
        return Text.from_markup(f"[bold green]🏆 -{grades_better} {plural}[/bold green]")
    # Original is better
    grades_worse = diff
    plural = "grade" if grades_worse == 1 else "grades"
    return Text.from_markup(f"[red]+{grades_worse} {plural}[/red]")


def _format_winner_indicator(winner: str) -> Text:
    """Format the winner indicator with emojis and styling."""
    if winner == "N/A":
        return Text.from_markup("[dim]N/A[/dim]")
    if winner == "plain":
        return Text.from_markup("[bold green]🏆 Plain License[/bold green]")
    return Text.from_markup("[bold yellow]🏆 Original[/bold yellow]")


def format_for_console(
    pl_scores: Scores, pl_title: str, original_scores: Scores, original_title: str
) -> None:
    """Format the scores for console output with enhanced styling."""
    # Print title with larger, more prominent styling
    console.print()
    console.print(
        Text.from_markup("📊 [bold bright_blue on white] READABILITY COMPARISON [/bold bright_blue on white]"),
        justify="center",
    )
    console.print(
        Text.from_markup(f"[bold bright_green]{pl_title}[/bold bright_green] [bold white]vs[/bold white] [bold bright_yellow]{original_title}[/bold bright_yellow]"),
        justify="center",
    )
    console.print()

    # Create main comparison table with compact layout
    table = Table(
        title="📈 Readability Metrics Comparison",
        title_style="bold bright_cyan",
        show_lines=True,
        border_style="bright_blue",
        header_style="bold white on blue",
    )

    # Add columns for simplified grade-level display
    table.add_column("📋 Metric", justify="left", style="bold cyan", width=16)
    table.add_column(f"🟢 {pl_title[:15]}", justify="center", style="green", width=18)
    table.add_column("🟡 Original", justify="center", style="yellow", width=18)
    table.add_column("📊 Difference", justify="center", style="bold", width=20)

    # Track overall wins and grade totals for averaging
    plain_wins = 0
    original_wins = 0
    total_pl_grades = 0
    total_orig_grades = 0
    valid_metrics = 0

    for metric in pl_scores:
        _, plain_is_winner, original_is_winner = _determine_winner(
            metric, pl_scores, original_scores
        )

        if plain_is_winner:
            plain_wins += 1
        elif original_is_winner:
            original_wins += 1

        # Get normalized grade levels
        pl_grade = _normalize_to_grade_level(pl_scores, metric)
        original_grade = _normalize_to_grade_level(original_scores, metric)

        # Track grades for averaging (skip N/A values)
        if pl_grade != "N/A" and original_grade != "N/A":
            pl_num = 16 if pl_grade == "college" else pl_grade
            orig_num = 16 if original_grade == "college" else original_grade
            total_pl_grades += int(pl_num)
            total_orig_grades += int(orig_num)
            valid_metrics += 1

        # Format grade displays
        pl_grade_display = _format_grade_display(pl_grade, plain_is_winner)
        original_grade_display = _format_grade_display(original_grade, original_is_winner)

        # Calculate consolidated difference
        difference = _calculate_grade_difference(metric, pl_scores, original_scores)

        # Format metric name
        metric_name = metric.replace("_", " ").title()

        table.add_row(
            Text.from_markup(f"[bold]{metric_name}[/bold]"),
            pl_grade_display,
            original_grade_display,
            difference,
        )

    console.print(table)

    # Print grade level averages and summary
    console.print()
    console.rule("📊 [bold bright_cyan]Summary[/bold bright_cyan]")

    if valid_metrics > 0:
        avg_pl_grade = total_pl_grades / valid_metrics
        avg_orig_grade = total_orig_grades / valid_metrics

        # Format average grades
        def format_avg_grade(avg):
            if avg > 12:
                return f"🎓 college ({avg:.1f})"
            rounded = round(avg, 1)
            emoji = _get_grade_emoji(int(rounded))
            return f"{emoji} {rounded}"

        avg_diff = avg_pl_grade - avg_orig_grade
        console.print()
        console.print(
            Text.from_markup("[bold cyan]📈 Average Grade Levels:[/bold cyan]"),
            justify="center"
        )
        console.print(
            f"🟢 {pl_title}: {format_avg_grade(avg_pl_grade)}",
            justify="center"
        )
        console.print(
            f"🟡 {original_title}: {format_avg_grade(avg_orig_grade)}",
            justify="center"
        )

        if avg_diff < 0:
            avg_improvement = abs(avg_diff)
            console.print(
                Text.from_markup(f"[bold green]⬇️  Plain version is {avg_improvement:.1f} grades easier to read![/bold green]"),
                justify="center"
            )
        elif avg_diff > 0:
            console.print(
                Text.from_markup(f"[red]⬆️  Plain version is {avg_diff:.1f} grades harder to read[/red]"),
                justify="center"
            )
        else:
            console.print(
                Text.from_markup("[yellow]📊 Both versions have the same average grade level[/yellow]"),
                justify="center"
            )

    console.print()
    if plain_wins > original_wins:
        summary_style = "bold green"
        winner_icon = "🎉"
        summary_text = f"{pl_title} wins {plain_wins} metrics vs {original_wins}"
    elif original_wins > plain_wins:
        summary_style = "bold yellow"
        winner_icon = "📊"
        summary_text = f"{original_title} wins {original_wins} metrics vs {plain_wins}"
    else:
        summary_style = "bold blue"
        winner_icon = "🤝"
        summary_text = f"It's a tie! Both win {plain_wins} metrics"

    console.print(
        Text.from_markup(f"{winner_icon} [{summary_style}]{summary_text}[/{summary_style}]"),
        justify="center"
    )
    console.print()


def process_scores(unvalidated_pl_scores, unvalidated_original_scores, license_data) -> None:
    """Process the unvalidated scores into a validated Scores object."""
    if not validate_scores(unvalidated_original_scores) or not validate_scores(
        unvalidated_pl_scores
    ):
        raise ValueError(
            "Invalid readability scores. Ensure all scores are valid and of type float or None."
        )
    pl_scores: Scores = unvalidated_pl_scores
    original_scores: Scores = unvalidated_original_scores
    pl_title = license_data["license"].title
    original_title = license_data["license"].get_title(original=True)
    params = (pl_scores, pl_title, original_scores, original_title)
    if IS_CI:
        format_for_ci(*params)
    else:
        format_for_console(*params)


def _filter_metrics(
    metrics: tuple[ReadabilityMetric, ...], words: int, sentences: int
) -> tuple[ReadabilityMetric, ...]:
    """Filter out the ALL metric from the provided metrics."""

    def filter_message(metric: ReadabilityMetric, limit) -> None:
        console.print(
            f"Filtering out {metric.name} due to minimum requirements. {limit}", style="bold red"
        )

    filtered_metrics = []
    for metric in metrics:
        match metric.test_minimums:
            case "num_words", min_words if words < min_words:
                filter_message(metric, f"Minimum words: {min_words}")
            case "num_sentences", min_sentences if sentences < min_sentences:
                filter_message(metric, f"Minimum sentences: {min_sentences}")
            case _:
                filtered_metrics.append(metric)
    if not filtered_metrics:
        raise ValueError(
            f"No valid readability metrics for the provided text with {words} words and {sentences} sentences. "
            f"Ensure the text meets the minimum requirements for at least one metric: {', '.join(f'{set(metric.test_minimums[0])} >= {metric.test_minimums[1]}' for metric in metrics)}."
        )
    return tuple(filtered_metrics)


@app.default
def compare(
    license_name: Annotated[
        LicenseType,
        Parameter(
            required=True,
            help="The name of the license to compare readability for.",
            show_choices=True,
        ),
    ],
    /,
    metrics: Annotated[
        tuple[ReadabilityMetric, ...],
        Parameter(
            name=["-m", "--metrics"],
            help="The readability metrics to compare. Provide a list either as space separated, comma separated without spaces, or as a json list. Defaults to providing `all`, which will use all available metrics.",
            converter=convert_metric_iterable,
            show_choices=True,
            negative=False,
            json_list=True,
            consume_multiple=True,
        ),
    ] = tuple(v for v in ReadabilityMetric.__members__.values() if v != ReadabilityMetric.ALL),
) -> None:
    """Compare the readability of different license texts."""
    license_data = _get_license_data(license_name)
    pl_readability = Readability(license_data["plain_license_text"])
    original_readability = Readability(license_data["original_text"])
    min_words, min_sentences = (
        min(*(r.statistics()["num_words"] for r in (pl_readability, original_readability))),
        min(*(r.statistics()["num_sentences"] for r in (pl_readability, original_readability))),
    )
    metrics = _filter_metrics(metrics, min_words, min_sentences)
    pl_raw_scores = tuple(
        (metric.value, get_score(pl_readability, metric.value)) for metric in metrics
    )
    original_raw_scores = tuple(
        (metric.value, get_score(original_readability, metric.value)) for metric in metrics
    )
    unvalidated_pl_scores = dict(pl_raw_scores)
    unvalidated_original_scores = dict(original_raw_scores)
    process_scores(unvalidated_pl_scores, unvalidated_original_scores, license_data)


@app.command
def about(
    metrics: Annotated[
        tuple[ReadabilityMetric, ...],
        Parameter(
            required=True,
            help="The readability metric or metrics to get information about.",
            show_choices=True,
            converter=convert_metric_iterable,
            negative=False,
            json_list=True,
            consume_multiple=True,
        ),
    ],
    /,
) -> None:
    """Get information about a readability metric or several metrics."""
    if not metrics:
        console.print("No metrics provided. Use --help to see available metrics.", style="bold red")
        return
    for m in metrics:
        about_metric = m.about
        console.rule(f"[bold green]{about_metric.name}")
        text = Padding(about_metric.description, (1, 2, 2, 2), style="yellow")
        console.print(text, **PRINT_PARAMS)  # type: ignore


def main() -> None:
    """Main entry point for the command line interface."""
    try:
        app()
    except Exception:
        console.print_exception(show_locals=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

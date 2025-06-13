from typing import Any

from rich.table import Table
from rich.text import Text

from plainr._console._console import PlainrConsole
from plainr._readability._scorer import ReadabilityComparison
from plainr.config import CONSTANTS
from plainr.types.readability import ReadabilityMetric


console = PlainrConsole()


def deliver_results(compared_licenses: ReadabilityComparison) -> None:
    """Deliver the comparison results based on environment (CI vs console)."""
    text_a_title = f"{compared_licenses.text_a.text_type.name.title()} License"
    text_b_title = f"{compared_licenses.text_b.text_type.name.title()} License"

    if CONSTANTS.is_ci:
        format_for_ci(compared_licenses, text_a_title, text_b_title)
    else:
        format_for_console(compared_licenses, text_a_title, text_b_title)


def format_for_ci(comparison: ReadabilityComparison, text_a_title: str, text_b_title: str) -> None:
    """Format the scores for CI output."""
    score_data = {text_a_title: {}, text_b_title: {}}

    # Process text_a results
    for scored_metric in comparison.text_a.results or []:
        metric_name = scored_metric.metric.value
        result_attrs = scored_metric.metric.result_attrs
        score_data[text_a_title][metric_name] = {
            attr: getattr(scored_metric.result, attr, None) for attr in result_attrs
        }

    # Process text_b results
    for scored_metric in comparison.text_b.results or []:
        metric_name = scored_metric.metric.value
        result_attrs = scored_metric.metric.result_attrs
        score_data[text_b_title][metric_name] = {
            attr: getattr(scored_metric.result, attr, None) for attr in result_attrs
        }

    console.print_json(data=score_data)


def _normalize_to_grade_level(scored_metric: Any) -> int | str:
    """Normalize any metric to a simple grade level."""
    if not scored_metric or not scored_metric.result:
        return "N/A"

    result = scored_metric.result
    # Try to get grade level info in order of preference
    grade_level = None

    # Check for single grade_level first
    if hasattr(result, "grade_level") and result.grade_level is not None:
        grade_level = result.grade_level
    # Check for multiple grade_levels
    elif hasattr(result, "grade_levels") and result.grade_levels is not None:
        if isinstance(result.grade_levels, list | tuple) and result.grade_levels:
            # Take the minimum grade level
            grade_level = min(result.grade_levels)
        else:
            grade_level = result.grade_levels

    if grade_level is None:
        return "N/A"

    # Convert to integer, rounding down
    try:
        grade_int = int(float(grade_level))  # type: ignore
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
    metric: ReadabilityMetric, text_a_metric: Any, text_b_metric: Any
) -> tuple[str, bool, bool]:
    """Helper to determine the winner for a metric."""
    text_a_score = getattr(text_a_metric.result, "score", None) if text_a_metric else None
    text_b_score = getattr(text_b_metric.result, "score", None) if text_b_metric else None

    if text_a_score is None or text_b_score is None:
        return "N/A", False, False

    if metric.value == "flesch":
        # Higher is better for Flesch
        text_a_wins = text_a_score > text_b_score
    else:
        # Lower is better for most metrics
        text_a_wins = text_a_score < text_b_score
    winner = "text_a" if text_a_wins else "text_b"
    return winner, text_a_wins, not text_a_wins


def _calculate_grade_difference(text_a_metric: Any, text_b_metric: Any) -> Text:
    """Calculate the difference in grade levels between text_a and text_b."""
    text_a_grade = _normalize_to_grade_level(text_a_metric)
    text_b_grade = _normalize_to_grade_level(text_b_metric)

    if text_a_grade == "N/A" or text_b_grade == "N/A":
        return Text.from_markup("[dim]N/A[/dim]")

    # Convert to numbers for calculation
    def grade_to_num(grade: int | str) -> int:
        return (
            16 if grade == "college" else int(grade)
        )  # Treat college as grade 16 for calculations

    text_a_num = grade_to_num(text_a_grade)
    text_b_num = grade_to_num(text_b_grade)

    diff = int(text_a_num) - int(text_b_num)

    if diff == 0:
        return Text.from_markup("[yellow]tie[/yellow]")
    if diff < 0:
        # Text A is better (lower grade level needed)
        grades_better = abs(diff)
        plural = "grade" if grades_better == 1 else "grades"
        return Text.from_markup(f"[bold green]🏆 -{grades_better} {plural}[/bold green]")
    # Text B is better
    grades_worse = diff
    plural = "grade" if grades_worse == 1 else "grades"
    return Text.from_markup(f"[red]+{grades_worse} {plural}[/red]")


def format_for_console(
    comparison: ReadabilityComparison, text_a_title: str, text_b_title: str
) -> None:
    """Format the scores for console output with enhanced styling."""
    # Print title with larger, more prominent styling
    console.print()
    console.print(
        Text.from_markup(
            "📊 [bold bright_blue on white] READABILITY COMPARISON [/bold bright_blue on white]"
        ),
        justify="center",
    )
    console.print(
        Text.from_markup(
            f"[bold bright_green]{text_a_title}[/bold bright_green] [bold white]vs[/bold white] [bold bright_yellow]{text_b_title}[/bold bright_yellow]"
        ),
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
    table.add_column(f"🟢 {text_a_title[:15]}", justify="center", style="green", width=18)
    table.add_column(f"🟡 {text_b_title[:15]}", justify="center", style="yellow", width=18)
    table.add_column("📊 Difference", justify="center", style="bold", width=20)

    # Track overall wins and grade totals for averaging
    text_a_wins = 0
    text_b_wins = 0
    total_text_a_grades = 0
    total_text_b_grades = 0
    valid_metrics = 0

    # Create dictionaries for easy lookup
    text_a_results = {sm.metric: sm for sm in comparison.text_a.results or []}
    text_b_results = {sm.metric: sm for sm in comparison.text_b.results or []}

    for metric in comparison.metrics_scored:
        text_a_metric = text_a_results.get(metric)
        text_b_metric = text_b_results.get(metric)

        _, text_a_is_winner, text_b_is_winner = _determine_winner(
            metric, text_a_metric, text_b_metric
        )

        if text_a_is_winner:
            text_a_wins += 1
        elif text_b_is_winner:
            text_b_wins += 1

        # Get normalized grade levels
        text_a_grade = _normalize_to_grade_level(text_a_metric)
        text_b_grade = _normalize_to_grade_level(text_b_metric)

        # Track grades for averaging (skip N/A values)
        if text_a_grade != "N/A" and text_b_grade != "N/A":
            text_a_num = 16 if text_a_grade == "college" else text_a_grade
            text_b_num = 16 if text_b_grade == "college" else text_b_grade
            total_text_a_grades += int(text_a_num)
            total_text_b_grades += int(text_b_num)
            valid_metrics += 1

        # Format grade displays
        text_a_grade_display = _format_grade_display(text_a_grade, is_winner=text_a_is_winner)
        text_b_grade_display = _format_grade_display(text_b_grade, is_winner=text_b_is_winner)

        # Calculate consolidated difference
        difference = _calculate_grade_difference(text_a_metric, text_b_metric)

        # Format metric name
        metric_name = metric.value.replace("_", " ").title()

        table.add_row(
            Text.from_markup(f"[bold]{metric_name}[/bold]"),
            text_a_grade_display,
            text_b_grade_display,
            difference,
        )

    console.print(table)

    # Print grade level averages and summary
    console.print()
    console.rule("📊 [bold bright_cyan]Summary[/bold bright_cyan]")

    if valid_metrics > 0:
        avg_text_a_grade = total_text_a_grades / valid_metrics
        avg_text_b_grade = total_text_b_grades / valid_metrics

        # Format average grades
        def format_avg_grade(avg: float) -> str:
            if avg > 12:
                return f"🎓 college ({avg:.1f})"
            rounded = round(avg, 1)
            emoji = _get_grade_emoji(int(rounded))
            return f"{emoji} {rounded}"

        avg_diff = avg_text_a_grade - avg_text_b_grade
        console.print()
        console.print(
            Text.from_markup("[bold cyan]📈 Average Grade Levels:[/bold cyan]"), justify="center"
        )
        console.print(f"🟢 {text_a_title}: {format_avg_grade(avg_text_a_grade)}", justify="center")
        console.print(f"🟡 {text_b_title}: {format_avg_grade(avg_text_b_grade)}", justify="center")

        if avg_diff < 0:
            avg_improvement = abs(avg_diff)
            console.print(
                Text.from_markup(
                    f"[bold green]⬇️  {text_a_title} is {avg_improvement:.1f} grades easier to read![/bold green]"
                ),
                justify="center",
            )
        elif avg_diff > 0:
            console.print(
                Text.from_markup(
                    f"[red]⬆️  {text_a_title} is {avg_diff:.1f} grades harder to read[/red]"
                ),
                justify="center",
            )
        else:
            console.print(
                Text.from_markup(
                    "[yellow]📊 Both versions have the same average grade level[/yellow]"
                ),
                justify="center",
            )

    console.print()
    if text_a_wins > text_b_wins:
        summary_style = "bold green"
        winner_icon = "🎉"
        summary_text = f"{text_a_title} wins {text_a_wins} metrics vs {text_b_wins}"
    elif text_b_wins > text_a_wins:
        summary_style = "bold yellow"
        winner_icon = "📊"
        summary_text = f"{text_b_title} wins {text_b_wins} metrics vs {text_a_wins}"
    else:
        summary_style = "bold blue"
        winner_icon = "🤝"
        summary_text = f"It's a tie! Both win {text_a_wins} metrics"

    console.print(
        Text.from_markup(f"{winner_icon} [{summary_style}]{summary_text}[/{summary_style}]"),
        justify="center",
    )
    console.print()


__all__ = ("deliver_results",)

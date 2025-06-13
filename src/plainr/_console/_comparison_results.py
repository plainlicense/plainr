from plainr._readability._scorer import ReadabilityComparison
from plainr._console._console import PlainrConsole
from rich.table import Table
from rich.padding import Padding

console = PlainrConsole()


def deliver_results(compared_licenses: ReadabilityComparison) -> None:
    pass

def format_for_ci(
    pl_scores: Scores, pl_title: str, original_scores: Scores, original_title: str
) -> None:
    """Format the scores for CI output."""
    score_book = {}
    for metric, result in pl_scores.items():
        result_attrs = ReadabilityMetric(metric).result_attrs
        score_book[pl_title][metric] = {
            attr: getattr(result, attr, None) for attr in result_attrs
        }
    for metric, result in original_scores.items():
        result_attrs = ReadabilityMetric(metric).result_attrs
        score_book[original_title][metric] = {
            attr: getattr(result, attr, None) for attr in result_attrs
        }
    console.print_json(data=score_book)


def _normalize_to_grade_level(scores: Scores, metric: str) -> int | str:
    """Normalize any metric to a simple grade level."""
    result = scores[metric]
    if not result:
        return "N/A"

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


def _calculate_grade_difference(
    metric: str, pl_scores: Scores, original_scores: Scores
) -> Text:
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
        return Text.from_markup(
            f"[bold green]🏆 -{grades_better} {plural}[/bold green]"
        )
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
        Text.from_markup(
            "📊 [bold bright_blue on white] READABILITY COMPARISON [/bold bright_blue on white]"
        ),
        justify="center",
    )
    console.print(
        Text.from_markup(
            f"[bold bright_green]{pl_title}[/bold bright_green] [bold white]vs[/bold white] [bold bright_yellow]{original_title}[/bold bright_yellow]"
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
        pl_grade_display = _format_grade_display(pl_grade, is_winner=plain_is_winner)
        original_grade_display = _format_grade_display(
            original_grade, is_winner=original_is_winner
        )

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
            justify="center",
        )
        console.print(
            f"🟢 {pl_title}: {format_avg_grade(avg_pl_grade)}", justify="center"
        )
        console.print(
            f"🟡 {original_title}: {format_avg_grade(avg_orig_grade)}", justify="center"
        )

        if avg_diff < 0:
            avg_improvement = abs(avg_diff)
            console.print(
                Text.from_markup(
                    f"[bold green]⬇️  Plain version is {avg_improvement:.1f} grades easier to read![/bold green]"
                ),
                justify="center",
            )
        elif avg_diff > 0:
            console.print(
                Text.from_markup(
                    f"[red]⬆️  Plain version is {avg_diff:.1f} grades harder to read[/red]"
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
        Text.from_markup(
            f"{winner_icon} [{summary_style}]{summary_text}[/{summary_style}]"
        ),
        justify="center",
    )
    console.print()


__all__ = (
    "deliver_results",
)

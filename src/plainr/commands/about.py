"""Get information about a readability measures available in Plainr."""

import sys

from typing import Annotated

from cyclopts import App, Parameter
from rich.padding import Padding

from plainr._console._console import PlainrConsole
from plainr.config import CONSTANTS
from plainr.types.readability import ReadabilityMetric
from plainr.utilities.readability import convert_tokens_to_metrics


console = PlainrConsole()

app = App(console=console)


@app.default
def about(
    metrics: Annotated[
        tuple[ReadabilityMetric, ...],
        Parameter(
            required=True,
            help="The readability metric or metrics to get information about.",
            show_choices=True,
            converter=convert_tokens_to_metrics,
            negative=False,
            json_list=True,
            consume_multiple=True,
        ),
    ],
    /,
) -> None:
    """Get information about a readability metric or several metrics."""
    if not metrics:
        console.print(
            "No metrics provided. Use --help to see available metrics.",
            style="bold red",
        )
        return
    for m in metrics:
        about_metric = m.about
        console.rule(f"[bold green]{about_metric.name}")
        text = Padding(about_metric.description, (1, 2, 2, 2), style="yellow")
        console.print(text, **CONSTANTS.print_params)  # type: ignore


def main() -> None:
    """Run the about command."""
    try:
        app()
    except Exception:
        console.print_exception()
        sys.exit(1)


if __name__ == "__main__":
    main()

__all__ = ("app",)

"""
Compare the readability of Plain License licenses with their original counterparts.
"""

import sys

from typing import Annotated

from cyclopts import App, Parameter

from plainr._console._comparison_results import deliver_results
from plainr._console._console import PlainrConsole
from plainr._data import get_nltk_data
from plainr._licenses import get_license_data
from plainr._readability._scorer import ReadabilityScorer, get_comparison
from plainr.config import CONSTANTS
from plainr.types.licenses import LicenseData, LicenseType, TextType
from plainr.types.readability import ReadabilityMetric
from plainr.utilities.readability import convert_tokens_to_metrics


get_nltk_data()

console = PlainrConsole()

app = App(
    console=console,
    help=f"""Compare the readability of Plain License licenses with their original counterparts against any of {len(ReadabilityMetric.__members__)} readability metrics; or all of them.""",
)

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
            converter=convert_tokens_to_metrics,
            show_choices=True,
            negative=False,
            json_list=True,
            consume_multiple=True,
        ),
    ] = tuple(
        v for v in ReadabilityMetric.__members__.values() if v != ReadabilityMetric.ALL
    ),
) -> None:
    """Compare the readability of different license texts."""
    license_data: LicenseData = get_license_data(license_name)
    plain_license_scores: ReadabilityScorer = ReadabilityScorer(
        text=license_data["plain_license_text"],
        text_type=TextType.PLAIN,
        license_scored=LicenseType.from_value(license_name),
        metrics=metrics
    )
    original_license_scores: ReadabilityScorer = ReadabilityScorer(
        text=license_data["original_text"],
        text_type=TextType.ORIGINAL,
        license_scored=LicenseType.from_value(license_name),
        metrics=metrics
    )
    compared_licenses = get_comparison(plain_license_scores, original_license_scores)
    deliver_results(compared_licenses)


def main() -> None:
    """Main entry point for the compare command."""
    try:
        app()
    except Exception:
        console.print_exception(show_locals=CONSTANTS.is_debug)
        sys.exit(1)


if __name__ == "__main__":
    main()


__all__ = ("app",)

"""
A command line tool to calculate the readability of Plain License licenses compared to their original counterparts.
"""
import sys

from textwrap import dedent

from cyclopts import App

from plainr._console._console import PlainrConsole
from plainr.commands import about_app, compare_app


console = PlainrConsole()

__version__ = "0.1.0"


app = App(
    name="Plainr",
    help=dedent("""
                The **Plain License** CLI tool. Understanding as DevOps.

                - **`plainr compare`** Compare readability of Plain License licenses with their original counterparts against 9 readability metrics.
                - **`plainr about`** Get information about readability metrics.
                - **`plainr score`** Calculate readability scores for any text. [planned]
                - **`plainr init`** Add a Plain License to your project. [planned]
                - **`plainr update`** Update your Plain License to the latest version. [planned]
                - **`plainr action`** Add a Github Action to your project to audit readability and update your Plain License. [planned]
                """).strip(),
    console=PlainrConsole(),
    version=__version__,
    version_flags=["--version", "-v"],
    help_on_error=True,
)

app.command(compare_app)
app.command(about_app)


def main() -> None:
    """Main entry point for the command line interface."""
    try:
        app()
    except Exception:
        console.print_exception(show_locals=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

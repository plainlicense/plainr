"""
Configuration module for plainr. Sets up runtime and config constants for the package.
"""

import os
import sys

from dataclasses import dataclass
from pathlib import Path

from plainr.types.utility import FromMarkupParams, LogLevel, PrintParams


RICH_DEFAULT_PRINT_PARAMS: PrintParams = PrintParams(
    crop=True,
    emoji=None,
    end="\n",
    height=None,
    highlight=True,
    justify="default",
    markup=None,
    new_line_start=False,
    no_wrap=None,
    overflow=None,
    sep=" ",
    soft_wrap=False,
    style=None,
    width=None,
)

RICH_DEFAULT_MARKUP_PARAMS: FromMarkupParams = FromMarkupParams(
    style="", emoji=True, emoji_variant=None, justify=None, overflow=None, end="\n"
)

PLAINR_DEFAULT_MARKUP_PARAMS: FromMarkupParams = {**RICH_DEFAULT_MARKUP_PARAMS, "emoji_variant": "emoji"}


@dataclass(frozen=True)
class CONSTANTS:
    """TypedDict for runtime constants used in plainr."""

    is_ci: bool = (
        bool(os.environ.get("GITHUB_RUN_ID")) or os.environ.get("CI") == "true"
    )

    print_params: PrintParams = (
        RICH_DEFAULT_PRINT_PARAMS
        if is_ci
        else PrintParams(markup=True, emoji=True, soft_wrap=True, new_line_start=True)
    )

    markup_params: FromMarkupParams = PLAINR_DEFAULT_MARKUP_PARAMS

    repo_root = Path(__file__).parent.parent

    is_debug: bool = (
        os.environ.get("PLAINR_DEBUG", "false").lower() in ("true", "1", "yes")
        or os.environ.get("DEBUG", "false").lower() in ("true", "1", "yes")
        or (hasattr(sys, "gettrace") and sys.gettrace() is not None)
    )

    log_level: LogLevel = (
        LogLevel.DEBUG if is_debug else LogLevel.WARNING if is_ci else LogLevel.INFO
    )


__all__ = ("CONSTANTS",)

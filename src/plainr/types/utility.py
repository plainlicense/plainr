"""Utility types for Plainr."""

from enum import IntEnum
from typing import Literal, TypedDict

from rich.console import JustifyMethod, OverflowMethod
from rich.emoji import EmojiVariant
from rich.style import Style


type SepType = Literal[" "] | str  # noqa: PYI051  # We're being explicit.
type EndType = Literal["\n"] | str  # noqa: PYI051  # We're being explicit.

class LogLevel(IntEnum):
    """
    Enum for log levels.
    """

    NONE = 0
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40

    @classmethod
    def from_string(cls, level: str) -> "LogLevel":
        """
        Convert a string to a LogLevel.
        """
        return cls.__members__.get(level.upper(), cls.NONE)

    @classmethod
    def from_value(cls, value: "float | str | LogLevel") -> "LogLevel":
        """
        Convert a number to a LogLevel.
        """
        if isinstance(value, cls):
            return value
        if isinstance(value, str) and value.isdigit():
            value = float(value)
        if value in cls._value2member_map_:
            return cls._value2member_map_[value]  # type: ignore # we really are an Enum type pylance
        clamped = max(0, min(value, cls.ERROR))
        assert isinstance(clamped, (int | float)), (  # noqa: S101 # for type checker; it can't be anything else by now
            "LogLevel must be an integer or float"
        )
        rounded = int(round(clamped / 10.0) * 10)
        return cls._value2member_map_.get(rounded, cls.NONE)  # type: ignore

    def is_same(self, other: object) -> bool:
        """
        Check for approximate equality with another LogLevel or an integer by normalizing the integer to a LogLevel. Set a log level to `1 000 000` if you really want to (it will be clamped to `40`).
        """
        if isinstance(other, LogLevel):
            return self == other
        if isinstance(other, int | float):
            return self == type(self).from_value(other)
        if isinstance(other, str) and other.isdigit():
            return self == type(self).from_value(other)
        return False

class PrintParams(TypedDict, total=False):
    """TypedDict for Rich's Console.print() parameters."""

    sep: SepType | None
    end: EndType | None
    style: str | Style | None
    justify: JustifyMethod | None
    overflow: OverflowMethod | None
    no_wrap: bool | None
    emoji: bool | None
    markup: bool | None
    highlight: bool | None
    width: int | None
    crop: bool | None
    soft_wrap: bool | None
    new_line_start: bool | None
    height: int | None

class FromMarkupParams(TypedDict, total=False):
    """
    TypedDict for parameters used when converting from markup to Text.
    This is used to ensure that the parameters passed to the conversion function
    are correctly typed and documented.
    """

    style: str | Style
    emoji: bool
    emoji_variant: EmojiVariant | None
    justify: JustifyMethod | None
    overflow: OverflowMethod | None
    end: EndType

__all__ = ["FromMarkupParams", "LogLevel", "PrintParams"]

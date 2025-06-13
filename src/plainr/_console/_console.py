"""Rich console for plainr with environment-aware detection and configuration."""

import json
import re

from collections.abc import Generator, Iterable
from typing import Any, TypeGuard, overload, override

from rich.console import Console as Console
from rich.text import Text
from rich.theme import Theme

from plainr.config import CONSTANTS
from plainr.types.utility import FromMarkupParams, PrintParams
from plainr.utilities.type_checking import is_iterable_of_type


MARKUP_PATTERN = re.compile(
    rf"(\[/?[a-z ]{(3,)}\])|(\[link=https?://.[^\]]+\])", re.IGNORECASE
)


class PlainrConsole(Console):
    """A singleton console class for plainr with environment-aware settings."""

    _instance: "PlainrConsole | None" = None

    def __init__(self) -> None:
        """Initialize the console with custom settings."""
        kwargs = {
            "theme": Theme({
                "info": "bold blue",
                "warning": "bold yellow",
                "error": "bold red",
                "success": "bold green",
            }),
            "force_terminal": True,
            "highlight": True,
            "emoji": not CONSTANTS.is_ci,
            "width": 80 if CONSTANTS.is_ci else None,
            "markup": True,
            "soft_wrap": True,
        }

        super().__init__(**kwargs)  # type: ignore

    def __new__(cls) -> "Console":
        """Ensure only one instance of Console is created."""
        if not hasattr(cls, "_instance"):
            cls._instance = super().__new__(cls)
        if not cls._instance:
            raise RuntimeError("Console instance failed to initialize.")
        return cls._instance

    def _is_markup_params(self, kwargs: dict[str, Any]) -> TypeGuard[FromMarkupParams]:
        """Check if the given keyword arguments are suitable for rich markup."""
        return all(key in CONSTANTS.markup_params for key in kwargs) and all(
            key not in CONSTANTS.print_params
            for key in kwargs
            if key not in CONSTANTS.markup_params
        )

    def _set_text_kwargs(self, kwargs: dict[str, Any]) -> FromMarkupParams:
        """Set text-related keyword arguments."""
        kwargs |= CONSTANTS.markup_params
        kwargs = {k: v for k, v in kwargs.items() if k in CONSTANTS.print_params}
        if self._is_markup_params(kwargs):
            return kwargs
        raise ValueError(
            "Keyword arguments do not match the expected markup parameters. ", kwargs
        )

    def _has_markup(self, objs: Any) -> bool:
        """Check if the given objects contain rich markup."""
        if isinstance(objs, str):
            return bool(MARKUP_PATTERN.search(objs))
        return any(isinstance(obj, str) and MARKUP_PATTERN.search(obj) for obj in objs)

    @overload
    def _markup_to_text(
        self, str: str | Text | Iterable[str] | Iterable[Text] | Iterable[Any]
    ) -> tuple[Text, ...]: ...

    @overload
    def _markup_to_text(self, objs: dict[Any, Any]) -> tuple[Text, ...]: ...

    @overload
    def _markup_to_text(self, objs: None) -> tuple: ...

    @overload
    def _markup_to_text(self, objs: Iterable[Any]) -> tuple[Text, ...] | Any: ...

    def _markup_to_text(self, objs: Any, kwargs: FromMarkupParams) -> Any:  # type: ignore
        """Convert markup objects to Text objects."""
        if not objs:
            return ()
        if isinstance(objs, Text) or is_iterable_of_type(objs, Text):
            # If the object is already a Text instance, return it as a tuple
            return (objs,) if isinstance(objs, Text) else tuple(objs)
        if isinstance(objs, str) or is_iterable_of_type(objs, str):
            # If all objects are strings, remove rich markup if in CI
            if CONSTANTS.is_ci:
                objs = (
                    (MARKUP_PATTERN.sub("", objs),)
                    if isinstance(objs, str)
                    else tuple(
                        MARKUP_PATTERN.sub("", obj)
                        for obj in objs
                        if isinstance(obj, str)
                    )
                )
            else:
                return (
                    (Text.from_markup(objs, **kwargs))
                    if isinstance(objs, str)
                    else tuple(
                        Text.from_markup(obj, **kwargs) for obj in objs if isinstance(obj, str)
                    )
                )
        else:
            objs = (
                list(objs)
                if isinstance(objs, list | tuple | set | frozenset | Generator)
                else (list(objs.astuple()) if hasattr(objs, "astuple") else objs)
            )
            try:
                objs = json.dumps(objs, ensure_ascii=False)
                return self._markup_to_text(objs)
            except Exception:
                return objs  # pass on the problem to rich!
        return objs

    @override
    def print( # type: ignore
        self, *objs: Any, **kwargs: PrintParams | FromMarkupParams | None
    ) -> None:  # type: ignore # it really is the same as Console.print
        """
        Print method that handles the console output.

        Converts markup strings to Text objects if not in CI, and removes rich markup if in CI.
        """
        if self._has_markup(objs):
            kwargs = (
                self._set_text_kwargs(kwargs) if kwargs else CONSTANTS.markup_params
            )  # type: ignore
            objs = self._markup_to_text(objs, **kwargs)
        kwargs = CONSTANTS.print_params | {
            k: v for k, v in kwargs.items() if k in CONSTANTS.print_params
        }  # type: ignore
        super().print(*objs, **kwargs)  # type: ignore


__all__ = ("PlainrConsole",)

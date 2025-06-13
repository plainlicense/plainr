"""Utilities for handling readability metrics."""

from collections.abc import Sequence
from typing import Any

from cyclopts import Token

from plainr.types import ReadabilityMetric


def convert_tokens_to_metrics(
    type_: Any, tokens: Sequence[Token]
) -> tuple[ReadabilityMetric, ...]:
    """Convert a list of cyclopts tokens into a tuple of ReadabilityMetric."""
    assert type_ == tuple[ReadabilityMetric, ...], (  # noqa: S101 # for pylance
        "Type must be a tuple of ReadabilityMetric."
    )
    metrics = []
    if len(tokens) == 1 and tokens[0].value.lower() == "all":
        return tuple(
            v
            for v in ReadabilityMetric.__members__.values()
            if v != ReadabilityMetric.ALL
        )  # type: ignore
    for token in tokens:
        if " " in token.value or "," in token.value:
            values = token.value.replace(",", " ").split()
            metrics.extend(
                tuple(
                    ReadabilityMetric.from_name(v.strip()) for v in values if v.strip()
                )
            )
        else:
            metrics.append(ReadabilityMetric.from_name(token.value))
    return tuple(metrics)

__all__ = ("convert_tokens_to_metrics",)

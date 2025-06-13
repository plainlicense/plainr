"""
Provides classes for scoring and comparing readability of texts and licenses.

`Readability Scorer` is a dataclass that represents the results of readability scoring for a given text or license. It processes the text and results, providing a clean interface for accessing readability metrics, scores, and statistics. It also handles the initialization of the readability object and ensures that the text meets the minimum requirements for scoring.

`Readability Comparison` is an immutable dataclass that compares the readability scores between any two texts. It validates the scores, ensures compatibility for comparison, and provides a structured way to access the comparison results. It includes backward compatibility properties for plain vs original license comparisons.
"""

import contextlib

from collections.abc import Sequence
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Annotated, Any, Literal, TypeGuard, cast

from readability import Readability
from readability.exceptions import ReadabilityException

from plainr.types.licenses import LicenseType, TextType
from plainr.types.readability import (
    GradedScoredMetric,
    IndividualScoreResponseType,
    ReadabilityMetric,
    ReadabilityStats,
    ScoredMetric,
)


@dataclass(order=True, slots=True)
class ReadabilityScorer:
    """Dataclass for readability scorer results."""

    text_type: TextType
    # if text_type is not TextType.UNKNOWN, this must be set or will raise ValueError

    readability: Annotated[Readability | None, field(compare=True, kw_only=True)] = None

    # Text to evaluate. If this is not set, the readability object must be set.
    text: str | None = None

    license_scored: Annotated[
        LicenseType | None, field(default=None, compare=True, repr=True)
    ] = None

    metrics: Annotated[
        Sequence[ReadabilityMetric] | None,
        field(default_factory=list, compare=True, repr=True),
    ] = None

    results: Annotated[
        Sequence[ScoredMetric] | None,
        field(default=None, compare=True, repr=False, kw_only=True),
    ] = None

    _statistics: Annotated[
        ReadabilityStats | None,
        field(default_factory=dict, compare=True, repr=False, kw_only=True),
    ] = None

    _unscored: Annotated[
        tuple[tuple[ReadabilityMetric, str], ...] | None,
        field(default_factory=tuple, compare=False, repr=False, kw_only=True),
    ] = None

    def __post_init__(self) -> None:
        """Post-initialization to calculate results."""
        if not self.text and not self.readability:
            raise ValueError(
                "We minimally need text to evaluate or a readability object to evaluate"
            )
        self.text_type = self.text_type or TextType.UNKNOWN
        if self.text_type != TextType.UNKNOWN and not self.license_scored:
            raise ValueError("You need to identify the license scored.")
        self.readability = self.readability or Readability(self.text)
        if (_statistics := self.readability.statistics()) and self._is_readabilitystats(
            _statistics
        ):  # raises if isn't valid, so will not be None
            self._statistics = _statistics
        self.metrics = (
            self._filter_metrics(self.metrics)
            if self.metrics
            else [
                v
                for v in ReadabilityMetric.__members__.values()
                if v != ReadabilityMetric.ALL
            ]
        )
        _results = [(metric, self._get_score(metric)) for metric in self.metrics]
        self.results = tuple(
            ScoredMetric(metric, result) for metric, result in _results if result
        )

    def _is_readabilitystats(self, statistics: Any) -> TypeGuard[ReadabilityStats]:
        if all(key for key in statistics if key in ReadabilityStats) and all(
            (
                isinstance(value, float)
                if key in ("avg_words_per_sentence", "avg_syllables_per_word")
                else isinstance(value, int)  # type: ignore
            )
            for key, value in statistics.items()
            if key in ReadabilityStats
        ):
            return True
        raise TypeError(
            "Statistic object failed type checking, it isn't a valid `ReadabilityStats` dictionary."
        )

    def _filter_metrics(
        self, metrics: Sequence[ReadabilityMetric]
    ) -> tuple[ReadabilityMetric, ...]:
        """Filter out any metrics that are not relevant."""
        words, sentences = (
            self._statistics["num_words"],  # type: ignore # would have raised before this if None
            self._statistics["num_sentences"],  # type: ignore # would have raised before this if None
        )
        filtered_metrics = []
        unscored = []
        for metric in metrics:
            match metric.test_minimums:
                case "num_words", min_words if words < min_words:
                    unscored += (metric, f"Minimum words: {min_words} < {words}")
                case "num_sentences", min_sentences if sentences < min_sentences:
                    unscored += (
                        metric,
                        f"Minimum sentences: {min_sentences} < {sentences}",
                    )
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

    @property
    def unscored_metrics(self) -> tuple[tuple[ReadabilityMetric, str], ...]:
        """Get the unscored metrics."""
        return self._unscored or ()

    @property
    def graded_scores(self) -> tuple[GradedScoredMetric, ...]:
        """Get the results with normalized grade levels as `GradedScoreMetric`."""
        return tuple(GradedScoredMetric.from_score(score) for score in self.results)  # type: ignore # we've already verified it isn't known in post_init


@dataclass(order=True, slots=True, frozen=True)
class ReadabilityComparison:
    """
    Dataclass for comparing readability scores between any two texts.

    While it *doesn't really matter* which text is text_a or text_b, for consistency, when the text is a license, text_a should be the plain license and text_b should be the original license. Similarly, "new" vs. "old" text comparisons should follow the same convention, where text_a is the "new" text and text_b is the "old" text.
    """

    text_a: ReadabilityScorer
    text_b: ReadabilityScorer
    metrics_scored: Annotated[
        tuple[ReadabilityMetric, ...],
        field(default_factory=tuple, compare=True, repr=True),
    ]
    unscored_metrics: Annotated[
        tuple[tuple[ReadabilityMetric, str], ...],
        field(default_factory=tuple, compare=False, repr=False),
    ]

    def __post_init__(self) -> None:
        """Post-initialization to validate the comparison."""
        self._validate_self()

    def _validate_self(self) -> None:
        """Validate the comparison results."""
        if not isinstance(self.text_a, ReadabilityScorer):
            raise TypeError("Text A scores must be a ReadabilityScorer instance.")
        if not isinstance(self.text_b, ReadabilityScorer):
            raise TypeError("Text B scores must be a ReadabilityScorer instance.")
        # Only validate license matching if both texts are associated with licenses
        if (
            self.text_a.license_scored is not None
            and self.text_b.license_scored is not None
            and self.text_a.license_scored != self.text_b.license_scored
        ):
            raise ValueError(
                "When comparing licensed texts, both must be for the same license type. Received: "
                f"{self.text_a.license_scored} and {self.text_b.license_scored}."
            )
        if not self.metrics_scored:
            raise ValueError(
                "No metrics scored. Ensure that at least one metric is provided for comparison."
            )

    @property
    def scored_text(self) -> tuple[str, str]:
        """Get the scored texts for both texts."""
        return (self.text_a.text or "", self.text_b.text or "")

    @property
    def data(
        self,
    ) -> MappingProxyType[
        Literal["text_a", "text_b", "metrics_scored", "unscored_metrics"],
        ReadabilityScorer
        | tuple[ReadabilityMetric, ...]
        | tuple[tuple[ReadabilityMetric, str], ...],
    ]:
        """Get the comparison data as an immutable mapping (readonly dict)."""
        return MappingProxyType({
            "text_a": self.text_a,
            "text_b": self.text_b,
            "metrics_scored": self.metrics_scored,
            "unscored_metrics": self.unscored_metrics,
        })

    @property
    def text_types(self) -> tuple[TextType, TextType]:
        """Get the text types for both texts."""
        return (self.text_a.text_type, self.text_b.text_type)

    @property
    def license(self) -> LicenseType | Literal[False]:
        """Get the license type that was scored (if both texts are licenses)."""
        return self.text_a.license_scored if self.text_a.license_scored == self.text_b.license_scored and self.text_a.license_scored else False


def _validate_readability_scorer(scorer: ReadabilityScorer) -> None:
    """Validate the ReadabilityScorer instance."""
    if not isinstance(scorer, ReadabilityScorer):
        raise TypeError("Expected a ReadabilityScorer instance.")
    if not isinstance(scorer.metrics, Sequence):
        raise TypeError("Expected metrics to be a sequence.")
    if not all(isinstance(metric, ReadabilityMetric) for metric in scorer.metrics):
        raise TypeError("All metrics must be ReadabilityMetric instances.")


def get_comparison(
    text_a: ReadabilityScorer, text_b: ReadabilityScorer
) -> ReadabilityComparison:
    """
    Get a comparison of the readability scores between any two texts.

    Creates a `ReadabilityComparison` instance that contains the scores for both texts.
    It first validates the readability scorers and resolves differences in metrics scored.
    If the metrics differ, it creates new `ReadabilityScorer` instances with the union of the metrics.

    Args:
        text_a: First ReadabilityScorer instance to compare
        text_b: Second ReadabilityScorer instance to compare

    Returns:
        ReadabilityComparison instance with the comparison results
    """
    # Union of all metrics considered by both
    _validate_readability_scorer(text_a)
    _validate_readability_scorer(text_b)
    text_a_metrics = cast(Sequence[ReadabilityMetric], text_a.metrics)
    text_b_metrics = cast(Sequence[ReadabilityMetric], text_b.metrics)
    all_metrics = set(text_a_metrics) | set(text_b_metrics)
    # Union of all unscored metrics (as (metric, reason) tuples)
    all_unscored = set(text_a.unscored_metrics) | set(text_b.unscored_metrics)
    # The set of metrics that were scored by both (i.e., not in unscored)
    scored_metrics = tuple(
        sorted(
            metric
            for metric in all_metrics
            if all(metric != unscored[0] for unscored in all_unscored)
        )
    )
    # If the metrics differ, we need new scorer instances with the scored metrics
    if len(scored_metrics) != len(text_a_metrics):
        text_a = ReadabilityScorer(
            text=text_a.text,
            text_type=text_a.text_type,
            license_scored=text_a.license_scored,
            metrics=scored_metrics,
            readability=text_a.readability,
        )
    if len(scored_metrics) != len(text_b_metrics):
        text_b = ReadabilityScorer(
            text=text_b.text,
            text_type=text_b.text_type,
            license_scored=text_b.license_scored,
            metrics=scored_metrics,
            readability=text_b.readability,
        )
    return ReadabilityComparison(
        text_a=text_a,
        text_b=text_b,
        metrics_scored=scored_metrics,
        unscored_metrics=tuple(sorted(all_unscored)),
    )

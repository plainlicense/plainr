"""Types for plainr's readability functionality."""
from pathlib import Path
from typing import (NamedTuple, Literal, TypedDict, TypeGuard, Any)
from enum import StrEnum
from readability import scorers
from readability import Readability


type Metric = Literal[
    "ari",
    "coleman_liau",
    "dale_chall",
    "flesch",
    "flesch_kincaid",
    "gunning_fog",
    "linsear_write",
    "smog",
    "spache",
]

type IndividualScoreResponseType = type[
    scorers.ARI
    | scorers.ColemanLiau
    | scorers.DaleChall
    | scorers.Flesch
    | scorers.FleschKincaid
    | scorers.GunningFog
    | scorers.LinsearWrite
    | scorers.Smog
    | scorers.Spache
]

type AllScoreResponseType = tuple[
    type[scorers.ARI],
    type[scorers.ColemanLiau],
    type[scorers.DaleChall],
    type[scorers.Flesch],
    type[scorers.FleschKincaid],
    type[scorers.GunningFog],
    type[scorers.LinsearWrite],
    type[scorers.Smog],
    type[scorers.Spache],
]

type ScorerResponseType = IndividualScoreResponseType | AllScoreResponseType


def validate_metrics_members(
    members: dict[str, Any | None],
) -> TypeGuard[dict[str, tuple[str]]]:
    """Validate that all members have alternative names."""
    for metric, other_names in members.items():
        if not other_names:
            raise ValueError(f"Metric {metric} does not have alternative names.")
        if not isinstance(other_names, tuple):
            raise TypeError(
                f"Alternative names for {metric} must be a tuple, got {type(other_names)}."
            )
        if not all(isinstance(name, str) for name in other_names):
            raise TypeError(f"All alternative names for {metric} must be strings.")
    return True


class Scores(TypedDict, total=False):
    """TypedDict for readability scores."""

    ari: scorers.ari.Result | None
    coleman_liau: scorers.coleman_liau.Result | None
    dale_chall: scorers.dale_chall.Result | None
    flesch: scorers.flesch.Result | None
    flesch_kincaid: scorers.flesch_kincaid.Result | None
    gunning_fog: scorers.gunning_fog.Result | None
    linsear_write: scorers.linsear_write.Result | None
    smog: scorers.smog.Result | None
    spache: scorers.spache.Result | None


class AboutMetric(NamedTuple):
    """NamedTuple for metric description."""

    name: str
    description: str


class ReadabilityMetric(StrEnum):
    """Enum for readability metrics."""

    ARI = "ari"
    COLEMAN_LIAU = "coleman_liau"
    DALE_CHALL = "dale_chall"
    FLESCH = "flesch"
    FLESCH_KINCAID = "flesch_kincaid"
    GUNNING_FOG = "gunning_fog"
    LINSEAR_WRITE = "linsear_write"
    SMOG = "smog"
    SPACHE = "spache"

    ALL = "all"

    def __str__(self) -> str:
        """Return the string representation of the readability metric."""
        return self.value

    @property
    def other_names(self) -> tuple[str, ...]:
        """Return alternative names for the readability metric."""
        return self._generate_metric_names(self.value)

    @staticmethod
    def _generate_metric_names(k: str) -> tuple[str, ...]:
        """Generate alternative names for a readability metric."""
        names = [k, f"{k}_metrics"] if k == "all" else [k]
        if any("_" in name for name in names):
            new_names = []
            for name in names:
                if "_" in name:
                    new_names.extend((
                        name.replace("_", " "),
                        name.replace("_", "-"),
                        "".join(n[0] for n in name.split("_") if n and n[0].isalpha()),
                    ))
            names.extend(new_names)
        elif k in {"smog", "spache"}:
            names.append(k[:1])
        else:
            names.append(k[0])
        if k in {"coleman_liau", "dale_chall", "gunning_fog", "linsear_write"}:
            names.append(k[0])
        return tuple(
            sorted({
                n
                for name in names
                for n in (name.lower(), name.upper(), name.title())
                if name and n
            })
        )

    def _all_scorers(self) -> AllScoreResponseType:
        """Return all scorer classes for the readability metric."""
        return (
            scorers.ARI,
            scorers.ColemanLiau,
            scorers.DaleChall,
            scorers.Flesch,
            scorers.FleschKincaid,
            scorers.GunningFog,
            scorers.LinsearWrite,
            scorers.Smog,
            scorers.Spache,
        )

    @property
    def scorer(self) -> ScorerResponseType:
        """Return the scorer class for the readability metric."""
        if self == ReadabilityMetric.ALL:
            return self._all_scorers()
        scorer_map = {
            ReadabilityMetric.ARI: scorers.ARI,
            ReadabilityMetric.COLEMAN_LIAU: scorers.ColemanLiau,
            ReadabilityMetric.DALE_CHALL: scorers.DaleChall,
            ReadabilityMetric.FLESCH: scorers.Flesch,
            ReadabilityMetric.FLESCH_KINCAID: scorers.FleschKincaid,
            ReadabilityMetric.GUNNING_FOG: scorers.GunningFog,
            ReadabilityMetric.LINSEAR_WRITE: scorers.LinsearWrite,
            ReadabilityMetric.SMOG: scorers.Smog,
            ReadabilityMetric.SPACHE: scorers.Spache,
        }
        return scorer_map[self]

    @property
    def test_minimums(self) -> tuple[Literal["num_words", "num_sentences"], int]:
        """Return the minimum required input for the readability metric."""
        if self == ReadabilityMetric.SMOG:
            return "num_sentences", 30
        return "num_words", 100

    @classmethod
    def other_names_map(cls) -> dict[str, tuple[str, ...]]:
        """Return a map of readability metrics to their alternative names."""
        members = {k: v.other_names for k, v in cls.__members__.items()}
        if not validate_metrics_members(members):
            raise ValueError("Invalid readability metrics members.")
        return members

    @classmethod
    def from_name(cls, name: str) -> "ReadabilityMetric":
        """Return the ReadabilityMetric from a string name."""
        for member_name, names in cls.other_names_map().items():
            if name in names:
                return cls.__members__[member_name]
        raise ValueError(
            f"Invalid readability metric: {name}. Must be one of {cls.metrics()} or their alternative names: {[name for metric in cls for name in metric.other_names]}."
        )

    @classmethod
    def metrics(cls) -> list[str]:
        """Return a list of all readability metrics."""
        return sorted(cls.__members__.keys())

    @classmethod
    def readability_map(cls) -> dict["ReadabilityMetric", str]:  # type: ignore
        """Return a map of readability metrics to their function names."""
        return {
            v: k for k, v in cls._value2member_map_.items() if hasattr(Readability, k)
        }  # type: ignore

    @property
    def names(self) -> tuple[str, ...] | str:
        """Return the values of the readability metric."""
        return (
            tuple(k for k in ReadabilityMetric.__members__ if k != "ALL")
            if self == ReadabilityMetric.ALL
            else self.name
        )

    @property
    def about(self) -> AboutMetric:
        """Return the description of the readability metric."""
        return {
            # These are taken in large part from py-readability-metrics' README file.
            # (C) 2018 Carmine M. DiMascio and licensed under the MIT License.
            ReadabilityMetric.ARI: AboutMetric(
                name="Automated Readability Index",
                description="Unlike the other indices, the ARI, along with the Coleman-Liau, relies on a factor of characters per word, instead of the usual syllables per word. ARI is widely used on all types of texts.",
            ),
            ReadabilityMetric.COLEMAN_LIAU: AboutMetric(
                name="Coleman-Liau Index",
                description="The Coleman-Liau index is a readability test designed to gauge the understandability of English texts. The Coleman-Liau Formula usually gives a lower grade value than any of the Kincaid, ARI and Flesch values when applied to technical documents.",
            ),
            ReadabilityMetric.DALE_CHALL: AboutMetric(
                name="Dale-Chall Readability Score",
                description="The Dale-Chall Formula is an accurate readability formula for the simple reason that it is based on the use of familiar words, rather than syllable or letter counts. Reading tests show that readers usually find it easier to read, process and recall a passage if they find the words familiar. The Dale-Chall formula is based on a list of 3,000 familiar words, which were selected by a group of 4th grade students. The formula is designed to be used with texts that are written for an audience of 4th grade or higher.",
            ),
            ReadabilityMetric.FLESCH: AboutMetric(
                name="Flesch Reading Ease",
                description="The U.S. Department of Defense uses the Reading Ease test as the standard test of readability for its documents and forms. Florida requires that life insurance policies have a Flesch Reading Ease score of 45 or greater.",
            ),
            ReadabilityMetric.FLESCH_KINCAID: AboutMetric(
                name="Flesch-Kincaid Grade Level",
                description="The U.S. Army uses Flesch-Kincaid Grade Level for assessing the difficulty of technical manuals. The commonwealth of Pennsylvania uses Flesch-Kincaid Grade Level for scoring automobile insurance policies to ensure their texts are no higher than a ninth grade level of reading difficulty. Many other U.S. states also use Flesch-Kincaid Grade Level to score other legal documents such as business policies and financial forms.",
            ),
            ReadabilityMetric.GUNNING_FOG: AboutMetric(
                name="Gunning Fog Index",
                description="The Gunning fog index measures the readability of English writing. The index estimates the years of formal education needed to understand the text on a first reading. A fog index of 12 requires the reading level of a U.S. high school senior (around 18 years old).",
            ),
            ReadabilityMetric.LINSEAR_WRITE: AboutMetric(
                name="Linsear Write Formula",
                description="Linsear Write is a readability metric for English text, purportedly developed for the United States Air Force to help them calculate the readability of their technical manuals.",
            ),
            ReadabilityMetric.SMOG: AboutMetric(
                name="Simple Measure of Gobbledygook Index",
                description="The SMOG Readability Formula is a popular method to use on health literacy materials.",
            ),
            ReadabilityMetric.SPACHE: AboutMetric(
                name="Spache Readability Formula",
                description="The Spache Readability Formula is used for Primary-Grade Reading Materials, published in 1953 in The Elementary School Journal. The Spache Formula is best used to calculate the difficulty of text that falls at the 3rd grade level or below.",
            ),
        }[self]

    @property
    def result_attrs(self) -> tuple[str, ...]:
        """Return the attributes of the result object for the readability metric."""
        if self == ReadabilityMetric.ALL:
            raise ValueError(
                "ALL is not a valid readability metric. Get the property of each type."
            )
        match self:
            case ReadabilityMetric.ARI:
                return ("score", "grade_levels", "ages")
            case ReadabilityMetric.DALE_CHALL:
                return ("score", "grade_levels")
            case ReadabilityMetric.FLESCH:
                return ("score", "grade_levels", "ease")
            case (
                ReadabilityMetric.COLEMAN_LIAU
                | ReadabilityMetric.GUNNING_FOG
                | ReadabilityMetric.FLESCH_KINCAID
                | ReadabilityMetric.LINSEAR_WRITE
                | ReadabilityMetric.SMOG
                | ReadabilityMetric.SPACHE
            ):
                return ("score", "grade_level")

class ScoredMetric(NamedTuple):
    """NamedTuple for scored metrics."""

    metric: ReadabilityMetric
    result: IndividualScoreResponseType

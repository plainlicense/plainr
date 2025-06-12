from pathlib import Path
from typing import Any, NamedTuple, TypeGuard, Annotated, TypedDict
from enum import StrEnum, Enum
from plainr._data import REPO_ROOT

class LicenseData(TypedDict):
    """TypedDict for license data."""

    license: LicenseContent
    plain_license_text: str
    original_text: str


class TextType(Enum):
    """Enum for text types."""

    UNKNOWN = 0
    PLAIN = 1
    ORIGINAL = 2

    def __str__(self) -> str:
        """Return the string representation of the text type."""
        return {
            TextType.UNKNOWN: "unknown",
            TextType.PLAIN: "Plain License",
            TextType.ORIGINAL: "original license",
        }[self]


class LicenseType(StrEnum):
    """Enum for license types."""

    MPL = "mpl"
    MIT = "mit"
    ELASTIC = "elastic"
    UNLICENSE = "unlicense"

    @property
    def spdx_id(self) -> str:
        """Return the SPDX ID for the license type."""
        return {
            LicenseType.MPL: "mpl-2.0",
            LicenseType.MIT: "mit",
            LicenseType.ELASTIC: "elastic-2.0",
            LicenseType.UNLICENSE: "unlicense",
        }[self]

    @property
    def category(self) -> str:
        """Return the category of the license type."""
        return {
            LicenseType.MPL: "copyleft",
            LicenseType.MIT: "permissive",
            LicenseType.ELASTIC: "source-available",
            LicenseType.UNLICENSE: "public-domain",
        }[self]

    @property
    def root_path(self) -> Path:
        """Return the root path for the license type."""
        return REPO_ROOT / "docs" / "licenses" / self.category / self.spdx_id

    @property
    def path(self) -> Path:
        """Return the path to the license file."""
        return (
            self.root_path / "index.md" if self.root_path.is_dir() else self.root_path
        )

    @classmethod
    def licenses(cls) -> list[str]:
        """Return a list of all license names."""
        return sorted(cls.__members__.keys())

    @classmethod
    def from_value(cls, value: str) -> "LicenseType":
        """Return the LicenseType from a string value."""
        value = value.strip().lower()
        if value in cls.licenses():
            return cls(value)
        if value in (ids := [license_type.spdx_id for license_type in cls]):
            return cls(ids.index(value))
        raise ValueError(
            f"Invalid license type: {value}. Must be one of {cls.licenses()} or their SPDX IDs: {[license_type.spdx_id for license_type in cls]}."
        )

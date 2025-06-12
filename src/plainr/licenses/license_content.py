# sourcery skip: avoid-global-variables, do-not-use-staticmethod, no-complex-if-expressions, no-relative-imports
"""
Standalone license factory that works without mkdocs dependencies.
Streamlined version for CLI tools - contains only functions needed for readability analysis.
"""
# ===========================================================================

import re

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from re import Pattern
from textwrap import dedent
from typing import Any, ClassVar

import ez_yaml


@dataclass
class LicensePageData:
    """Simple data class to replace mkdocs Page object."""
    meta: dict[str, Any]
    markdown: str | None = None
    title: str | None = None
    url: str = ""


def parse_license_file(file_path: Path) -> LicensePageData:
    """Parse a license file and extract frontmatter and content."""
    if not file_path.exists():
        raise FileNotFoundError(f"License file {file_path} does not exist")

    content = file_path.read_text(encoding="utf-8")

    # Extract YAML frontmatter
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            frontmatter_yaml = parts[1].strip()
            markdown_content = parts[2].strip()
        else:
            frontmatter_yaml = ""
            markdown_content = content
    else:
        frontmatter_yaml = ""
        markdown_content = content

    # Parse frontmatter
    meta = ez_yaml.to_object(frontmatter_yaml) if frontmatter_yaml else {}
    if not isinstance(meta, dict):
        meta = {}

    # Extract title from meta or markdown
    title = meta.get("title")
    if not isinstance(title, str):
        title = None
    if not title and markdown_content:
        # Try to extract title from first heading
        first_line = markdown_content.split("\n")[0].strip()
        if first_line.startswith("#"):
            title = first_line.lstrip("#").strip()

    return LicensePageData(
        meta=meta,
        markdown=markdown_content,
        title=title,
        url=str(file_path)
    )


class LicenseContent:
    """
    Simplified license content class for CLI tools.
    Contains only the functionality needed for readability analysis.
    """

    _year_pattern: ClassVar[Pattern[str]] = re.compile(r"\{\{\s{1,2}year\s{1,2}\}\}")
    _definition_pattern = re.compile(
        r"(?P<term>`[\w\s]+`)\s*?\n{1,2}:\s{1,4}(?P<def>[\w\s]+)\n{2}", re.MULTILINE
    )
    _header_pattern: ClassVar[Pattern[str]] = re.compile(r"#+ (\w+?)\n")
    _markdown_pattern: ClassVar[Pattern[str]] = re.compile(r"#+ |(\*\*|\*|`)(.*?)\1", re.MULTILINE)
    _link_pattern: ClassVar[Pattern[str]] = re.compile(r"\[(.*?)\]\((.*?)\)", re.MULTILINE)
    _image_pattern: ClassVar[Pattern[str]] = re.compile(r"!\[(.*?)\]\((.*?)\)", re.MULTILINE)

    def __init__(self, page: LicensePageData) -> None:
        """
        Initialize with minimal attributes needed for readability analysis.

        Args:
            page (LicensePageData): The page data containing metadata and content.
        """
        self.page = page
        self.meta = page.meta
        self.title = f"The {self.meta['plain_name']}"
        self.year = str(datetime.now(UTC).strftime("%Y"))
        self.reader_license_text: str = self.replace_year(self.meta["reader_license_text"])
        self.plaintext_license_text = self.process_markdown_to_plaintext()
        self.original_license_text = dedent(self.meta.get("original_license_text", ""))

    def get_title(self, *, original: bool = False) -> str:
        """Returns the title of the license."""
        return self.meta.get("original_name", self.title) if original else self.title

    def replace_year(self, text: str) -> str:
        """Replaces the year placeholder in the provided text with the current year."""
        return type(self)._year_pattern.sub(self.year, text)  # noqa: SLF001

    def process_markdown_to_plaintext(self, text: str | None = None) -> str:
        """
        Strips Markdown formatting from the license text to produce a plaintext version.

        Returns:
            str: The processed plaintext version of the Markdown license text.
        """
        text = text or self.reader_license_text
        text = self.process_definitions(text, plaintext=True)
        if headers := self._header_pattern.finditer(text):
            for header in headers:
                text = text.replace(header.group(0), f"{header.group(1).upper()}\n")
        text = type(self)._markdown_pattern.sub(r"\2", text)  # Remove headers, bold, italic, inline code  # noqa: SLF001
        text = type(self)._link_pattern.sub(r"\1 (\2)", text)  # Handle links  # noqa: SLF001
        return type(self)._image_pattern.sub(r"\1 (\2)", text)  # Handle images  # noqa: SLF001

    @staticmethod
    def process_definitions(text: str, *, plaintext: bool = False) -> str:
        """
        Identifies and processes definitions in the input text, formatting them appropriately.

        Args:
            text (str): The input text containing definitions to be processed.
            plaintext (bool, optional): A flag indicating whether to
            return definitions in plaintext format. Defaults to False.

        Returns:
            str: The processed text with definitions formatted appropriately.
        """
        definition_pattern = LicenseContent._definition_pattern
        if matches := definition_pattern.finditer(text):
            for match in matches:
                term = match.group("term")
                def_text = match.group("def")
                if plaintext:
                    replacement = "\n" + dedent(f"""{term.replace("`", "")} - {def_text}""") + "\n"
                else:
                    replacement = "\n" + dedent(f"""{term}:\n{def_text}""") + "\n"
                text = text.replace(match.group(0), replacement)
        if matches := re.findall(r"\{\s?\.\w+\s?\}", text):
            for match in matches:
                text = text.replace(match, "")
        return text

    @property
    def plaintext_content(self) -> str:
        """
        Returns the plaintext content of the Plain License version of the license.
        This property provides an unformatted version suitable for readability analysis.
        """
        return self.plaintext_license_text.replace("```plaintext", "").replace("```", "").strip()

    @property
    def original_plaintext_content(self) -> str:
        """
        Returns the original license as an unformatted plaintext string.
        Suitable for readability analysis.
        """
        return self.original_license_text.strip()

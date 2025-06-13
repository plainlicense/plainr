"""Initialization for the licenses module."""
from plainr._licenses._license_content import (
    LicenseContent,
    LicensePageData,
    get_license_data,
    parse_license_file,
)


__all__ = ("LicenseContent", "LicensePageData", "get_license_data", "parse_license_file")

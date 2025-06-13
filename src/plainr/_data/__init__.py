"""Data module for Plainr. Downloads and manages NLTK data resources."""
from pathlib import Path

import nltk


def get_nltk_data() -> None:
    """
    Downloads the NLTK data if it is not already present.
    """
    nltk_data_dir = Path(__file__).parent / "nltk_data"

    if nltk_data_dir not in nltk.data.path:
        nltk.data.path.append(str(nltk_data_dir))

    try:
        nltk.find("punkt_tab")
    except LookupError:
        nltk.download("punkt_tab", quiet=True, download_dir=nltk_data_dir)


__all__ = ("get_nltk_data",)

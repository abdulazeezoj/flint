"""Brupy's error hierarchy.

`BrupyUserError` maps to exit code 1 (the user did something we can
explain, e.g. an existing directory or an invalid name). Anything else
bubbles up and is treated as exit code 2 (unexpected/internal error), per
PRODUCT_FLOW.md §5.
"""

from __future__ import annotations


class BrupyError(Exception):
    """Base class for all Brupy-raised errors."""


class BrupyUserError(BrupyError):
    """An error caused by user input/environment, not a Brupy bug."""

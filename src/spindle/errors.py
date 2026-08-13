"""Spindle's error hierarchy.

`SpindleUserError` maps to exit code 1 (the user did something we can
explain, e.g. an existing directory or an invalid name). Anything else
bubbles up and is treated as exit code 2 (unexpected/internal error), per
PRODUCT_FLOW.md §5.
"""

from __future__ import annotations


class SpindleError(Exception):
    """Base class for all Spindle-raised errors."""


class SpindleUserError(SpindleError):
    """An error caused by user input/environment, not a Spindle bug."""

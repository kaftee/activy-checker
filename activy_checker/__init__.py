"""activy-checker: audit Activy's activity sync."""
from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

from .activy import ActivyClient
from .compare import CompareResult, Match, compare
from .garmin import GarminClient
from .models import Activity
from .report import render_comparison, render_summary, summarize

try:
    __version__ = version("activy-checker")
except PackageNotFoundError:  # running from a source tree that was never installed
    __version__ = "0+unknown"

__all__ = [
    "ActivyClient",
    "GarminClient",
    "Activity",
    "compare",
    "CompareResult",
    "Match",
    "summarize",
    "render_summary",
    "render_comparison",
]

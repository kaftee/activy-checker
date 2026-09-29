"""activy-checker: verify that your Garmin activities made it into Activy."""
from __future__ import annotations

from .activy import ActivyClient
from .compare import CompareResult, Match, compare
from .garmin import GarminClient
from .models import Activity
from .report import render_comparison, render_summary, summarize

__version__ = "0.2.5"
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

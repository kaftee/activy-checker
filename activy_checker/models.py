"""Shared, normalized activity model used for both sources (Activy, Garmin)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# Common categories that both services' types are mapped to.
KIND_BIKE = "bike"
KIND_RUN = "run"
KIND_WALK = "walk"
KIND_SWIM = "swim"
KIND_EXERCISE = "exercise"
KIND_STEPS = "steps"
KIND_OTHER = "other"

KIND_LABEL = {
    KIND_BIKE: "Bike",
    KIND_RUN: "Run",
    KIND_WALK: "Walk",
    KIND_SWIM: "Swim",
    KIND_EXERCISE: "Exercise",
    KIND_STEPS: "Steps",
    KIND_OTHER: "Other",
}


@dataclass
class Activity:
    """A single activity reduced to a common shape."""

    source: str  # "activy" | "garmin"
    id: str  # identifier in the source system
    date: str  # "YYYY-MM-DD" (local start date)
    start: str  # full start timestamp (ISO) if available
    kind: str  # one of KIND_*
    raw_type: str  # original source type (e.g. "road_biking", "0")
    distance_km: float
    duration_s: int
    raw: dict[str, Any] = field(default_factory=dict, repr=False)

    @property
    def duration_hms(self) -> str:
        return format_duration(self.duration_s)


def format_duration(seconds: int) -> str:
    s = int(seconds or 0)
    return f"{s // 3600}:{s % 3600 // 60:02d}:{s % 60:02d}"

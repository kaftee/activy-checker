"""Match Activy activities against Garmin and describe the differences.

The two services share start timestamps almost exactly (Activy copies the
duration from Garmin), so date + duration is the most reliable match key.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .models import Activity


@dataclass
class Match:
    activy: Activity
    garmin: Activity

    @property
    def distance_delta_km(self) -> float:
        return round(self.activy.distance_km - self.garmin.distance_km, 2)


@dataclass
class CompareResult:
    matched: list[Match] = field(default_factory=list)
    only_garmin: list[Activity] = field(default_factory=list)  # missing in Activy
    only_activy: list[Activity] = field(default_factory=list)  # missing in Garmin
    distance_mismatches: list[Match] = field(default_factory=list)


def compare(
    activy: list[Activity],
    garmin: list[Activity],
    duration_tolerance_s: int = 8,
    distance_tolerance_km: float = 0.5,
) -> CompareResult:
    """Greedy match by (date, duration ± tolerance)."""
    result = CompareResult()
    used = [False] * len(garmin)

    for a in activy:
        best = -1
        for i, g in enumerate(garmin):
            if used[i] or g.date != a.date:
                continue
            if abs(g.duration_s - a.duration_s) <= duration_tolerance_s:
                best = i
                break
        if best >= 0:
            used[best] = True
            m = Match(activy=a, garmin=garmin[best])
            result.matched.append(m)
            if abs(m.distance_delta_km) > distance_tolerance_km:
                result.distance_mismatches.append(m)
        else:
            result.only_activy.append(a)

    result.only_garmin = [g for i, g in enumerate(garmin) if not used[i]]
    return result

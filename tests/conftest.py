"""Shared test fixtures. All data is synthetic; no network access is used."""
from __future__ import annotations

import pytest

from activy_checker.models import Activity


def make_activity(
    source: str,
    date: str,
    duration_s: int,
    distance_km: float = 0.0,
    kind: str = "bike",
    raw_type: str = "road_biking",
    id: str | None = None,
) -> Activity:
    return Activity(
        source=source,
        id=id or f"{source}-{date}-{duration_s}",
        date=date,
        start=f"{date}T10:00:00",
        kind=kind,
        raw_type=raw_type,
        distance_km=distance_km,
        duration_s=duration_s,
    )


@pytest.fixture
def act():
    return make_activity


def activy_event(user_id, date, activity_id, activity_type=0, distance=10.0, time="0.01:00:00.000"):
    """A feed event shaped like Activy's newsfeed response."""
    return {
        "Date": f"{date}T10:00:00.000+02:00",
        "Content": {
            "Ride": {
                "UserId": user_id,
                "ActivityId": activity_id,
                "ActivityType": activity_type,
                "Distance": distance,
                "Time": time,
            }
        },
    }


def non_ride_event(date):
    return {"Date": f"{date}T10:00:00.000+02:00", "Content": {"Ride": None, "LevelUp": {}}}


def garmin_raw(activity_id, start, type_key="road_biking", distance_m=10000.0, duration=3600.0):
    """A dict shaped like garminconnect's get_activities_by_date() item."""
    return {
        "activityId": activity_id,
        "startTimeLocal": start,
        "activityType": {"typeKey": type_key},
        "distance": distance_m,
        "duration": duration,
    }

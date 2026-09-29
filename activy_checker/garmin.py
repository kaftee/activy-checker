"""Garmin Connect client (thin wrapper over the `garminconnect` library)."""
from __future__ import annotations

import datetime
from typing import Any, Callable

from .models import (
    Activity,
    KIND_BIKE,
    KIND_EXERCISE,
    KIND_OTHER,
    KIND_RUN,
    KIND_SWIM,
    KIND_WALK,
)

# Garmin activityType.typeKey -> common category
_KIND_BY_TYPEKEY = {
    "road_biking": KIND_BIKE,
    "mountain_biking": KIND_BIKE,
    "gravel_cycling": KIND_BIKE,
    "cycling": KIND_BIKE,
    "virtual_ride": KIND_BIKE,
    "indoor_cycling": KIND_BIKE,
    "running": KIND_RUN,
    "trail_running": KIND_RUN,
    "treadmill_running": KIND_RUN,
    "track_running": KIND_RUN,
    "walking": KIND_WALK,
    "hiking": KIND_WALK,
    "casual_walking": KIND_WALK,
    "swimming": KIND_SWIM,
    "open_water_swimming": KIND_SWIM,
    "lap_swimming": KIND_SWIM,
    "indoor_cardio": KIND_EXERCISE,
    "strength_training": KIND_EXERCISE,
    "yoga": KIND_EXERCISE,
    "fitness_equipment": KIND_EXERCISE,
}


class GarminError(RuntimeError):
    pass


class GarminClient:
    """Wraps `garminconnect.Garmin`, normalizing results to `Activity`."""

    def __init__(self, tokenstore: str | None = None):
        self.tokenstore = tokenstore
        self._api = None

    def login(
        self,
        email: str | None = None,
        password: str | None = None,
        mfa_prompt: Callable[[], str] | None = None,
    ) -> None:
        try:
            from garminconnect import Garmin
        except ImportError as e:  # pragma: no cover
            raise GarminError(
                "The 'garminconnect' package is required. Install with: pip install garminconnect"
            ) from e

        # 1) try to resume a saved session
        if self.tokenstore:
            try:
                api = Garmin()
                api.login(self.tokenstore)
                self._api = api
                return
            except Exception:
                pass

        # 2) fresh login (may require MFA)
        if not email or not password:
            raise GarminError("Garmin email and password are required for a fresh login")
        api = Garmin(email=email, password=password,
                     prompt_mfa=mfa_prompt or (lambda: input("Garmin MFA code: ").strip()))
        api.login()
        self._api = api
        if self.tokenstore:
            for saver in (lambda: api.garth.dump(self.tokenstore),
                          lambda: api.session.dump(self.tokenstore)):
                try:
                    saver()
                    break
                except Exception:
                    continue

    def get_activities(self, since: str, until: str | None = None) -> list[Activity]:
        if self._api is None:
            raise GarminError("Not logged in: call client.login(...) first")
        until = until or datetime.date.today().isoformat()
        raw = self._api.get_activities_by_date(since, until)
        return [_to_activity(a) for a in raw]


def _to_activity(a: dict[str, Any]) -> Activity:
    type_key = (a.get("activityType") or {}).get("typeKey", "") or ""
    start = a.get("startTimeLocal") or ""
    return Activity(
        source="garmin",
        id=str(a.get("activityId")),
        date=start[:10],
        start=start,
        kind=_KIND_BY_TYPEKEY.get(type_key, KIND_OTHER),
        raw_type=type_key,
        distance_km=round(float(a.get("distance") or 0.0) / 1000.0, 2),
        duration_s=int(a.get("duration") or 0),
        raw=a,
    )

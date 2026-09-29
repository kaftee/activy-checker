"""Garmin Connect client (thin wrapper over the `garminconnect` library)."""
from __future__ import annotations

import contextlib
import datetime
import logging
from typing import Any, Callable, Iterator

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


class _ListHandler(logging.Handler):
    def __init__(self, sink: list[str]):
        super().__init__(level=logging.DEBUG)
        self.sink = sink

    def emit(self, record: logging.LogRecord) -> None:
        self.sink.append(f"{record.levelname}: {record.getMessage()}")


@contextlib.contextmanager
def _capture_library_logs(sink: list[str], enabled: bool = True) -> Iterator[None]:
    """Collect garminconnect's log output into ``sink`` instead of the terminal.

    During sign-in garminconnect tries several strategies and logs a warning for
    each one Garmin rejects (e.g. "mobile+cffi returned 429 ..."), even when a
    later strategy succeeds. Those warnings are noise for end users.
    """
    if not enabled:
        yield
        return
    logger = logging.getLogger("garminconnect")
    handler = _ListHandler(sink)
    previous_propagate = logger.propagate
    logger.addHandler(handler)
    logger.propagate = False
    try:
        yield
    finally:
        logger.removeHandler(handler)
        logger.propagate = previous_propagate


def _garmin_class():
    try:
        from garminconnect import Garmin
    except ImportError as e:  # pragma: no cover
        raise GarminError(
            "The 'garminconnect' package is required. Install with: pip install garminconnect"
        ) from e
    return Garmin


class GarminClient:
    """Wraps `garminconnect.Garmin`, normalizing results to `Activity`.

    ``tokenstore`` is an optional directory (tokens are kept in
    ``garmin_tokens.json`` inside it) or a path to a ``.json`` file. When set,
    a saved session is reused and a fresh login is persisted there, so MFA is
    only needed once.

    With ``quiet=True`` (default) the library's sign-in warnings are kept in
    ``self.log`` instead of being printed.
    """

    def __init__(self, tokenstore: str | None = None, quiet: bool = True):
        self.tokenstore = tokenstore
        self.quiet = quiet
        self.log: list[str] = []
        self._api = None

    def try_resume(self) -> bool:
        """Resume a saved session from ``tokenstore``; return True on success."""
        if not self.tokenstore:
            return False
        Garmin = _garmin_class()
        try:
            api = Garmin()
            with _capture_library_logs(self.log, self.quiet):
                api.login(self.tokenstore)
        except Exception:
            return False
        self._api = api
        return True

    def login(
        self,
        email: str | None = None,
        password: str | None = None,
        mfa_prompt: Callable[[], str] | None = None,
    ) -> None:
        """Log in, reusing a saved session when possible (may prompt for MFA)."""
        if self.try_resume():
            return
        if not email or not password:
            raise GarminError("Garmin email and password are required for a fresh login")
        Garmin = _garmin_class()
        api = Garmin(email=email, password=password,
                     prompt_mfa=mfa_prompt or (lambda: input("Garmin MFA code: ").strip()))
        try:
            # With a tokenstore, garminconnect persists the new session itself.
            with _capture_library_logs(self.log, self.quiet):
                api.login(self.tokenstore)
        except Exception as e:
            raise GarminError(f"Garmin login failed: {e}") from e
        self._api = api

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

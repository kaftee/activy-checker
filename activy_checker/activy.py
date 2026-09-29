"""Client for Activy's unofficial mobile API (OpenID Connect + CQRS queries).

Activy exposes no public API. This client talks to the same endpoints as the
mobile app, authenticating against YOUR account (grant_type=password).
Intended for use with your own account and your own data.
"""
from __future__ import annotations

import json
import ssl
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from .models import (
    Activity,
    KIND_BIKE,
    KIND_EXERCISE,
    KIND_OTHER,
    KIND_RUN,
    KIND_STEPS,
)

AUTH_BASE = "https://players.v3.activy.pl/auth"
TOKEN_URL = AUTH_BASE + "/connect/token"
USERINFO_URL = AUTH_BASE + "/connect/userinfo"
CLIENT_ID = "activy.mobile"
SCOPE = (
    "openid profile email offline_access "
    "activy.rides activy.players activy.contests activy.rankings"
)

HOSTS = {
    "players": "https://players.v3.activy.pl",
    "rides": "https://rides.v3.activy.pl",
    "contests": "https://contests.v3.activy.pl",
    "rankings": "https://rankings.v3.activy.pl",
}

MYCONTESTS = "Activy.Contests.Contracts.Mobile.Contests.MyContests"
USER_CONTEST_FEED = "Activy.Players.Contracts.Mobile.Newsfeed.UserContestFeed"
CONTEST_FEED = "Activy.Players.Contracts.Mobile.Newsfeed.ContestFeed"

# Activy ActivityType -> common category
_KIND_BY_TYPE = {0: KIND_BIKE, 1: KIND_RUN, 2: KIND_EXERCISE, 3: KIND_STEPS}

_CTX = ssl.create_default_context()


class ActivyError(RuntimeError):
    pass


class ActivyClient:
    def __init__(self, timeout: int = 40):
        self._token: str | None = None
        self._user_id: str | None = None
        self.timeout = timeout

    # ---- authentication --------------------------------------------------
    def login(self, email: str, password: str) -> None:
        data = urllib.parse.urlencode({
            "grant_type": "password",
            "client_id": CLIENT_ID,
            "username": email,
            "password": password,
            "scope": SCOPE,
        }).encode()
        req = urllib.request.Request(TOKEN_URL, data=data, method="POST")
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
        req.add_header("Accept", "application/json")
        try:
            with urllib.request.urlopen(req, context=_CTX, timeout=self.timeout) as r:
                body = json.loads(r.read().decode("utf-8", "replace"))
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")
            raise ActivyError(f"Activy login failed (HTTP {e.code}): {detail[:200]}")
        token = body.get("access_token")
        if not token:
            raise ActivyError(f"No access_token in response: {body}")
        self._token = token

    @property
    def user_id(self) -> str:
        if self._user_id is None:
            self._user_id = self._userinfo()["sub"]
        return self._user_id

    def _userinfo(self) -> dict[str, Any]:
        return self._get(USERINFO_URL)

    # ---- low-level calls -------------------------------------------------
    def _headers(self) -> dict[str, str]:
        if not self._token:
            raise ActivyError("Not logged in: call client.login(email, password) first")
        return {
            "Authorization": "Bearer " + self._token,
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "activy-checker/1.0",
        }

    def _get(self, url: str) -> Any:
        req = urllib.request.Request(url, method="GET")
        for k, v in self._headers().items():
            req.add_header(k, v)
        with urllib.request.urlopen(req, context=_CTX, timeout=self.timeout) as r:
            return json.loads(r.read().decode("utf-8", "replace"))

    def query(self, service: str, namespace: str, payload: dict[str, Any]) -> tuple[int, Any]:
        url = f"{HOSTS[service]}/api/query/{namespace}"
        req = urllib.request.Request(url, data=json.dumps(payload).encode(), method="POST")
        for k, v in self._headers().items():
            req.add_header(k, v)
        try:
            with urllib.request.urlopen(req, context=_CTX, timeout=self.timeout) as r:
                return r.status, json.loads(r.read().decode("utf-8", "replace"))
        except urllib.error.HTTPError as e:
            return e.code, None

    # ---- high-level ------------------------------------------------------
    def contest_ids(self) -> list[str]:
        st, data = self.query("contests", MYCONTESTS, {})
        if st != 200 or not isinstance(data, list):
            return []
        ids = []
        for x in data:
            cid = x.get("Id") or x.get("ContestId") or (x.get("Contest") or {}).get("Id")
            if cid:
                ids.append(cid)
        return ids

    def get_activities(self, since: str, max_pages: int = 500) -> list[Activity]:
        """Return your activities with date >= ``since`` (YYYY-MM-DD).

        Activities are read from each contest's feed (there is no dedicated
        list endpoint). The feed is reverse-chronological, so we paginate until
        every event on a page is older than ``since``.
        """
        me = self.user_id
        found: dict[str, Activity] = {}
        for cid in self.contest_ids():
            self._collect_contest(cid, me, since, found, max_pages)
        return sorted(found.values(), key=lambda a: a.start or "")

    def _collect_contest(self, cid, me, since, found, max_pages) -> None:
        # pick a working feed
        feed = USER_CONTEST_FEED
        st, arr = self.query("players", feed, {"ContestId": cid, "Page": 0, "PageSize": 50})
        if st != 200 or not isinstance(arr, list) or not arr:
            feed = CONTEST_FEED
        page = 0
        while page < max_pages:
            st, arr = self.query("players", feed,
                                 {"ContestId": cid, "Page": page, "PageSize": 50})
            if st != 200 or not isinstance(arr, list) or not arr:
                break
            page_dates = []
            for ev in arr:
                date = (ev.get("Date") or "")[:10]
                page_dates.append(date)
                ride = (ev.get("Content") or {}).get("Ride")
                if not ride:
                    continue
                if ride.get("UserId") not in (me, None):
                    continue
                if date and date < since:
                    continue
                act = _ride_to_activity(ride, ev.get("Date"))
                if act and act.id not in found:
                    found[act.id] = act
            # early stop: whole page older than 'since'
            if page_dates and max(page_dates) < since:
                break
            page += 1


def _duration_seconds(t: str | None) -> int:
    """Parse Activy duration 'd.hh:mm:ss.fff' or 'hh:mm:ss' into seconds."""
    if not t:
        return 0
    try:
        head = t.split(":")[0]
        if "." in head:
            days_s, hms = t.split(".", 1)
            days = int(days_s)
        else:
            days, hms = 0, t
        parts = hms.split(".")[0].split(":")
        h, m, s = (list(map(int, parts)) + [0, 0, 0])[:3]
        return days * 86400 + h * 3600 + m * 60 + s
    except (ValueError, IndexError):
        return 0


def _ride_to_activity(ride: dict[str, Any], date_iso: str | None) -> Activity | None:
    aid = ride.get("ActivityId")
    if not aid:
        return None
    atype = ride.get("ActivityType")
    return Activity(
        source="activy",
        id=str(aid),
        date=(date_iso or "")[:10],
        start=date_iso or "",
        kind=_KIND_BY_TYPE.get(atype, KIND_OTHER),
        raw_type=str(atype),
        distance_km=round(float(ride.get("Distance") or 0.0), 2),
        duration_s=_duration_seconds(ride.get("Time")),
        raw=ride,
    )

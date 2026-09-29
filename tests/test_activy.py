import pytest

from activy_checker import activy as activy_mod
from activy_checker.activy import (
    CONTEST_FEED,
    MYCONTESTS,
    USER_CONTEST_FEED,
    ActivyClient,
    ActivyError,
    _duration_seconds,
    _ride_to_activity,
)

from .conftest import activy_event, non_ride_event

ME = "user-me"
OTHER = "user-other"


# ---- duration parsing -----------------------------------------------------

@pytest.mark.parametrize(
    "value, expected",
    [
        ("0.01:27:09.000", 5229),
        ("0.00:10:09.000", 609),
        ("1.02:00:00.000", 86400 + 7200),
        ("01:00:00", 3600),
        ("00:06:26", 386),
        ("", 0),
        (None, 0),
        ("garbage", 0),
    ],
)
def test_duration_seconds(value, expected):
    assert _duration_seconds(value) == expected


# ---- ride -> Activity -----------------------------------------------------

def test_ride_to_activity_maps_fields():
    ride = {"ActivityId": "a1", "ActivityType": 0, "Distance": 83.7, "Time": "0.03:50:21.000"}
    a = _ride_to_activity(ride, "2026-09-02T09:00:00.000+02:00")
    assert a.source == "activy"
    assert a.id == "a1"
    assert a.date == "2026-09-02"
    assert a.kind == "bike"
    assert a.distance_km == 83.7
    assert a.duration_s == 3 * 3600 + 50 * 60 + 21


@pytest.mark.parametrize("atype, kind", [(0, "bike"), (1, "run"), (2, "exercise"), (3, "steps"), (99, "other")])
def test_ride_to_activity_kind_mapping(atype, kind):
    a = _ride_to_activity({"ActivityId": "x", "ActivityType": atype}, "2026-09-01T00:00:00")
    assert a.kind == kind


def test_ride_without_id_is_skipped():
    assert _ride_to_activity({"ActivityType": 0}, "2026-09-01T00:00:00") is None


def test_ride_missing_distance_defaults_to_zero():
    a = _ride_to_activity({"ActivityId": "x", "ActivityType": 2}, "2026-09-01T00:00:00")
    assert a.distance_km == 0.0
    assert a.duration_s == 0


# ---- client with a fake transport -----------------------------------------

class FakeActivy(ActivyClient):
    """ActivyClient whose network calls are replaced by in-memory pages."""

    def __init__(self, pages, contests=("c1",), user_contest_feed_works=True):
        super().__init__()
        self._token = "fake-token"
        self.pages = pages  # list of lists (feed pages, newest first)
        self.contests = list(contests)
        self.ucf_works = user_contest_feed_works
        self.calls = []

    def _userinfo(self):
        return {"sub": ME}

    def query(self, service, namespace, payload):
        self.calls.append((service, namespace, dict(payload)))
        if namespace == MYCONTESTS:
            return 200, [{"Id": c} for c in self.contests]
        if namespace == USER_CONTEST_FEED and not self.ucf_works:
            return 403, None
        if namespace in (USER_CONTEST_FEED, CONTEST_FEED):
            page = payload.get("Page", 0)
            if page < len(self.pages):
                return 200, self.pages[page]
            return 200, []
        return 404, None


def test_get_activities_filters_to_own_user_and_date():
    pages = [[
        activy_event(ME, "2026-09-28", "a1"),
        activy_event(OTHER, "2026-09-28", "b1"),
        non_ride_event("2026-09-27"),
        activy_event(ME, "2026-09-02", "a2"),
        activy_event(ME, "2026-08-31", "a-old"),  # before 'since'
    ]]
    acts = FakeActivy(pages).get_activities(since="2026-09-01")
    assert [a.id for a in acts] == ["a2", "a1"]  # sorted by start


def test_get_activities_paginates_and_deduplicates():
    pages = [
        [activy_event(ME, "2026-09-20", "a1"), activy_event(ME, "2026-09-19", "a2")],
        [activy_event(ME, "2026-09-19", "a2"), activy_event(ME, "2026-09-10", "a3")],  # a2 duplicated
    ]
    acts = FakeActivy(pages).get_activities(since="2026-09-01")
    assert sorted(a.id for a in acts) == ["a1", "a2", "a3"]


def test_get_activities_stops_early_when_page_is_older_than_since():
    pages = [
        [activy_event(ME, "2026-09-05", "a1")],
        [activy_event(OTHER, "2026-08-20", "b1")],  # whole page older -> stop here
        [activy_event(ME, "2026-08-10", "never-read")],
    ]
    client = FakeActivy(pages)
    acts = client.get_activities(since="2026-09-01")
    assert [a.id for a in acts] == ["a1"]
    feed_pages = [p["Page"] for _, ns, p in client.calls if ns == USER_CONTEST_FEED and "Page" in p]
    assert 2 not in feed_pages


def test_get_activities_falls_back_to_contest_feed():
    pages = [[activy_event(ME, "2026-09-05", "a1")]]
    client = FakeActivy(pages, user_contest_feed_works=False)
    acts = client.get_activities(since="2026-09-01")
    assert [a.id for a in acts] == ["a1"]
    assert any(ns == CONTEST_FEED for _, ns, _ in client.calls)


def test_get_activities_merges_multiple_contests():
    class TwoContests(FakeActivy):
        def query(self, service, namespace, payload):
            if namespace in (USER_CONTEST_FEED, CONTEST_FEED) and payload.get("Page", 0) == 0:
                cid = payload["ContestId"]
                return 200, [activy_event(ME, "2026-09-05", f"{cid}-a")]
            return super().query(service, namespace, payload)

    client = TwoContests(pages=[], contests=("c1", "c2"))
    acts = client.get_activities(since="2026-09-01")
    assert sorted(a.id for a in acts) == ["c1-a", "c2-a"]


def test_no_contests_returns_empty():
    assert FakeActivy(pages=[], contests=()).get_activities(since="2026-09-01") == []


def test_calls_without_login_raise():
    with pytest.raises(ActivyError):
        ActivyClient()._headers()


def test_login_sends_password_grant(monkeypatch):
    captured = {}

    class Resp:
        status = 200

        def read(self):
            return b'{"access_token": "tok"}'

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def fake_urlopen(req, context=None, timeout=None):
        captured["url"] = req.full_url
        captured["body"] = req.data.decode()
        return Resp()

    monkeypatch.setattr(activy_mod.urllib.request, "urlopen", fake_urlopen)
    client = ActivyClient()
    client.login("someone@example.com", "secret")
    assert client._token == "tok"
    assert captured["url"] == activy_mod.TOKEN_URL
    assert "grant_type=password" in captured["body"]
    assert "client_id=activy.mobile" in captured["body"]


def test_login_http_error_raises_activy_error(monkeypatch):
    import io
    import urllib.error

    def fake_urlopen(req, context=None, timeout=None):
        raise urllib.error.HTTPError(req.full_url, 400, "Bad Request", {}, io.BytesIO(b'{"error":"invalid_grant"}'))

    monkeypatch.setattr(activy_mod.urllib.request, "urlopen", fake_urlopen)
    with pytest.raises(ActivyError, match="HTTP 400"):
        ActivyClient().login("someone@example.com", "wrong")

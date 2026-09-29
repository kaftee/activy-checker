import pytest

from activy_checker.garmin import GarminClient, GarminError, _to_activity

from .conftest import garmin_raw


def test_to_activity_converts_units():
    a = _to_activity(garmin_raw(123, "2026-09-27 08:00:00", "road_biking", 106230.0, 12003.4))
    assert a.source == "garmin"
    assert a.id == "123"
    assert a.date == "2026-09-27"
    assert a.kind == "bike"
    assert a.raw_type == "road_biking"
    assert a.distance_km == 106.23
    assert a.duration_s == 12003


@pytest.mark.parametrize(
    "type_key, kind",
    [
        ("road_biking", "bike"),
        ("mountain_biking", "bike"),
        ("cycling", "bike"),
        ("running", "run"),
        ("walking", "walk"),
        ("hiking", "walk"),
        ("open_water_swimming", "swim"),
        ("indoor_cardio", "exercise"),
        ("something_new", "other"),
    ],
)
def test_type_mapping(type_key, kind):
    assert _to_activity(garmin_raw(1, "2026-09-01 08:00:00", type_key)).kind == kind


def test_missing_fields_default_to_zero():
    a = _to_activity({"activityId": 1, "startTimeLocal": "2026-09-01 08:00:00"})
    assert a.kind == "other"
    assert a.distance_km == 0.0
    assert a.duration_s == 0


def test_get_activities_requires_login():
    with pytest.raises(GarminError):
        GarminClient().get_activities("2026-09-01")


def test_get_activities_uses_api():
    class FakeApi:
        def get_activities_by_date(self, start, end):
            self.args = (start, end)
            return [garmin_raw(1, "2026-09-02 08:00:00"), garmin_raw(2, "2026-09-03 08:00:00", "walking")]

    client = GarminClient()
    client._api = FakeApi()
    acts = client.get_activities("2026-09-01", "2026-09-30")
    assert client._api.args == ("2026-09-01", "2026-09-30")
    assert [a.kind for a in acts] == ["bike", "walk"]


def _install_fake_garminconnect(monkeypatch, resume_ok, fresh_login_ok=True, noisy=False):
    """Register a fake `garminconnect` module and return the list of created instances.

    Mirrors garminconnect 0.3 semantics: ``login(tokenstore)`` loads a saved
    session if one exists; otherwise it logs in with the credentials and
    persists the new session to ``tokenstore``.
    """
    import sys
    import types

    created = []

    class FakeGarmin:
        def __init__(self, email=None, password=None, prompt_mfa=None, **kw):
            self.email, self.password, self.prompt_mfa = email, password, prompt_mfa
            self.login_args = None
            self.saved_to = None
            created.append(self)

        def login(self, tokenstore=None):
            self.login_args = tokenstore
            if noisy:  # like garminconnect when Garmin rate-limits a strategy
                import logging
                logging.getLogger("garminconnect.client").warning(
                    "mobile+cffi returned 429: GarminConnectTooManyRequestsError: rate limited")
            if tokenstore is not None and resume_ok:
                return None, None
            if not self.email or not self.password:
                raise RuntimeError("Username and password are required")
            if not fresh_login_ok:
                raise RuntimeError("429 Too Many Requests")
            self.saved_to = tokenstore
            return None, None

    fake = types.ModuleType("garminconnect")
    fake.Garmin = FakeGarmin
    monkeypatch.setitem(sys.modules, "garminconnect", fake)
    return created


def test_fresh_login_requires_credentials(monkeypatch):
    _install_fake_garminconnect(monkeypatch, resume_ok=False)
    with pytest.raises(GarminError, match="email and password"):
        GarminClient().login()


def test_login_resumes_saved_session(monkeypatch, tmp_path):
    created = _install_fake_garminconnect(monkeypatch, resume_ok=True)
    client = GarminClient(tokenstore=str(tmp_path))
    client.login()  # no credentials needed
    assert len(created) == 1
    assert created[0].login_args == str(tmp_path)
    assert client._api is created[0]


def test_fresh_login_passes_mfa_prompt_and_saves_session(monkeypatch, tmp_path):
    created = _install_fake_garminconnect(monkeypatch, resume_ok=False)
    prompt = lambda: "123456"  # noqa: E731
    client = GarminClient(tokenstore=str(tmp_path))
    client.login("someone@example.com", "secret", mfa_prompt=prompt)
    fresh = created[-1]
    assert fresh.email == "someone@example.com"
    assert fresh.prompt_mfa is prompt
    assert fresh.saved_to == str(tmp_path)  # session persisted for the next run
    assert client._api is fresh


def test_fresh_login_without_tokenstore(monkeypatch):
    created = _install_fake_garminconnect(monkeypatch, resume_ok=False)
    client = GarminClient()
    client.login("someone@example.com", "secret")
    assert len(created) == 1  # no resume attempt without a tokenstore
    assert created[0].saved_to is None


def test_try_resume_without_tokenstore_is_false(monkeypatch):
    created = _install_fake_garminconnect(monkeypatch, resume_ok=True)
    assert GarminClient().try_resume() is False
    assert created == []


def test_try_resume_missing_session_is_false(monkeypatch, tmp_path):
    _install_fake_garminconnect(monkeypatch, resume_ok=False)
    client = GarminClient(tokenstore=str(tmp_path))
    assert client.try_resume() is False
    assert client._api is None


def test_library_warnings_are_captured_not_printed(monkeypatch, capsys):
    import logging

    _install_fake_garminconnect(monkeypatch, resume_ok=False, noisy=True)
    lib_logger = logging.getLogger("garminconnect")
    before = (list(lib_logger.handlers), lib_logger.propagate)
    client = GarminClient()
    client.login("someone@example.com", "secret")
    assert capsys.readouterr().err == ""
    assert client.log == ["WARNING: mobile+cffi returned 429: GarminConnectTooManyRequestsError: rate limited"]
    assert (list(lib_logger.handlers), lib_logger.propagate) == before  # logger restored


def test_library_warnings_pass_through_when_not_quiet(monkeypatch, caplog):
    # Not swallowed: the record reaches the normal logging chain (in a real
    # terminal Python prints it to stderr; under pytest caplog receives it).
    _install_fake_garminconnect(monkeypatch, resume_ok=False, noisy=True)
    client = GarminClient(quiet=False)
    with caplog.at_level("WARNING"):
        client.login("someone@example.com", "secret")
    assert any("returned 429" in r.getMessage() for r in caplog.records)
    assert client.log == []


def test_logger_restored_after_failed_login(monkeypatch):
    import logging

    _install_fake_garminconnect(monkeypatch, resume_ok=False, fresh_login_ok=False, noisy=True)
    lib_logger = logging.getLogger("garminconnect")
    before = (list(lib_logger.handlers), lib_logger.propagate)
    client = GarminClient()
    with pytest.raises(GarminError):
        client.login("someone@example.com", "secret")
    assert (list(lib_logger.handlers), lib_logger.propagate) == before
    assert client.log  # kept for diagnostics


def test_failed_fresh_login_raises_garmin_error(monkeypatch):
    _install_fake_garminconnect(monkeypatch, resume_ok=False, fresh_login_ok=False)
    with pytest.raises(GarminError, match="429"):
        GarminClient().login("someone@example.com", "secret")

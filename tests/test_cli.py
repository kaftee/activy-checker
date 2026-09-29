import json

import pytest

from activy_checker import cli
from activy_checker.activy import ActivyError

from .conftest import make_activity as mk


class FakeActivyClient:
    activities = []
    fail = None  # exception instance to raise from login()

    def login(self, email, password):
        if self.fail:
            raise self.fail
        self.email = email

    def get_activities(self, since, progress=None):
        if progress:
            progress({"contest": 1, "contests": 1, "page": 1, "found": 1, "reached": since})
        return list(self.activities)


class FakeGarminClient:
    activities = []
    has_saved_session = False
    logins = []
    fetch_error = None

    def __init__(self, tokenstore=None):
        self.tokenstore = tokenstore

    def try_resume(self):
        return bool(self.tokenstore) and self.has_saved_session

    def login(self, email=None, password=None, mfa_prompt=None):
        FakeGarminClient.logins.append((email, password))

    def get_activities(self, since, until=None):
        if self.fetch_error:
            raise self.fetch_error
        return list(self.activities)


@pytest.fixture
def fakes(monkeypatch):
    FakeActivyClient.activities = [
        mk("activy", "2026-09-01", 3600, 30.0),
        mk("activy", "2026-08-15", 3600, 30.0),  # outside the range, filtered out
    ]
    FakeActivyClient.fail = None
    FakeGarminClient.has_saved_session = False
    FakeGarminClient.logins = []
    FakeGarminClient.fetch_error = None
    FakeGarminClient.activities = [
        mk("garmin", "2026-09-01", 3600, 30.0),
        mk("garmin", "2026-09-27", 12003, 106.23),
    ]
    monkeypatch.setattr(cli, "ActivyClient", FakeActivyClient)
    monkeypatch.setattr(cli, "GarminClient", FakeGarminClient)
    monkeypatch.setattr(cli.getpass, "getpass", lambda prompt="": "pw")
    monkeypatch.setattr("builtins.input", lambda prompt="": "someone@example.com")


def test_full_run_reports_missing_activity(fakes, capsys):
    rc = cli.main(["--since", "2026-09-01", "--until", "2026-09-30"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "== Activy ==" in out and "== Garmin ==" in out
    assert "Missing in Activy: 1" in out
    assert "106.23 km" in out


def test_activy_only_skips_garmin(fakes, capsys):
    rc = cli.main(["--since", "2026-09-01", "--activy-only"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "== Activy ==" in out
    assert "Garmin" not in out


def test_json_output(fakes, tmp_path):
    path = tmp_path / "result.json"
    rc = cli.main(["--since", "2026-09-01", "--until", "2026-09-30", "--json", str(path)])
    data = json.loads(path.read_text())
    assert rc == 0
    assert data["activy"]["summary"]["total"]["count"] == 1
    assert data["garmin"]["summary"]["total"]["count"] == 2
    assert data["comparison"]["matched"] == 1
    assert [x["distance_km"] for x in data["comparison"]["missing_in_activy"]] == [106.23]


def test_activy_login_failure_returns_error_code(fakes, capsys):
    FakeActivyClient.fail = ActivyError("bad credentials")
    rc = cli.main(["--since", "2026-09-01"])
    assert rc == 2
    assert "Activy error" in capsys.readouterr().err


def test_network_error_is_reported_not_raised(fakes, capsys):
    import urllib.error

    FakeActivyClient.fail = urllib.error.URLError("no route to host")
    rc = cli.main(["--since", "2026-09-01"])
    assert rc == 2
    assert "no route to host" in capsys.readouterr().err


def test_garmin_failure_returns_error_code(fakes, capsys):
    FakeGarminClient.fetch_error = RuntimeError("429 Too Many Requests")
    rc = cli.main(["--since", "2026-09-01"])
    assert rc == 3
    assert "Garmin error: 429" in capsys.readouterr().err


def test_steps_entries_are_excluded_by_default(fakes, tmp_path):
    FakeActivyClient.activities.append(mk("activy", "2026-09-02", 0, 4.2, kind="steps", raw_type="3"))
    path = tmp_path / "r.json"
    cli.main(["--since", "2026-09-01", "--until", "2026-09-30", "--json", str(path)])
    data = json.loads(path.read_text())
    assert data["activy"]["summary"]["total"]["count"] == 1
    assert data["comparison"]["missing_in_garmin"] == []


def test_include_steps_keeps_them(fakes, tmp_path):
    FakeActivyClient.activities.append(mk("activy", "2026-09-02", 0, 4.2, kind="steps", raw_type="3"))
    path = tmp_path / "r.json"
    cli.main(["--since", "2026-09-01", "--until", "2026-09-30", "--include-steps", "--json", str(path)])
    data = json.loads(path.read_text())
    assert data["activy"]["summary"]["total"]["count"] == 2
    assert len(data["comparison"]["missing_in_garmin"]) == 1


def test_tolerance_flags_are_applied(fakes, tmp_path):
    FakeActivyClient.activities = [mk("activy", "2026-09-01", 3600, 30.0)]
    FakeGarminClient.activities = [mk("garmin", "2026-09-01", 3620, 30.3)]
    path = tmp_path / "r.json"
    cli.main(["--since", "2026-09-01", "--json", str(path)])
    assert json.loads(path.read_text())["comparison"]["matched"] == 0
    cli.main(["--since", "2026-09-01", "--duration-tolerance", "30",
              "--distance-tolerance", "0.1", "--json", str(path)])
    cmp_ = json.loads(path.read_text())["comparison"]
    assert cmp_["matched"] == 1
    assert len(cmp_["distance_mismatches"]) == 1


def test_tokenstore_first_run_prompts_for_password(fakes, tmp_path):
    rc = cli.main(["--since", "2026-09-01", "--garmin-tokenstore", str(tmp_path)])
    assert rc == 0
    assert FakeGarminClient.logins == [("someone@example.com", "pw")]


def test_tokenstore_saved_session_skips_login(fakes, tmp_path, capsys):
    FakeGarminClient.has_saved_session = True
    rc = cli.main(["--since", "2026-09-01", "--garmin-tokenstore", str(tmp_path)])
    assert rc == 0
    assert FakeGarminClient.logins == []
    assert "Resumed saved Garmin session" in capsys.readouterr().err


def test_prompts_go_to_stderr_not_stdout(fakes, capsys):
    cli.main(["--since", "2026-09-01"])
    captured = capsys.readouterr()
    assert "Activy email:" in captured.err
    assert "Garmin email:" in captured.err
    assert "email:" not in captured.out


def test_email_flags_skip_prompts(fakes, capsys):
    cli.main(["--since", "2026-09-01", "--activy-email", "a@example.com", "--garmin-email", "g@example.com"])
    assert "email:" not in capsys.readouterr().err
    assert FakeGarminClient.logins == [("g@example.com", "pw")]


def test_warns_when_no_activy_activities(fakes, capsys):
    FakeActivyClient.activities = []
    cli.main(["--since", "2026-09-01", "--activy-only"])
    assert "no Activy activities found" in capsys.readouterr().err


def test_progress_message_format():
    msg = cli._activy_progress({"contest": 1, "contests": 1, "page": 12, "found": 5,
                                "reached": "2026-09-14"}, "2026-09-01")
    assert msg == ("Scanning Activy feed: page 12, 5 of yours so far, reached 2026-09-14 "
                   "(going back to 2026-09-01) ...")
    multi = cli._activy_progress({"contest": 2, "contests": 3, "page": 1, "found": 0,
                                  "reached": ""}, "2026-09-01")
    assert "(contest 2/3)" in multi and "reached" not in multi


def test_default_since_is_fixed_date():
    assert cli.build_parser().parse_args([]).since == "2026-09-01"


def test_since_flag_overrides_default():
    assert cli.build_parser().parse_args(["--since", "2026-05-01"]).since == "2026-05-01"


def test_ctrl_c_exits_cleanly(fakes, monkeypatch, capsys):
    def interrupted(prompt=""):
        raise KeyboardInterrupt

    monkeypatch.setattr(cli.getpass, "getpass", interrupted)
    rc = cli.main(["--since", "2026-09-01"])
    assert rc == 130
    assert "Aborted." in capsys.readouterr().err

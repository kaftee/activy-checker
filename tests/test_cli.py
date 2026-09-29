import json

import pytest

from activy_checker import cli
from activy_checker.activy import ActivyError

from .conftest import make_activity as mk


class FakeActivyClient:
    activities = []
    fail = False

    def login(self, email, password):
        if self.fail:
            raise ActivyError("bad credentials")
        self.email = email

    def get_activities(self, since):
        return list(self.activities)


class FakeGarminClient:
    activities = []

    def __init__(self, tokenstore=None):
        self.tokenstore = tokenstore

    def login(self, email=None, password=None, mfa_prompt=None):
        pass

    def get_activities(self, since, until=None):
        return list(self.activities)


@pytest.fixture
def fakes(monkeypatch):
    FakeActivyClient.activities = [
        mk("activy", "2026-09-01", 3600, 30.0),
        mk("activy", "2026-08-15", 3600, 30.0),  # outside the range, filtered out
    ]
    FakeActivyClient.fail = False
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
    FakeActivyClient.fail = True
    rc = cli.main(["--since", "2026-09-01"])
    assert rc == 2
    assert "Activy error" in capsys.readouterr().err


def test_default_since_is_30_days_ago():
    import datetime

    args = cli.build_parser().parse_args([])
    expected = (datetime.date.today() - datetime.timedelta(days=30)).isoformat()
    assert args.since == expected

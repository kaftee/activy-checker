# activy-checker

[![tests](https://github.com/kaftee/activy-checker/actions/workflows/tests.yml/badge.svg)](https://github.com/kaftee/activy-checker/actions/workflows/tests.yml)

Verify that your [Garmin Connect](https://connect.garmin.com) activities were
correctly imported into [Activy](https://activy.app), and get a clean summary of
your activities from both sources.

Activy imports activities from Garmin, but the import is not always complete —
a ride can silently fail to appear, or be recorded with a wrong distance.
`activy-checker` logs into **your** Activy and Garmin accounts, pulls your
activities from a given date, and reports:

- **Missing in Activy** — activities present in Garmin but not imported.
- **Missing in Garmin** — activities present only in Activy.
- **Distance mismatches** — the same activity recorded with different distance.
- A per-kind **summary** (count, distance, time) for each source.

## Disclaimer

This is an **unofficial** tool. Activy has no public API, so this project talks
to the same mobile endpoints the Activy app uses, authenticating with your own
credentials. Use it only with **your own account and your own data**, at your
own risk. Not affiliated with or endorsed by Activy or Garmin.

## Install

Requires Python 3.12+.

```bash
git clone https://github.com/kaftee/activy-checker.git
cd activy-checker
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
```

## Usage

```bash
# Compare the last 30 days (default)
activy-checker

# Compare a specific range
activy-checker --since 2026-09-01 --until 2026-09-29

# Only fetch and summarize Activy
activy-checker --activy-only

# Save the full result as JSON
activy-checker --since 2026-09-01 --json result.json

# Cache the Garmin session so you are not asked for MFA every run
activy-checker --garmin-tokenstore ~/.garminconnect
```

You are prompted for each account's email and password interactively
(passwords are read with `getpass` and never stored by the tool). If your
Garmin account uses MFA, you are asked for the code once.

### Example output

```
== Activy ==

Kind         Count     Distance       Time
----------------------------------------
Bike            18      791.6 km    ...
Run             17       99.0 km    ...
Exercise         9        0.0 km    ...
----------------------------------------
TOTAL           44      890.6 km    ...

== Comparison: Activy vs Garmin ==

Matched: 44 | Missing in Activy: 1 | Missing in Garmin: 0 | Distance mismatches: 1

-- Missing in Activy (present in Garmin, not imported) [1] --
  2026-09-27  road_biking        106.23 km  3:20:03
```

## How it works

- **Activy**: OpenID Connect password grant against `players.v3.activy.pl`,
  then CQRS-style `POST /api/query/<contract>` calls. Activities are read from
  each contest's feed (there is no dedicated list endpoint) and filtered to your
  own `userId`.
- **Garmin**: uses the [`garminconnect`](https://pypi.org/project/garminconnect/)
  library.
- **Matching**: by `date + duration` (Activy copies Garmin's duration to the
  second), which is more robust than matching on distance.

## Development

```bash
pip install -e ".[dev]"
pytest --cov=activy_checker
```

The test suite runs fully offline: API clients are replaced with in-memory
fakes and all fixtures are synthetic, so no accounts or network are needed.

## Roadmap

- [x] Tests
- [ ] Documentation

## License

MIT — see [LICENSE](LICENSE).

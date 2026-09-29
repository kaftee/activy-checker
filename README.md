# activy-checker

[![tests](https://github.com/kaftee/activy-checker/actions/workflows/tests.yml/badge.svg)](https://github.com/kaftee/activy-checker/actions/workflows/tests.yml)

Check that your [Garmin Connect](https://connect.garmin.com) activities were
actually imported into [Activy](https://activy.app) — and get a clean summary of
your training from both sources.

Activy imports workouts from Garmin, but the import is not always complete: a
ride can silently never appear, or show up with the wrong distance. If Activy
powers a company or charity challenge, those gaps cost you points.
`activy-checker` logs into **your** two accounts, pulls your activities for a
date range and tells you exactly what is different.

```
Matched: 5 | Missing in Activy: 1 | Missing in Garmin: 0 | Distance mismatches: 1

-- Missing in Activy (present in Garmin, not imported) [1] --
  2026-05-10  road_biking          98.40 km  3:12:00
```

## Why I built this

Activy's import from Garmin is not 100% reliable. I found out by pure chance:
one day I noticed that an activity recorded on my Garmin had never appeared in
Activy. Nothing warned me — not the app, not Activy.

When I contacted Activy support, I was not told about any errors on their
side, and they were not willing to look at the history of my earlier
activities to check whether anything else was missing. I found that strange:
if one activity can silently go missing, others can too, and I had no way to
check.

That is why I wrote `activy-checker` — so that anyone can verify their own
Activy history against Garmin instead of relying on luck.

## Features

- **Missing in Activy** — activities recorded on Garmin that never reached Activy.
- **Missing in Garmin** — activities that exist only in Activy (e.g. manual entries).
- **Distance mismatches** — the same activity stored with a different distance.
- **Summaries** — count, distance and time per activity kind, for each source.
- **JSON export** of everything above, for your own scripts or a support ticket.
- Passwords are prompted with `getpass` and never stored; the Garmin session can
  optionally be cached so MFA is needed only once.

## Disclaimer

This is an **unofficial** tool, not affiliated with or endorsed by Activy or
Garmin. Activy has no public API, so `activy-checker` talks to the same mobile
endpoints the Activy app uses, signing in with your own credentials. Use it only
with **your own account and your own data**, at your own risk. The Activy API
can change without notice and break the tool.

## Quick start

Requires **Python 3.12+**.

```bash
git clone https://github.com/kaftee/activy-checker.git
cd activy-checker
python3 -m venv .venv && source .venv/bin/activate
pip install -e .

activy-checker --since 2026-09-01
```

You will be asked for your Activy email and password, then your Garmin email,
password and — if your Garmin account uses two-factor authentication — the MFA
code.

## Common commands

```bash
activy-checker                                   # from 2026-09-01 (default)
activy-checker --since 2026-09-01 --until 2026-09-30
activy-checker --activy-only                     # just summarize Activy
activy-checker --garmin-tokenstore ~/.garminconnect   # cache Garmin session
activy-checker --since 2026-09-01 --json result.json  # machine-readable output
```

All options are described in [docs/usage.md](docs/usage.md).

## Example output

```
== Activy ==

Kind       Count     Distance       Time
----------------------------------------
Bike           2     103.5 km    3:31:00
Run            2       9.3 km    1:27:00
Exercise       1       0.0 km    0:25:00
----------------------------------------
TOTAL          5     112.8 km    5:23:00

== Garmin ==

Kind       Count     Distance       Time
----------------------------------------
Bike           3     201.9 km    6:43:01
Run            1       5.2 km    0:32:01
Walk           1       9.9 km    0:55:01
Exercise       1       0.0 km    0:25:00
----------------------------------------
TOTAL          6     217.0 km    8:35:03

== Comparison: Activy vs Garmin ==

Matched: 5 | Missing in Activy: 1 | Missing in Garmin: 0 | Distance mismatches: 1

-- Missing in Activy (present in Garmin, not imported) [1] --
  2026-05-10  road_biking          98.40 km  3:12:00

-- Missing in Garmin (present in Activy only) [0] --
  (none)

-- Distance mismatches (same activity, different distance) [1] --
  2026-05-05  Activy    4.10 km  vs Garmin    9.87 km  (Δ -5.77 km)
```

(Sample data.) Note that the two summaries use each service's own categories:
Activy files Garmin walks and hikes under **Run**, so kinds are not expected to
line up one-to-one — the comparison matches individual activities, not kinds.

## Documentation

- [Usage](docs/usage.md) — every option, exit codes, JSON format, using it as a library
- [How it works](docs/how-it-works.md) — the Activy API, fetching, matching rules, type mapping
- [Troubleshooting](docs/troubleshooting.md) — login problems, Garmin rate limits, reading the results
- [Contributing](CONTRIBUTING.md) — development setup and tests
- [Changelog](CHANGELOG.md)

## Other integrations

`activy-checker` currently compares Activy with **Garmin Connect** only. If
you use Activy with **Strava**, **Polar**, **Suunto** or another service and
would like it supported, please
[open a feature request](https://github.com/kaftee/activy-checker/issues/new?template=feature_request.yml)
and tell us which service you use.

Found a bug? [Report it here](https://github.com/kaftee/activy-checker/issues/new?template=bug_report.yml).

## License

MIT — see [LICENSE](LICENSE).

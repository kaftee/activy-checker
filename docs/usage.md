# Usage

```
activy-checker [--since YYYY-MM-DD] [--until YYYY-MM-DD]
               [--activy-email EMAIL] [--garmin-email EMAIL]
               [--activy-only] [--garmin-tokenstore PATH]
               [--include-steps]
               [--duration-tolerance SECONDS] [--distance-tolerance KM]
               [--json PATH]
```

The tool runs in three steps:

1. Sign in to Activy and fetch your activities in the date range, then print a summary.
2. Sign in to Garmin Connect and fetch your activities in the same range, then print a summary.
3. Match the two lists and print the differences.

Progress messages and prompts go to **stderr**; the summaries and the
comparison go to **stdout**, so `activy-checker > report.txt` captures just the
report.

Reading Activy can take a minute or two for a longer date range (see
[how it works](how-it-works.md#why-activities-come-from-contest-feeds)). A live
progress line shows what is happening:

```
⠹ Scanning Activy feed: page 57, 21 of yours so far, reached 2026-09-14 (going back to 2026-09-01) ...
```

## Options

| Option | Default | Description |
|---|---|---|
| `--since YYYY-MM-DD` | `2026-09-01` | First day to include (by local start date). |
| `--until YYYY-MM-DD` | today | Last day to include. |
| `--activy-email EMAIL` | prompted | Activy login email. The password is always prompted. |
| `--garmin-email EMAIL` | prompted | Garmin login email. The password is always prompted. |
| `--activy-only` | off | Only fetch and summarize Activy; skip Garmin and the comparison. |
| `--garmin-tokenstore PATH` | none | Cache the Garmin session here and reuse it on later runs (see below). |
| `--include-steps` | off | Keep Activy step-count entries. They are excluded by default because they have no counterpart activity in Garmin and would always show up as "missing in Garmin". |
| `--duration-tolerance SECONDS` | `8` | Maximum difference in duration for two activities to be considered the same. |
| `--distance-tolerance KM` | `0.5` | A matched pair whose distances differ by more than this is reported as a distance mismatch. |
| `--json PATH` | none | Also write the full result to a JSON file. |

### Credentials

Passwords are read with Python's `getpass` (not echoed) and are only kept in
memory for the duration of the run. Nothing is written to disk except the
optional Garmin session cache.

### Caching the Garmin session

Garmin sign-in can require an MFA code and is rate limited, so repeated logins
are slow and occasionally blocked. With `--garmin-tokenstore` the session is
saved after the first successful login and reused afterwards:

```bash
activy-checker --garmin-tokenstore ~/.garminconnect
```

- `PATH` can be a **directory** (tokens are stored in `garmin_tokens.json`
  inside it) or a path to a **`.json` file**.
- The file is created with owner-only permissions (`0600`, directory `0700`)
  by the `garminconnect` library.
- On later runs you are not asked for Garmin credentials at all. If the saved
  session has expired, you are prompted again and the cache is refreshed.
- The file contains a refresh token that grants access to your Garmin account.
  Keep it private and never commit it.

The Activy session is not cached; you sign in to Activy on every run.

## Exit codes

| Code | Meaning |
|---|---|
| `0` | Success (differences found are **not** an error). |
| `2` | Activy failed: bad credentials, network error, or an unexpected response. |
| `3` | Garmin failed: bad credentials, MFA, rate limit, or network error. |
| `130` | Interrupted with Ctrl+C. |

## JSON output

`--json result.json` writes:

```json
{
  "activy": {
    "summary": {
      "by_kind": { "bike": { "count": 2, "distance_km": 103.5, "duration_s": 12660 } },
      "total": { "count": 5, "distance_km": 112.8, "duration_s": 19380 }
    },
    "activities": [
      {
        "source": "activy",
        "id": "…",
        "date": "2026-05-03",
        "start": "2026-05-03T08:00:00.000+02:00",
        "kind": "bike",
        "raw_type": "0",
        "distance_km": 42.0,
        "duration_s": 5400
      }
    ]
  },
  "garmin": { "summary": { "…": "…" }, "activities": [ "…" ] },
  "comparison": {
    "matched": 5,
    "missing_in_activy": [ { "…": "an activity object, as above" } ],
    "missing_in_garmin": [],
    "distance_mismatches": [
      { "date": "2026-05-05", "activy_km": 4.1, "garmin_km": 9.87, "delta_km": -5.77 }
    ]
  }
}
```

- `kind` is one of `bike`, `run`, `walk`, `swim`, `exercise`, `steps`, `other`
  (see [type mapping](how-it-works.md#activity-types)).
- `raw_type` is the source's own type: Activy's numeric `ActivityType`, or
  Garmin's `typeKey` such as `road_biking`.
- `delta_km` is `activy_km - garmin_km`; negative means Activy recorded less.
- With `--activy-only`, only the `activy` key is present.

## Using it as a library

```python
import getpass

from activy_checker import ActivyClient, GarminClient, compare, render_comparison, summarize

activy = ActivyClient()
activy.login("you@example.com", getpass.getpass("Activy password: "))
activy_acts = activy.get_activities(since="2026-09-01")

garmin = GarminClient(tokenstore="~/.garminconnect")
garmin.login("you@example.com", getpass.getpass("Garmin password: "))
garmin_acts = garmin.get_activities(since="2026-09-01", until="2026-09-30")

result = compare(activy_acts, garmin_acts, duration_tolerance_s=8, distance_tolerance_km=0.5)
print(render_comparison(result))
print(summarize(garmin_acts)["total"])

for missing in result.only_garmin:
    print(missing.date, missing.raw_type, missing.distance_km, missing.duration_hms)
```

Every activity is an `Activity` dataclass with `source`, `id`, `date`, `start`,
`kind`, `raw_type`, `distance_km`, `duration_s` and the original API payload in
`raw`. `CompareResult` has `matched` (a list of `Match` pairs), `only_garmin`,
`only_activy` and `distance_mismatches`.

The library does not apply the CLI's defaults: `ActivyClient.get_activities`
has no end date and includes step entries (kind `steps`), so filter those
yourself if needed.

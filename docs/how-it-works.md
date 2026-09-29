# How it works

```
activy_checker/
├── activy.py    Activy client: sign-in, feed pagination, parsing
├── garmin.py    Garmin client: thin wrapper over the garminconnect library
├── models.py    Activity dataclass shared by both sources
├── compare.py   Matching and difference detection
├── report.py    Summaries and text output
└── cli.py       Command-line entry point
```

Both clients return lists of the same `Activity` type, so the matching and
reporting code does not care where an activity came from.

## Activy

Activy has no public API. The client uses the endpoints of the Activy mobile
app, which are unofficial and may change.

### Sign-in

Activy runs a standard OpenID Connect server. The client uses the *resource
owner password* grant — the same flow the app uses when you sign in with email
and password:

```
POST https://players.v3.activy.pl/auth/connect/token
Content-Type: application/x-www-form-urlencoded

grant_type=password&client_id=activy.mobile&username=…&password=…
&scope=openid profile email offline_access activy.rides activy.players activy.contests activy.rankings
```

The response contains an `access_token`, sent as `Authorization: Bearer …` on
every later request. Your user id is read from the standard `userinfo`
endpoint (`sub` claim) and is used to recognise your own activities.

### Queries

Data is read with CQRS-style queries — a `POST` to
`https://<service>.v3.activy.pl/api/query/<contract name>` with a JSON body in
PascalCase:

| Query | Service | Used for |
|---|---|---|
| `Activy.Contests.Contracts.Mobile.Contests.MyContests` | `contests` | Contests you have joined |
| `Activy.Players.Contracts.Mobile.Newsfeed.UserContestFeed` | `players` | A contest's activity feed (needs `ContestId` **and** your `UserId`) |
| `Activy.Players.Contracts.Mobile.Newsfeed.ContestFeed` | `players` | Fallback feed if the one above is unavailable |

### Why activities come from contest feeds

The app has no "list my activities" query. Your activities are visible as
`Ride` entries in the feeds of the contests you take part in, so the client:

1. Lists your contests with `MyContests`.
2. For each contest, pages through the feed (`Page` = 0, 1, 2, …, `PageSize` = 50).
3. Keeps only `Ride` entries whose `UserId` is yours, dated on or after `--since`.
4. De-duplicates by `ActivityId` (an activity can appear in several contests or pages).

A contest feed contains **everyone's** activities, newest first, so reaching a
date a few weeks back in a large contest can take a hundred or more requests.
Paging stops as soon as:

- a full page is older than `--since`,
- the feed returns the same page again (it ignores paging), or
- 500 pages have been read (safety limit).

While this runs, the CLI shows a progress line on stderr — the current page,
how many of your activities were found so far and how far back the feed has
reached. It is only drawn when stderr is a terminal.

Consequence: Activy activities are only found if you are in at least one
contest. That is the normal way Activy is used, but see
[troubleshooting](troubleshooting.md#activy-returns-no-activities).

### Fields used

| Activy field | Becomes | Notes |
|---|---|---|
| `ActivityId` | `id` | |
| event `Date` | `date`, `start` | Local start time with offset |
| `ActivityType` | `kind`, `raw_type` | See [activity types](#activity-types) |
| `Distance` | `distance_km` | Already in km |
| `Time` | `duration_s` | Format `d.hh:mm:ss.fff`, e.g. `0.01:27:09.000` |

## Garmin

Garmin access uses the [`garminconnect`](https://pypi.org/project/garminconnect/)
library (`get_activities_by_date`). Distances arrive in metres and are converted
to km; `duration` is in seconds. With `--garmin-tokenstore` the library loads a
saved session, or performs a fresh login (with MFA if required) and saves the
new session there.

## Matching

Activy copies the duration of an imported activity from Garmin almost to the
second, while the distance can be rounded or changed. Duration on the same day
is therefore the most reliable key:

- An Activy and a Garmin activity match when they start on the **same date**
  and their durations differ by at most `--duration-tolerance` seconds
  (default 8).
- If several Garmin activities qualify, the one with the **closest duration**
  wins.
- Each Garmin activity can be matched **at most once**.

Everything is then sorted into:

| Result | Meaning |
|---|---|
| `matched` | Pairs found in both services |
| `only_garmin` | **Missing in Activy** — on Garmin, never imported |
| `only_activy` | **Missing in Garmin** — only in Activy (manual entries, other sources) |
| `distance_mismatches` | Matched pairs whose distance differs by more than `--distance-tolerance` km (default 0.5) |

Small differences such as 3.06 vs 3.1 km are rounding and are not reported.

## Activity types

Each source's type is mapped to a common `kind` for the summaries. Matching does
**not** use `kind` — only date and duration — so a Garmin walk that Activy
files under "Run" still matches.

### Activy `ActivityType`

| Value | `kind` | Notes |
|---|---|---|
| `0` | `bike` | |
| `1` | `run` | Activy also puts Garmin walks and hikes here |
| `2` | `exercise` | Includes Garmin cardio and swimming |
| `3` | `steps` | Step-count entries; excluded by the CLI unless `--include-steps` |
| other | `other` | |

### Garmin `typeKey`

| `typeKey` | `kind` |
|---|---|
| `road_biking`, `mountain_biking`, `gravel_cycling`, `cycling`, `virtual_ride`, `indoor_cycling` | `bike` |
| `running`, `trail_running`, `treadmill_running`, `track_running` | `run` |
| `walking`, `hiking`, `casual_walking` | `walk` |
| `swimming`, `open_water_swimming`, `lap_swimming` | `swim` |
| `indoor_cardio`, `strength_training`, `yoga`, `fitness_equipment` | `exercise` |
| anything else | `other` |

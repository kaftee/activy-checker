# Troubleshooting

## Signing in

### `Activy error: Activy login failed (HTTP 400)`

The email or password is wrong. The tool signs in with an email and password,
exactly like the "log in with email" option in the Activy app — check that the
same credentials work there.

If you normally sign in to Activy **with Apple or Facebook**, your account may
not have a password at all. Setting one with "Forgot password" in the app may
help, but this is untested.

### `Activy error: <urlopen error …>`

A network problem: no connection, a proxy, or a firewall blocking
`*.v3.activy.pl`. Check that you can reach
`https://players.v3.activy.pl/auth/.well-known/openid-configuration` in a browser.

### Garmin prints `… returned 429 … rate limited` but continues

The `garminconnect` library tries several sign-in strategies. Garmin
rate-limits some of them, so warnings like these are normal as long as the run
continues and ends with your activities:

```
mobile+cffi returned 429: GarminConnectTooManyRequestsError: …
mobile+requests returned 429: GarminConnectTooManyRequestsError: …
```

### `Garmin error: … 429 …` and the run stops

All sign-in strategies were rate limited. Wait a while before trying again, and
avoid repeated logins by caching the session:

```bash
activy-checker --garmin-tokenstore ~/.garminconnect
```

After one successful login, later runs reuse the session and do not sign in
again.

### I'm asked for a Garmin MFA code every time

Use `--garmin-tokenstore`; the code is then only needed when the saved session
expires.

### `Found old garth-format tokens … no longer supported`

The token store holds a session saved by an old version of `garminconnect`.
Delete it (or point `--garmin-tokenstore` somewhere new) and sign in once with
your password.

## Reading the results

### An activity is "Missing in Activy"

It exists in Garmin but Activy never imported it. The tool cannot see why —
the activity simply is not in Activy. Possible reasons include:

- The Garmin → Activy connection was broken or re-authorised around that time.
- Activy rejected or held it, e.g. as a suspected duplicate or during verification.
- The activity type is not accepted by the contest.

The fix is on Activy's side: check the Garmin connection in the app, or
contact Activy support. The `--json` output lists the missing activities with dates, types,
distances and durations, which is handy for a support request.

### An activity is "Missing in Garmin"

It exists only in Activy — typically a manual entry, or an activity from
another source such as Apple Health, Strava or the Activy app's own GPS
recording. This is informational, not an error.

### A "distance mismatch"

Both services have the activity (same day, same duration), but Activy stored a
different distance. Activy can edit activities after import (its app has
notices for GPS problems and automatic edits), which is one likely cause. Only
differences above `--distance-tolerance` (0.5 km by default) are reported.

### Something matched the wrong activity, or did not match at all

Matching uses the start date and duration (±8 s by default). Two activities
can fail to match when:

- An activity crosses midnight, or the two services record the start in
  different time zones, so the dates differ.
- The durations differ by more than the tolerance. Try
  `--duration-tolerance 30`.

### The two summaries show different kinds

That is expected. Each service has its own categories — for example, Activy
records Garmin walks and hikes as **Run**, and swims and cardio as
**Exercise**. See [activity types](how-it-works.md#activity-types). The
comparison works on individual activities, so this does not affect it.

### Activy returns no activities

Activy activities are read from the feeds of contests you have joined. If you
are not in any contest, nothing is found. Also check the date range: the
default is only the last 30 days.

Version 0.2.0 had a bug that always returned no Activy activities after a long
wait; upgrade to 0.2.1 or later.

## Something else

The Activy API is unofficial and may change. If the tool suddenly stops
finding activities that you can see in the app, please
[open an issue](https://github.com/kaftee/activy-checker/issues) — without
pasting passwords, tokens, or personal data.

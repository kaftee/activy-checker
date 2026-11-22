# Security policy

## Supported versions

Only the latest release on [PyPI](https://pypi.org/project/activy-checker/)
receives fixes.

## Reporting a vulnerability

Please **do not open a public issue** for a security problem. Report it
privately through GitHub instead:
[Report a vulnerability](https://github.com/kaftee/activy-checker/security/advisories/new).

Include what you found, how to reproduce it and what it affects. You can expect
a first answer within a week.

## How credentials are handled

- The Activy and Garmin passwords are asked for with `getpass` on every run
  that needs them and are never stored or logged.
- The Activy access token is kept in memory only, for the length of the run.
- With `--garmin-tokenstore`, the `garminconnect` library caches the Garmin
  session in that directory; anyone who can read it can use your Garmin
  session. Without the option nothing is written.
- Nothing is sent anywhere except Activy (`*.v3.activy.pl`) and Garmin Connect.

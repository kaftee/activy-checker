# Contributing

Thanks for helping! Bug reports, fixes and support for new activity types are
all welcome.

## Development setup

Requires Python 3.12+.

```bash
git clone https://github.com/kaftee/activy-checker.git
cd activy-checker
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

## Running the tests

```bash
pytest                                   # quick run
pytest --cov=activy_checker --cov-report=term-missing
```

The suite runs fully **offline**. The Activy and Garmin clients are replaced by
in-memory fakes (see `tests/conftest.py` and the `Fake*` classes in the tests),
so no accounts or network access are needed. CI runs the same tests on
Python 3.12, 3.13 and 3.14 for every push and pull request.

## Guidelines

- **Never commit personal data.** Test fixtures must be synthetic: no real
  emails, user ids, activity ids, tokens, or exported API responses from a real
  account. `.gitignore` already excludes token files and local exports.
- Add or update tests for any behaviour change.
- Keep the Activy client dependency-free (standard library only).
- When adding a Garmin `typeKey` or an Activy `ActivityType`, update the
  mapping, its test, and the tables in [docs/how-it-works.md](docs/how-it-works.md).
- Code, comments and documentation are in English.

## Reporting a bug

Please include the command you ran, the error output, and your Python and
`garminconnect` versions (`pip show garminconnect`). Remove any email
addresses, tokens and activity details you do not want to share.

# Contributing

Thanks for helping! Bug reports, fixes and support for new activity types are
all welcome.

Would you like another service compared with Activy (Strava, Polar, Suunto, …)?
Please [open a feature request](https://github.com/kaftee/activy-checker/issues/new?template=feature_request.yml)
first, so we can discuss it before any code is written.

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

## Linting

```bash
ruff check .          # the same check CI runs
ruff check --fix .    # apply the safe automatic fixes
```

The rules are in `pyproject.toml` (`[tool.ruff]`). Dependabot proposes updates
for the dependencies and for the GitHub Actions, which are pinned to commit
SHAs, once a month.

## Guidelines

- **Never commit personal data.** Test fixtures must be synthetic: no real
  emails, user ids, activity ids, tokens, or exported API responses from a real
  account. `.gitignore` already excludes token files and local exports.
- Add or update tests for any behaviour change.
- Keep the Activy client dependency-free (standard library only).
- When adding a Garmin `typeKey` or an Activy `ActivityType`, update the
  mapping, its test, and the tables in [docs/how-it-works.md](docs/how-it-works.md).
- Code, comments and documentation are in English.

## Releasing (maintainers)

Releases are published to PyPI by the `publish` GitHub Actions workflow using
[Trusted Publishing](https://docs.pypi.org/trusted-publishers/), so no API
tokens are stored anywhere.

1. Bump `version` in `pyproject.toml` (the only place it is set:
   `activy_checker.__version__` reads it from the installed package) and turn
   the `Unreleased` section of `CHANGELOG.md` into the new version.
2. Create a GitHub release with tag `vX.Y.Z` matching the version. Publishing
   the release runs the `publish` workflow, which waits for a maintainer to
   approve the `pypi` environment and then uploads to PyPI.

## Reporting a bug

Please include the command you ran, the error output, and your Python and
`garminconnect` versions (`pip show garminconnect`). Remove any email
addresses, tokens and activity details you do not want to share.

A security problem goes through a private report instead, see
[SECURITY.md](SECURITY.md).

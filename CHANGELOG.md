# Changelog

## 0.2.0

### Fixed
- `--garmin-tokenstore` now works: the Garmin session is actually saved after
  the first login (the previous code targeted an API removed in
  `garminconnect` 0.3), and the first run prompts for the password instead of
  failing.
- Matching picks the Garmin activity with the closest duration, not the first
  one within the tolerance.
- Network errors are reported as `Activy error: …` / `Garmin error: …` with
  exit codes 2 / 3 instead of a traceback.
- Per-kind distances in the JSON summary are rounded.

### Added
- Activy step-count entries are excluded by default; `--include-steps` keeps them.
- `--duration-tolerance` and `--distance-tolerance` options.
- Documentation: usage, how it works, troubleshooting, contributing.

### Changed
- Requires Python 3.12+ (the minimum supported by `garminconnect`).

## 0.1.0

- Initial release: fetch activities from Activy and Garmin Connect, report
  activities missing in either service and distance mismatches, per-kind
  summaries and JSON export.
- Offline test suite and CI.

# Changelog

All notable changes to this project are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and version numbers
follow [Semantic Versioning](https://semver.org/).

## [1.1.0] - 2026-09-28

Checks and tests only. The tool's output is unchanged.

### Added

- A test that runs `change_control.py` end to end on the sample data and checks the README's Result block against what it actually prints, so the README can't drift from the code.
- A check that the committed `assets/report.md` is exactly what the script regenerates.
- Regression tests for the code-review fixes already in 1.0.0: a Cancelled change with no decision date isn't counted as decided, sign-first negative amounts, a missing cycle time shown as N/A, "n/a" rather than "None" in the markdown report, and markdown-safe free text.
- A test that pins the chart colors and styling shared across all six toolkit repos.
- ruff linting, run locally from `ruff.toml` and as its own CI job.
- CI now tests on Python 3.11 and 3.12, matching the "Python 3.11+" badge.
- `.gitattributes` keeps line endings consistent (LF) on every OS.

### Changed

- Removed an unused import in the tests, flagged by the new lint rules.

## [1.0.0] - 2026-09-13

First tagged release, marking the state of the repo before this changelog started. Change log metrics: approval rate, decision cycle time, stale pending changes, and cumulative approved cost and schedule impact, with charts and a markdown report. Includes the fixes from code review, a pytest suite and CI.

[1.1.0]: https://github.com/alexc-hue/change-control-register/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/alexc-hue/change-control-register/releases/tag/v1.0.0

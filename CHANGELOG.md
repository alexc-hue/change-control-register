# Changelog

All notable changes to this project are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and version numbers
follow [Semantic Versioning](https://semver.org/).

## [1.2.1] - 2026-11-12

Maintenance release. The tool's output is unchanged.

### Changed

- `pytest>=9.0.3` in `requirements-dev.txt` (was `>=7.0`).
- CI runs the tests on Python 3.11, 3.12, 3.13 and 3.14 (was 3.11 and 3.12).
- CI actions are updated (checkout v7.0.1, setup-python v7.1.0, codecov-action v7.1.1) and pinned
  to commit SHAs, not tags.
- README: the list of related repos is the same in all eight repos now. It names the six toolkit
  tools, then the two data center practice models separately.
- README: long dashes replaced with plain punctuation.
- `.gitignore` also covers `.env` files, ruff and coverage caches, build output and editor folders.

## [1.2.0] - 2026-09-28

Performance at larger sizes. Output is unchanged: the console report and report.md are byte-identical to the previous release on the sample data and on generated inputs, and every chart renders pixel-identical on the sample data, so no committed image changed. The only visible difference is on inputs larger than a chart's cap, where the chart now shows a subset and says so in its title.

### Added

- `benchmarks/size_test.py`, a hand-run size test: generates bigger inputs, runs the tool end to end
  and prints run time and peak memory. Not part of CI or the test suite.
- Measured size-test numbers in the README's Limitations section.
- Tests for the chart cap.

### Changed

- The cycle-time chart shows at most the 30 changes that waited longest, built in one pass. 10,000
  changes went from about 12 minutes to about 4 seconds.

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

[1.2.1]: https://github.com/alexc-hue/change-control-register/compare/v1.2.0...v1.2.1
[1.2.0]: https://github.com/alexc-hue/change-control-register/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/alexc-hue/change-control-register/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/alexc-hue/change-control-register/releases/tag/v1.0.0

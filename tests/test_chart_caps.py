"""The cycle-time chart caps itself at CHART_TOP_N changes; the reports don't."""

from __future__ import annotations

import pandas as pd

import change_control


def _changes(n: int) -> pd.DataFrame:
    pending = [i % 3 == 0 for i in range(n)]
    return pd.DataFrame({
        "change_id": [f"C{i:03d}" for i in range(n)],
        "date_raised": pd.date_range("2026-01-01", periods=n, freq="D"),
        "status": ["Pending" if p else "Approved" for p in pending],
        "days_open": [i if p else pd.NA for i, p in enumerate(pending)],
        "cycle_days": [pd.NA if p else i for i, p in enumerate(pending)],
        "is_stale": [p and i > 30 for i, p in enumerate(pending)],
    })


def test_small_logs_are_charted_in_full_in_raised_order():
    rows = change_control._cycle_time_rows(_changes(10))
    assert list(rows["change_id"]) == [f"C{i:03d}" for i in range(10)]
    assert list(rows["chart_days"]) == list(range(10))


def test_large_logs_chart_the_longest_waits_in_raised_order():
    rows = change_control._cycle_time_rows(_changes(100))
    assert len(rows) == change_control.CHART_TOP_N
    assert set(rows["chart_days"]) == set(range(70, 100))
    assert list(rows["date_raised"]) == sorted(rows["date_raised"])

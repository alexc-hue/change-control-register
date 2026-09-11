"""Tests for src/metrics.py: cycle/aging, cumulative impact, summary stats.

Small hand-built change log, not the repo's sample CSV. Rows are chosen to
exercise the "approved but missing a decision date" edge case explicitly --
that's the bug summary_stats' approval_rate_pct fix addresses.
"""

from __future__ import annotations

import math

import pandas as pd
import pytest

from src.metrics import add_cycle_and_aging, cumulative_impact, summary_stats


def _changes():
    return pd.DataFrame({
        "change_id": ["C1", "C2", "C3", "C4", "C5"],
        "date_raised": pd.to_datetime([
            "2026-01-01", "2026-01-02", "2026-01-03", "2026-01-04", "2026-01-05",
        ]),
        # C2 is Approved but has no recorded decision date -- the data-quality
        # gap approval_rate_pct's fix is specifically about.
        "date_decided": pd.to_datetime([
            "2026-01-05", None, "2026-01-10", None, "2026-01-06",
        ]),
        "status": ["Approved", "Approved", "Rejected", "Pending", "Approved"],
        "cost_impact": [1000, 1500, 500, 2000, 3000],
        "schedule_impact_days": [2, 3, 0, 5, 1],
    })


def test_add_cycle_and_aging_cycle_days_for_decided_rows():
    out = add_cycle_and_aging(_changes(), status_date="2026-03-01")
    by_id = out.set_index("change_id")

    assert by_id.loc["C1", "cycle_days"] == 4
    assert by_id.loc["C3", "cycle_days"] == 7
    assert by_id.loc["C5", "cycle_days"] == 1


def test_add_cycle_and_aging_approved_without_decision_date_has_no_cycle_days():
    """C2 is Approved (not Pending) but never got a decision date -- it must
    not be silently treated as decided just because it isn't Pending."""
    out = add_cycle_and_aging(_changes(), status_date="2026-03-01")
    by_id = out.set_index("change_id")
    assert pd.isna(by_id.loc["C2", "cycle_days"])


def test_add_cycle_and_aging_pending_days_open_and_stale_flag():
    out = add_cycle_and_aging(_changes(), status_date="2026-03-01")
    by_id = out.set_index("change_id")

    assert by_id.loc["C4", "days_open"] == 56  # 2026-01-04 -> 2026-03-01
    assert bool(by_id.loc["C4", "is_stale"]) is True  # > STALE_PENDING_DAYS (30)
    assert bool(by_id.loc["C1", "is_stale"]) is False  # not pending at all


def test_summary_stats_approval_rate_and_missing_decision_date():
    """The fix under test: approval_rate_pct's numerator (approved AND
    decided) must be a subset of its denominator (decided), and an approved
    change missing its decision date must be surfaced separately rather than
    silently pushing the rate above 100%."""
    aged = add_cycle_and_aging(_changes(), status_date="2026-03-01")
    stats = summary_stats(aged)

    # decided = C1, C3, C5 (3 rows). approved_decided = C1, C5 (2 rows) --
    # C2 is Approved but not "decided", so it's excluded from the numerator.
    assert stats["approved_missing_decision_date"] == 1
    assert stats["approval_rate_pct"] == pytest.approx(66.7)
    assert stats["approval_rate_pct"] <= 100.0


def test_summary_stats_counts_and_cost_totals():
    aged = add_cycle_and_aging(_changes(), status_date="2026-03-01")
    stats = summary_stats(aged)

    assert stats["total_changes"] == 5
    assert stats["approved_count"] == 3
    assert stats["rejected_count"] == 1
    assert stats["pending_count"] == 1
    assert stats["stale_pending_count"] == 1
    assert stats["avg_cycle_days"] == pytest.approx(4.0)  # mean of 4, 7, 1
    assert stats["approved_cost_impact"] == 5500
    assert stats["approved_schedule_days"] == 6
    assert stats["pending_cost_exposure"] == 2000
    assert stats["pending_schedule_exposure_days"] == 5


def test_summary_stats_no_decided_rows_returns_none_not_nan():
    changes = pd.DataFrame({
        "change_id": ["C1"],
        "date_raised": pd.to_datetime(["2026-01-01"]),
        "date_decided": pd.to_datetime([None]),
        "status": ["Pending"],
        "cost_impact": [100],
        "schedule_impact_days": [1],
    })
    aged = add_cycle_and_aging(changes, status_date="2026-01-10")
    stats = summary_stats(aged)
    assert stats["approval_rate_pct"] is None
    assert stats["avg_cycle_days"] is None


def test_cumulative_impact_running_totals_ordered_by_decision_date():
    cum = cumulative_impact(_changes())
    # Approved only: C1 (decided 01-05), C5 (01-06), C2 (decided NaT, sorts last).
    assert list(cum["change_id"]) == ["C1", "C5", "C2"]
    assert list(cum["cum_cost"]) == [1000, 4000, 5500]
    assert list(cum["cum_schedule_days"]) == [2, 3, 6]

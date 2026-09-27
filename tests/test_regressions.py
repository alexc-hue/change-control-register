"""Regression tests for bugs fixed in commits 5e148b6 and 0bda9ab.

Each test was confirmed to fail with its fix temporarily reverted before
being committed.
"""

from __future__ import annotations

import pandas as pd
import pytest

import change_control
from src.formatting import money
from src.metrics import add_cycle_and_aging, summary_stats

STATUS_DATE = "2026-02-01"


def _changes(statuses, decided_dates):
    n = len(statuses)
    return pd.DataFrame({
        "change_id": [f"C{i}" for i in range(1, n + 1)],
        "date_raised": pd.to_datetime(["2026-01-01"] * n),
        "date_decided": pd.to_datetime(decided_dates),
        "status": statuses,
        "cost_impact": [1000] * n,
        "schedule_impact_days": [1] * n,
        "category": ["Scope"] * n,
        "description": ["test"] * n,
    })


# --- 5e148b6 -----------------------------------------------------------------

def test_cancelled_change_without_decision_date_is_not_counted_as_decided():
    """"Decided" means a decision date exists, not "status isn't Pending".
    A Cancelled change with no date must stay out of the approval-rate
    denominator."""
    changes = add_cycle_and_aging(
        _changes(["Approved", "Rejected", "Cancelled"], ["2026-01-05", "2026-01-10", None]),
        STATUS_DATE,
    )
    stats = summary_stats(changes)
    assert stats["approval_rate_pct"] == pytest.approx(50.0)


def test_negative_money_puts_the_sign_before_the_symbol():
    assert money(-9000) == "-$9,000"
    assert money(9000) == "$9,000"


def test_timing_str_falls_back_when_cycle_days_is_missing():
    row = {"status": "Approved", "cycle_days": pd.NA, "days_open": pd.NA, "is_stale": False}
    assert change_control.timing_str(row) == "decided in N/A"


# --- 0bda9ab -----------------------------------------------------------------

def test_markdown_report_says_n_a_when_nothing_is_decided(monkeypatch, tmp_path):
    """With no decided changes the approval rate is None; the markdown report
    has to print 'n/a', not the string 'None'."""
    changes = add_cycle_and_aging(_changes(["Pending", "Pending"], [None, None]), STATUS_DATE)
    stats = summary_stats(changes)
    assert stats["approval_rate_pct"] is None

    monkeypatch.setattr(change_control, "ASSETS_DIR", str(tmp_path))
    change_control.write_report_markdown(changes, stats)
    report = (tmp_path / "report.md").read_text(encoding="utf-8")

    assert "**Approval rate:** n/a%" in report
    assert "None" not in report


def test_free_text_cannot_break_the_markdown_table():
    assert change_control._escape_md_cell("a|b\nc") == r"a\|b c"
    assert change_control._escape_md_cell(float("nan")) == ""

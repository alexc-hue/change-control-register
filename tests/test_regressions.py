"""Regression tests for bugs fixed in commits 5e148b6 and 0bda9ab, and in 1.2.2.

Each test was confirmed to fail with its fix temporarily reverted (or, for
1.2.2, before the fix was written) before being committed.
"""

from __future__ import annotations

import pandas as pd
import pytest

import change_control
from src.formatting import money
from src.metrics import (
    add_cycle_and_aging,
    cumulative_impact,
    load_change_log,
    summary_stats,
)

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


# --- 1.2.2 -------------------------------------------------------------------

def test_status_matching_ignores_case_and_whitespace():
    """"pending" or " Approved" used to vanish from every count with no warning."""
    changes = add_cycle_and_aging(
        _changes(["pending", " Approved", "REJECTED ", "Pending"], [None, "2026-01-05", "2026-01-10", None]),
        "2026-03-01",
    )
    stats = summary_stats(changes)
    assert (stats["pending_count"], stats["approved_count"], stats["rejected_count"]) == (2, 1, 1)
    assert stats["stale_pending_count"] == 2
    assert list(changes["status"]) == ["Pending", "Approved", "Rejected", "Pending"]
    assert list(cumulative_impact(changes)["change_id"]) == ["C2"]


def test_load_change_log_tidies_status(tmp_path):
    path = tmp_path / "log.csv"
    path.write_text(
        "change_id,date_raised,date_decided,status,cost_impact,schedule_impact_days\n"
        "C1,2026-01-01,,  pending ,100,1\n"
        "C2,2026-01-02,2026-01-04,approved,200,2\n"
        "C3,2026-01-03,,On Hold,300,3\n",
        encoding="utf-8",
    )
    assert list(load_change_log(str(path))["status"]) == ["Pending", "Approved", "On Hold"]


def test_cycle_and_aging_columns_are_numeric_not_object():
    """pd.NA made these object columns, so comparisons and sums went through slow
    object paths that depend on pandas' NA rules."""
    changes = add_cycle_and_aging(_changes(["Approved", "Pending"], ["2026-01-05", None]), STATUS_DATE)
    assert changes["cycle_days"].dtype == "float64"
    assert changes["days_open"].dtype == "float64"
    assert changes["is_stale"].dtype == bool


def test_money_does_not_print_minus_zero():
    assert money(-0.4) == "$0"
    assert money(-0.6) == "-$1"
    assert money(0.4) == "$0"

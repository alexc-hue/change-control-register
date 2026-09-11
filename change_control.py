"""
Change Control Register
-------------------------
Tracks a project's change log over time: cumulative approved cost and
schedule impact (budget/schedule creep), decision cycle time, and stale
pending changes that have sat undecided too long.

Run:
    pip install -r requirements.txt
    python change_control.py
"""

import os

import matplotlib.pyplot as plt
import pandas as pd

from src import chart_style, metrics
from src.formatting import money

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")

# Edit this to match your own project -- see README ("point this at your own
# data"). It isn't read from the CSV: STATUS_DATE is this fictional change
# log's own reporting cutoff.
STATUS_DATE = "2026-08-01"


def timing_str(row, stale_marker: str = "[STALE]") -> str:
    """Human-readable timing for one change log row.

    Shared by the console report and the markdown writer so the
    pending/stale-marker logic only lives in one place. `stale_marker` lets
    each caller use its own formatting (plain text vs. markdown bold).
    """
    if row["status"] == "Pending":
        return f"open {int(row['days_open'])}d" + (f" {stale_marker}" if row["is_stale"] else "")
    if pd.notna(row["cycle_days"]):
        return f"decided in {int(row['cycle_days'])}d"
    return "decided in N/A"


def print_report(changes, stats: dict) -> None:
    print("=" * 64)
    print("CHANGE CONTROL REPORT")
    print("=" * 64)
    print(f"Total changes logged: {stats['total_changes']}  "
          f"(Approved {stats['approved_count']}, Rejected {stats['rejected_count']}, "
          f"Pending {stats['pending_count']})")
    approval_rate = stats["approval_rate_pct"]
    print(f"Approval rate (of decided changes): "
          f"{approval_rate if approval_rate is not None else 'n/a'}%")
    avg_cycle = stats["avg_cycle_days"]
    print(f"Average decision cycle time: {avg_cycle if avg_cycle is not None else 'n/a'} days")
    print(f"Stale pending changes (open > {metrics.STALE_PENDING_DAYS}d): {stats['stale_pending_count']}")
    if stats["approved_missing_decision_date"]:
        print(f"Data quality: {stats['approved_missing_decision_date']} Approved change(s) "
              f"missing a decision date, excluded from the approval rate above")
    print()
    print(f"Approved cost impact:     {money(stats['approved_cost_impact'])}")
    print(f"Approved schedule impact: {stats['approved_schedule_days']:+d} days")
    print(f"Pending cost exposure:    {money(stats['pending_cost_exposure'])}")
    print(f"Pending schedule exposure: {stats['pending_schedule_exposure_days']:+d} days")

    print()
    print("-" * 64)
    print("CHANGE LOG")
    print("-" * 64)
    for _, row in changes.iterrows():
        timing = timing_str(row, stale_marker="[STALE]")
        print(f"  {row['change_id']:<5} {money(row['cost_impact']):>10}  "
              f"{row['schedule_impact_days']:+3d}d  ({row['category']}, {row['status']})  "
              f"{timing}  {row['description']}")


def chart_cumulative(cum, value_col: str, ylabel: str, title: str, filename: str) -> None:
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.step(cum["date_decided"].to_numpy(), cum[value_col].to_numpy(), where="post",
            color=chart_style.SERIES_1, linewidth=2)
    ax.scatter(cum["date_decided"].to_numpy(), cum[value_col].to_numpy(), color=chart_style.SERIES_1, s=20, zorder=3)
    ax.axhline(0, color=chart_style.INK, linewidth=0.8, alpha=0.6)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.grid(color=chart_style.GRID, linewidth=0.6)
    chart_style.apply_chrome(fig, ax)
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(os.path.join(ASSETS_DIR, filename), dpi=140, facecolor=chart_style.CHART_BG)
    plt.close(fig)


def chart_cycle_time(changes) -> None:
    fig, ax = plt.subplots(figsize=(9, 6))
    labels, values, colors = [], [], []
    for _, row in changes.sort_values("date_raised").iterrows():
        labels.append(f"{row['change_id']} ({row['status']})")
        if row["status"] == "Pending":
            values.append(row["days_open"])
            colors.append(chart_style.STATUS_CRITICAL if row["is_stale"] else chart_style.STATUS_WARNING)
        else:
            values.append(row["cycle_days"])
            colors.append(chart_style.STATUS_GOOD)
    ax.barh(labels, values, color=colors)
    threshold_line = ax.axvline(
        metrics.STALE_PENDING_DAYS, color=chart_style.BASELINE, linestyle="--", linewidth=1,
        label=f"Stale threshold ({metrics.STALE_PENDING_DAYS}d)",
    )
    ax.set_xlabel("Days")
    ax.set_title("Decision Cycle Time / Days Open")
    handles = [
        plt.Rectangle((0, 0), 1, 1, color=chart_style.STATUS_GOOD, label="Decided"),
        plt.Rectangle((0, 0), 1, 1, color=chart_style.STATUS_WARNING, label="Pending"),
        plt.Rectangle((0, 0), 1, 1, color=chart_style.STATUS_CRITICAL, label="Pending, stale"),
        threshold_line,
    ]
    ax.legend(handles=handles, fontsize=8)
    ax.grid(color=chart_style.GRID, linewidth=0.6, axis="x")
    chart_style.apply_chrome(fig, ax)
    fig.tight_layout()
    fig.savefig(os.path.join(ASSETS_DIR, "cycle_time.png"), dpi=140, facecolor=chart_style.CHART_BG)
    plt.close(fig)


def _escape_md_cell(value) -> str:
    """Escape/normalize a free-text value so it can't corrupt a markdown table.

    A raw `|` splits into extra columns, a backslash can escape the delimiter
    that follows it, and embedded newlines break the row onto multiple lines.
    """
    if value is None or value != value:  # covers None and NaN (NaN != NaN)
        return ""
    text = str(value)
    text = text.replace("\\", "\\\\").replace("|", "\\|")
    return text.replace("\r\n", " ").replace("\n", " ").replace("\r", " ")


def write_report_markdown(changes, stats: dict) -> None:
    approval_rate = stats["approval_rate_pct"]
    avg_cycle = stats["avg_cycle_days"]
    lines = [
        "# Change Control Report",
        "",
        f"**Total changes logged:** {stats['total_changes']} "
        f"(Approved {stats['approved_count']}, Rejected {stats['rejected_count']}, "
        f"Pending {stats['pending_count']})  ",
        f"**Approval rate:** {approval_rate if approval_rate is not None else 'n/a'}%  ",
        f"**Average decision cycle time:** {avg_cycle if avg_cycle is not None else 'n/a'} days  ",
        f"**Stale pending changes (open > {metrics.STALE_PENDING_DAYS}d):** {stats['stale_pending_count']}",
    ]
    if stats["approved_missing_decision_date"]:
        lines.append(
            f"**Data quality:** {stats['approved_missing_decision_date']} Approved change(s) missing a "
            f"decision date, excluded from the approval rate above"
        )
    lines += [
        "",
        f"**Approved cost impact:** {money(stats['approved_cost_impact'])}  ",
        f"**Approved schedule impact:** {stats['approved_schedule_days']:+d} days  ",
        f"**Pending cost exposure:** {money(stats['pending_cost_exposure'])}  ",
        f"**Pending schedule exposure:** {stats['pending_schedule_exposure_days']:+d} days",
        "",
        "## Change Log",
        "",
        "| Change | Cost Impact | Schedule Impact | Category | Status | Timing | Description |",
        "|---|---|---|---|---|---|---|",
    ]
    for _, row in changes.iterrows():
        timing = timing_str(row, stale_marker="**STALE**")
        lines.append(
            f"| {row['change_id']} | {money(row['cost_impact'])} | {row['schedule_impact_days']:+d}d "
            f"| {_escape_md_cell(row['category'])} | {row['status']} | {timing} "
            f"| {_escape_md_cell(row['description'])} |"
        )
    lines.append("")

    with open(os.path.join(ASSETS_DIR, "report.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main() -> None:
    os.makedirs(ASSETS_DIR, exist_ok=True)

    raw = metrics.load_change_log(os.path.join(DATA_DIR, "change_log.csv"))
    changes = metrics.add_cycle_and_aging(raw, STATUS_DATE)
    cum = metrics.cumulative_impact(changes)
    stats = metrics.summary_stats(changes)

    print_report(changes, stats)

    chart_cumulative(cum, "cum_cost", "Cumulative approved cost impact ($)",
                      "Budget Creep: Cumulative Approved Cost Impact", "cumulative_cost.png")
    chart_cumulative(cum, "cum_schedule_days", "Cumulative approved schedule impact (days)",
                      "Schedule Creep: Cumulative Approved Schedule Impact", "cumulative_schedule.png")
    chart_cycle_time(changes)
    write_report_markdown(changes, stats)

    print()
    print("-" * 64)
    print(f"Charts and report.md saved to {ASSETS_DIR}")


if __name__ == "__main__":
    main()

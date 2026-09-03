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

from src import metrics

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")

STATUS_DATE = "2026-08-01"

# Standardized chart color system (chart chrome, status scale, categorical series, baseline)
CHART_BG = "#fcfcfb"
INK = "#10182b"
GRID = "#e1e0d9"
BASELINE = "#3a4d7a"
SERIES_1 = "#2a78d6"
STATUS_GOOD = "#0ca30c"
STATUS_WARNING = "#fab219"
STATUS_CRITICAL = "#d03b3b"


def _apply_chrome(fig, axes) -> None:
    """Apply the standardized chart chrome (background, ink, gridlines) to a figure."""
    fig.patch.set_facecolor(CHART_BG)
    if hasattr(axes, "flatten"):
        axes = axes.flatten().tolist()
    elif not isinstance(axes, (list, tuple)):
        axes = [axes]
    for ax in axes:
        ax.set_facecolor(CHART_BG)
        ax.title.set_color(INK)
        ax.xaxis.label.set_color(INK)
        ax.yaxis.label.set_color(INK)
        ax.tick_params(colors=INK)
        for spine in ax.spines.values():
            spine.set_color(INK)


def money(x: float) -> str:
    return f"${x:,.0f}"


def print_report(changes, cum, stats: dict) -> None:
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
        if row["status"] == "Pending":
            timing = f"open {int(row['days_open'])}d" + (" [STALE]" if row["is_stale"] else "")
        else:
            timing = f"decided in {int(row['cycle_days'])}d"
        print(f"  {row['change_id']:<5} {money(row['cost_impact']):>10}  "
              f"{row['schedule_impact_days']:+3d}d  ({row['category']}, {row['status']})  "
              f"{timing}  {row['description']}")


def chart_cumulative(cum, value_col: str, ylabel: str, title: str, filename: str) -> None:
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.step(cum["date_decided"].to_numpy(), cum[value_col].to_numpy(), where="post",
            color=SERIES_1, linewidth=2)
    ax.scatter(cum["date_decided"].to_numpy(), cum[value_col].to_numpy(), color=SERIES_1, s=20, zorder=3)
    ax.axhline(0, color=INK, linewidth=0.8, alpha=0.6)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.grid(color=GRID, linewidth=0.6)
    _apply_chrome(fig, ax)
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(os.path.join(ASSETS_DIR, filename), dpi=140, facecolor=CHART_BG)
    plt.close(fig)


def chart_cycle_time(changes) -> None:
    fig, ax = plt.subplots(figsize=(9, 6))
    labels, values, colors = [], [], []
    for _, row in changes.sort_values("date_raised").iterrows():
        labels.append(f"{row['change_id']} ({row['status']})")
        if row["status"] == "Pending":
            values.append(row["days_open"])
            colors.append(STATUS_CRITICAL if row["is_stale"] else STATUS_WARNING)
        else:
            values.append(row["cycle_days"])
            colors.append(STATUS_GOOD)
    ax.barh(labels, values, color=colors)
    ax.axvline(metrics.STALE_PENDING_DAYS, color=BASELINE, linestyle="--", linewidth=1,
               label=f"Stale threshold ({metrics.STALE_PENDING_DAYS}d)")
    ax.set_xlabel("Days")
    ax.set_title("Decision Cycle Time (green = decided) / Days Open (amber/red = pending)")
    ax.legend(fontsize=8)
    ax.grid(color=GRID, linewidth=0.6, axis="x")
    _apply_chrome(fig, ax)
    fig.tight_layout()
    fig.savefig(os.path.join(ASSETS_DIR, "cycle_time.png"), dpi=140, facecolor=CHART_BG)
    plt.close(fig)


def write_report_markdown(changes, cum, stats: dict) -> None:
    lines = [
        "# Change Control Report",
        "",
        f"**Total changes logged:** {stats['total_changes']} "
        f"(Approved {stats['approved_count']}, Rejected {stats['rejected_count']}, "
        f"Pending {stats['pending_count']})  ",
        f"**Approval rate:** {stats['approval_rate_pct']}%  ",
        f"**Average decision cycle time:** {stats['avg_cycle_days']} days  ",
        f"**Stale pending changes (open > {metrics.STALE_PENDING_DAYS}d):** {stats['stale_pending_count']}",
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
        if row["status"] == "Pending":
            timing = f"open {int(row['days_open'])}d" + (" **STALE**" if row["is_stale"] else "")
        else:
            timing = f"decided in {int(row['cycle_days'])}d"
        lines.append(
            f"| {row['change_id']} | {money(row['cost_impact'])} | {row['schedule_impact_days']:+d}d "
            f"| {row['category']} | {row['status']} | {timing} | {row['description']} |"
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

    print_report(changes, cum, stats)

    chart_cumulative(cum, "cum_cost", "Cumulative approved cost impact ($)",
                      "Budget Creep: Cumulative Approved Cost Impact", "cumulative_cost.png")
    chart_cumulative(cum, "cum_schedule_days", "Cumulative approved schedule impact (days)",
                      "Schedule Creep: Cumulative Approved Schedule Impact", "cumulative_schedule.png")
    chart_cycle_time(changes)
    write_report_markdown(changes, cum, stats)

    print()
    print("-" * 64)
    print(f"Charts and report.md saved to {ASSETS_DIR}")


if __name__ == "__main__":
    main()

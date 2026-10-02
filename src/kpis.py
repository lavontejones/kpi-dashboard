"""Pure KPI computations for the Executive KPI Dashboard.

``compute_kpis`` takes filtered dataframes plus a scenario multiplier and
returns the six headline metrics, each with its prior-period value so the
app can render deltas. No Streamlit imports here — this module is meant to
be unit-testable and reusable.
"""

from __future__ import annotations

import pandas as pd

# Scenario math: revenue scales fully, COGS scales at 80% of the revenue
# change (the variable portion). Fixed costs stay fixed. This gives the
# downside/upside scenarios realistic operating leverage instead of just
# rescaling every number identically.
COGS_VARIABLE_SHARE = 0.80


def _period_mask(df: pd.DataFrame, col: str, start: pd.Timestamp, end: pd.Timestamp) -> pd.Series:
    return (df[col] >= start) & (df[col] <= end)


def _summarize(
    jobs: pd.DataFrame,
    expenses: pd.DataFrame,
    cash: pd.DataFrame,
    start: pd.Timestamp,
    end: pd.Timestamp,
    scenario_mult: float,
) -> dict:
    jf = jobs[_period_mask(jobs, "date", start, end)]
    ef = expenses[_period_mask(expenses, "date", start, end)]

    revenue = float(jf["revenue"].sum()) * scenario_mult
    cogs = float(jf["cogs"].sum()) * (1 + (scenario_mult - 1) * COGS_VARIABLE_SHARE)
    gross_margin_pct = (revenue - cogs) / revenue if revenue else 0.0
    opex = float(ef["amount"].sum())
    net_cash_flow = (revenue - cogs) - opex

    cash_f = cash[cash["week_start"] <= end]
    cash_balance = float(cash_f.sort_values("week_start")["balance"].iloc[-1]) if len(cash_f) else 0.0

    days = max((end - start).days + 1, 1)
    avg_weekly_outflow = (cogs + opex) / (days / 7)
    runway_weeks = cash_balance / avg_weekly_outflow if avg_weekly_outflow > 0 else 0.0

    return {
        "revenue": revenue,
        "gross_margin_pct": gross_margin_pct,
        "net_cash_flow": net_cash_flow,
        "cash_runway_weeks": runway_weeks,
        "cash_balance": cash_balance,
    }


def compute_kpis(
    jobs: pd.DataFrame,
    expenses: pd.DataFrame,
    cash: pd.DataFrame,
    pipeline: pd.DataFrame,
    start: pd.Timestamp,
    end: pd.Timestamp,
    scenario_mult: float = 1.0,
) -> dict:
    """Compute headline KPIs for [start, end], with prior-period values.

    The prior period is the equal-length window immediately before ``start``.
    Pipeline metrics are a point-in-time snapshot, so they carry no prior.
    """
    if end < start:
        raise ValueError("end must be on or after start")
    if scenario_mult <= 0:
        raise ValueError("scenario multiplier must be positive")
    current = _summarize(jobs, expenses, cash, start, end, scenario_mult)

    period_len = end - start
    p_end = start - pd.Timedelta(days=1)
    p_start = p_end - period_len
    prior = _summarize(jobs, expenses, cash, p_start, p_end, scenario_mult)
    has_prior = bool(
        _period_mask(jobs, "date", p_start, p_end).any()
        or _period_mask(expenses, "date", p_start, p_end).any()
    )

    active = pipeline[pipeline["stage"].isin(["Lead", "Qualified", "Proposal"])]
    won = pipeline[pipeline["stage"] == "Won"]
    lost = pipeline[pipeline["stage"] == "Lost"]
    decided = len(won) + len(lost)

    def with_prior(key: str) -> dict:
        return {
            "value": current[key],
            "prior": prior[key] if has_prior else None,
        }

    return {
        "revenue": with_prior("revenue"),
        "gross_margin_pct": with_prior("gross_margin_pct"),
        "net_cash_flow": with_prior("net_cash_flow"),
        "cash_runway_weeks": with_prior("cash_runway_weeks"),
        "cash_balance": with_prior("cash_balance"),
        "active_pipeline_value": {"value": float(active["value"].sum()), "prior": None},
        "avg_close_days": {
            "value": float(won["age_days"].mean()) if len(won) else 0.0,
            "prior": None,
        },
        "win_rate": {
            "value": (len(won) / decided) if decided else 0.0,
            "prior": None,
        },
    }


"""Executive KPI Dashboard — sample-data Streamlit app.

A management-reporting demo for a fictional home-services SMB
("Cedarline Home Services"). All figures are synthetic; see README.md.
"""

from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.kpis import compute_kpis

DATA_DIR = Path(__file__).resolve().parent / "data"
REGIONS = ["North", "South", "East", "West"]
SCENARIOS = {
    "Base": 1.00,
    "Downside (−15% revenue)": 0.85,
    "Upside (+15% revenue)": 1.15,
}
CASH_MIN_THRESHOLD = 50_000.0
FUNNEL_ORDER = ["Lead", "Qualified", "Proposal", "Won"]

st.set_page_config(page_title="Executive KPI Dashboard", layout="wide")


# ---------------------------------------------------------------- data loading
@st.cache_data
def load_data():
    jobs = pd.read_csv(DATA_DIR / "jobs.csv", parse_dates=["date"])
    expenses = pd.read_csv(DATA_DIR / "expenses.csv", parse_dates=["date"])
    cash = pd.read_csv(DATA_DIR / "cash.csv", parse_dates=["week_start"])
    pipeline = pd.read_csv(DATA_DIR / "pipeline.csv", parse_dates=["created_date"])
    return jobs, expenses, cash, pipeline


# ------------------------------------------------------------------ formatting
def fmt_money(x: float) -> str:
    if abs(x) >= 1_000_000:
        return f"${x / 1_000_000:.2f}M"
    return f"${x / 1_000:.0f}k"


def fmt_delta_money(current: float, prior: float | None) -> str | None:
    if prior is None:
        return None
    return f"{fmt_money(current - prior)} vs prior"


# --------------------------------------------------------------------- sidebar
def sidebar_filters(jobs: pd.DataFrame):
    st.sidebar.header("Filters")
    min_date, max_date = jobs["date"].min().date(), jobs["date"].max().date()
    default_start = max_date - pd.DateOffset(months=12) + pd.DateOffset(days=1)
    start, end = st.sidebar.date_input(
        "Date range",
        value=(default_start.date(), max_date),
        min_value=min_date,
        max_value=max_date,
    )
    regions = st.sidebar.multiselect("Region", REGIONS, default=REGIONS)
    scenario_name = st.sidebar.selectbox("Scenario", list(SCENARIOS.keys()))
    return pd.Timestamp(start), pd.Timestamp(end), regions, SCENARIOS[scenario_name], scenario_name


# ------------------------------------------------------------------- KPI row
def kpi_row(kpis: dict) -> None:
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    r = kpis["revenue"]
    c1.metric("Revenue", fmt_money(r["value"]), fmt_delta_money(r["value"], r["prior"]))
    m = kpis["gross_margin_pct"]
    c2.metric(
        "Gross Margin %",
        f"{m['value']:.1%}",
        f"{(m['value'] - m['prior']):.1%} pts vs prior" if m["prior"] is not None else None,
    )
    n = kpis["net_cash_flow"]
    c3.metric("Net Cash Flow", fmt_money(n["value"]), fmt_delta_money(n["value"], n["prior"]))
    w = kpis["cash_runway_weeks"]
    c4.metric(
        "Cash Runway",
        f"{w['value']:.1f} wks",
        f"{w['value'] - w['prior']:.1f} wks vs prior" if w["prior"] is not None else None,
    )
    p = kpis["active_pipeline_value"]
    c5.metric("Active Pipeline", fmt_money(p["value"]))
    d = kpis["avg_close_days"]
    c6.metric("Avg Close Time", f"{d['value']:.0f} days")


# ------------------------------------------------------------------ tab: revenue
def tab_revenue(jobs: pd.DataFrame, start, end) -> None:
    monthly = (
        jobs.assign(month=jobs["date"].dt.to_period("M").astype(str))
        .groupby("month", as_index=False)["revenue"]
        .sum()
    )
    monthly["month_dt"] = pd.to_datetime(monthly["month"])
    prior = monthly.copy()
    prior["month_dt"] = prior["month_dt"] + pd.DateOffset(years=1)
    prior = prior.rename(columns={"revenue": "revenue_prior_year"})

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=monthly["month_dt"], y=monthly["revenue"],
                             mode="lines+markers", name="Revenue"))
    fig.add_trace(go.Scatter(x=prior["month_dt"], y=prior["revenue_prior_year"],
                             mode="lines", name="Prior year", line=dict(dash="dash")))
    fig.update_layout(title="Monthly revenue vs prior year",
                      xaxis_title="", yaxis_title="Revenue ($)",
                      yaxis_tickprefix="$", hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)

    by_region = jobs.groupby("region", as_index=False)["revenue"].sum()
    fig2 = px.bar(by_region, x="region", y="revenue", title="Revenue by region",
                  labels={"region": "", "revenue": "Revenue ($)"}, text_auto=".2s")
    fig2.update_traces(texttemplate="$%{y:.2s}")
    st.plotly_chart(fig2, use_container_width=True)


# --------------------------------------------------------------------- tab: cash
def tab_cash(cash: pd.DataFrame, kpis: dict, end) -> None:
    cf = cash[cash["week_start"] <= end]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=cf["week_start"], y=cf["balance"],
                             fill="tozeroy", mode="lines", name="Cash balance"))
    fig.add_hline(y=CASH_MIN_THRESHOLD, line_dash="dash", line_color="red",
                  annotation_text=f"Minimum threshold (${CASH_MIN_THRESHOLD:,.0f})")
    fig.update_layout(title="Cash balance with minimum-threshold line",
                      xaxis_title="", yaxis_title="Balance ($)", yaxis_tickprefix="$")
    st.plotly_chart(fig, use_container_width=True)

    runway = kpis["cash_runway_weeks"]["value"]
    color = "green" if runway >= 8 else "orange" if runway >= 4 else "red"
    gauge = go.Figure(go.Indicator(
        mode="gauge+number", value=round(runway, 1),
        title={"text": "Cash runway (weeks)"},
        gauge={"axis": {"range": [0, max(16, runway * 1.3)]},
               "bar": {"color": color},
               "steps": [{"range": [0, 4], "color": "#f8d7da"},
                         {"range": [4, 8], "color": "#fff3cd"},
                         {"range": [8, 32], "color": "#d4edda"}]},
    ))
    st.plotly_chart(gauge, use_container_width=True)
    st.caption(
        f"Runway = current balance ({fmt_money(kpis['cash_balance']['value'])}) ÷ "
        "average weekly outflow (COGS + overhead) in the selected period. "
        "Bands reflect total-spend coverage: under 4 weeks is tight, 8+ is comfortable."
    )


# ----------------------------------------------------------------- tab: pipeline
def tab_pipeline(pipeline: pd.DataFrame, kpis: dict) -> None:
    funnel = (
        pipeline[pipeline["stage"].isin(FUNNEL_ORDER)]
        .groupby("stage", as_index=False)
        .agg(deals=("deal_id", "count"), value=("value", "sum"))
    )
    funnel["stage"] = pd.Categorical(funnel["stage"], categories=FUNNEL_ORDER, ordered=True)
    funnel = funnel.sort_values("stage")
    fig = px.bar(funnel, x="stage", y="deals", title="Pipeline funnel",
                 labels={"stage": "", "deals": "Deals"},
                 hover_data={"value": ":$,.0f"})
    st.plotly_chart(fig, use_container_width=True)

    c1, c2 = st.columns(2)
    c1.metric("Win rate", f"{kpis['win_rate']['value']:.0%}")
    c2.metric("Active pipeline value", fmt_money(kpis["active_pipeline_value"]["value"]))

    st.subheader("Deals by stage")
    st.dataframe(
        funnel.rename(columns={"stage": "Stage", "deals": "Deals", "value": "Value ($)"}),
        use_container_width=True, hide_index=True,
    )


# ---------------------------------------------------------------- tab: operations
def tab_operations(jobs: pd.DataFrame) -> None:
    monthly_jobs = (
        jobs.assign(month=jobs["date"].dt.to_period("M").astype(str))
        .groupby("month", as_index=False)
        .agg(jobs_completed=("job_id", "count"), revenue=("revenue", "sum"))
    )
    fig = px.bar(monthly_jobs, x="month", y="jobs_completed",
                 title="Jobs completed per month",
                 labels={"month": "", "jobs_completed": "Jobs"})
    st.plotly_chart(fig, use_container_width=True)

    tech = (
        jobs.groupby("technician", as_index=False)
        .agg(jobs=("job_id", "count"),
             revenue=("revenue", "sum"),
             avg_ticket=("revenue", "mean"))
        .sort_values("jobs", ascending=False)
    )
    months_in_period = max(jobs["date"].dt.to_period("M").nunique(), 1)
    capacity_per_tech = 22 * months_in_period  # ~22 jobs/month sustainable capacity
    tech["utilization"] = (tech["jobs"] / capacity_per_tech).clip(upper=1.2)

    fig2 = px.bar(tech, x="technician", y="utilization",
                  title="Technician utilization (vs ~22 jobs/month capacity)",
                  labels={"technician": "", "utilization": "Utilization"})
    fig2.update_yaxes(tickformat=".0%")
    fig2.add_hline(y=1.0, line_dash="dash", line_color="red",
                   annotation_text="Capacity")
    st.plotly_chart(fig2, use_container_width=True)

    st.subheader("Technician leaderboard")
    show = tech.copy()
    show["utilization"] = show["utilization"].map("{:.0%}".format)
    show["avg_ticket"] = show["avg_ticket"].map("${:,.0f}".format)
    show["revenue"] = show["revenue"].map("${:,.0f}".format)
    st.dataframe(
        show.rename(columns={"technician": "Tech", "jobs": "Jobs",
                             "revenue": "Revenue", "avg_ticket": "Avg ticket",
                             "utilization": "Utilization"}),
        use_container_width=True, hide_index=True,
    )


# ------------------------------------------------------------------------ main
def main() -> None:
    st.title("Executive KPI Dashboard")
    st.warning(
        "⚠️ **SAMPLE DATA** — fictional company **“Cedarline Home Services.”** "
        "All figures are synthetically generated for demonstration purposes and "
        "do not represent any real business."
    )

    jobs, expenses, cash, pipeline = load_data()
    start, end, regions, scenario_mult, scenario_name = sidebar_filters(jobs)

    jobs_f = jobs[jobs["region"].isin(regions)]
    if jobs_f.empty:
        st.error("No data for the selected filters.")
        return

    kpis = compute_kpis(jobs_f, expenses, cash, pipeline, start, end, scenario_mult)
    st.caption(f"Scenario: **{scenario_name}** · {start.date()} → {end.date()} · "
               f"{len(regions)} region(s)")
    kpi_row(kpis)

    t1, t2, t3, t4 = st.tabs(["Revenue", "Cash", "Pipeline", "Operations"])
    with t1:
        tab_revenue(jobs_f[(jobs_f["date"] >= start) & (jobs_f["date"] <= end)], start, end)
    with t2:
        tab_cash(cash, kpis, end)
    with t3:
        tab_pipeline(pipeline, kpis)
    with t4:
        tab_operations(jobs_f[(jobs_f["date"] >= start) & (jobs_f["date"] <= end)])


if __name__ == "__main__":
    main()

# Executive KPI Dashboard

A Streamlit management-reporting dashboard for a fictional home-services SMB
("Cedarline Home Services"). It answers the four questions an owner actually
asks every Monday morning: **how's revenue trending, how's cash, how's the
pipeline, how's the crew doing?**

> ⚠️ **Sample data.** Every figure in this app is synthetically generated for
> demonstration purposes. It does not represent any real business.

## What this demonstrates

This project maps directly to consulting deliverables:

- **KPI design** — choosing the six metrics that matter (revenue, gross margin,
  net cash flow, cash runway, pipeline value, close time) instead of drowning
  an owner in forty charts.
- **Management reporting** — a repeatable weekly/monthly pack: filters,
  prior-period deltas, and thresholds, not one-off analysis.
- **Scenario modeling** — Base / Downside (−15%) / Upside (+15%) revenue
  scenarios with realistic operating leverage (variable costs scale at 80% of
  the revenue change; fixed costs don't move).
- **Clean, testable code** — KPI logic lives in pure functions in
  `src/kpis.py`, separate from the Streamlit presentation layer.

## Quick start

```bash
pip install -r requirements.txt
python src/data_gen.py      # generate the sample dataset (seeded, reproducible)
streamlit run app.py
```

## Project structure

```
kpi-dashboard/
├── app.py              # Streamlit app (filters, KPI cards, 4 tabs)
├── src/
│   ├── data_gen.py     # deterministic synthetic data generator (seed=42)
│   └── kpis.py         # pure KPI computations + prior-period deltas
├── data/               # generated CSVs (jobs, expenses, cash, pipeline)
├── requirements.txt
└── README.md
```

The dataset covers 24 months of daily-granularity data: ~11k completed jobs
across 4 regions and 12 technicians, monthly overhead by category, weekly cash
balances derived from operating flows, and a 140-deal pipeline snapshot.
Revenue grows ~45% over the period with a summer seasonal peak; gross margin
runs ~35%.

## Screenshots

_Screenshots of the Revenue and Cash tabs will be added here after the first run._

## Ideas for extending

- Swap the CSV layer for real data: QuickBooks (P&L/cash) + Stripe/job-scheduling
  exports (jobs) + HubSpot (pipeline) — the KPI functions don't care where the
  dataframes come from.
- Add a weekly email/PDF export of the KPI card row for owners who don't open
  dashboards.
- Add budget-vs-actual: a `budget.csv` with monthly targets and variance columns.
- Add cohort/retention views for recurring-service businesses.

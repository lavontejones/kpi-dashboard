"""Deterministic synthetic data generator for the kpi-dashboard sample dataset.

Generates 24 months of daily-granularity operating data for a fictional
home-services SMB ("Cedarline Home Services") and writes four CSVs into
``data/``. Everything is seeded (SEED=42), so the output is reproducible.

The data is designed to look like a real small business:
- revenue grows ~45% over the period with a summer seasonal peak
- gross margin hovers around 35%
- cash dips in the slow winter months and rebuilds in summer
"""

from pathlib import Path

import numpy as np
import pandas as pd

SEED = 42
START = pd.Timestamp("2024-10-01")
END = pd.Timestamp("2026-09-30")
REGIONS = ["North", "South", "East", "West"]
REGION_WEIGHTS = [0.30, 0.25, 0.25, 0.20]
TECHNICIANS = [f"T-{i:02d}" for i in range(1, 13)]
OPENING_CASH = 200_000.0
CASH_FLOOR = 0.0  # generator keeps the business solvent; the app shows the dip

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _seasonal_multiplier(month: pd.Series) -> pd.Series:
    """Summer peak (July), winter trough (January)."""
    return 1.0 + 0.22 * np.sin(2 * np.pi * (month - 4) / 12)


def _weekday_factor(dow: pd.Series) -> pd.Series:
    return dow.map({0: 1.0, 1: 1.0, 2: 1.0, 3: 1.0, 4: 1.0, 5: 0.45, 6: 0.25})


def generate_jobs(rng: np.random.Generator) -> pd.DataFrame:
    """One row per completed job: date, region, revenue, cogs, technician."""
    days = pd.date_range(START, END, freq="D")
    elapsed = (days - START).days / 730.0  # 0 -> 1 over the dataset
    growth = 1.0 + 0.45 * elapsed
    lam = (
        20.0
        * growth
        * _seasonal_multiplier(days.month).to_numpy()
        * _weekday_factor(days.dayofweek).to_numpy()
    )
    counts = rng.poisson(lam)

    rows = []
    job_id = 0
    for day, n in zip(days, counts):
        for _ in range(int(n)):
            job_id += 1
            revenue = float(rng.lognormal(mean=np.log(680), sigma=0.50))
            cogs_ratio = float(np.clip(rng.normal(0.64, 0.06), 0.45, 0.85))
            rows.append(
                {
                    "job_id": f"J-{job_id:06d}",
                    "date": day.date().isoformat(),
                    "region": rng.choice(REGIONS, p=REGION_WEIGHTS),
                    "technician": rng.choice(TECHNICIANS),
                    "revenue": round(revenue, 2),
                    "cogs": round(revenue * cogs_ratio, 2),
                }
            )
    jobs = pd.DataFrame(rows)
    jobs["date"] = pd.to_datetime(jobs["date"])
    return jobs


def generate_expenses(rng: np.random.Generator) -> pd.DataFrame:
    """Monthly overhead by category, posted on the 1st of each month."""
    months = pd.date_range(START, END, freq="MS")
    n = len(months)
    elapsed = (months - START).days / 730.0
    seasonal = 1 + 0.30 * np.sin(2 * np.pi * (months.month - 4) / 12)
    categories = {
        "Payroll": 72_000 * (1 + 0.30 * elapsed),
        "Rent & facilities": np.full(n, 12_000.0),
        "Marketing": 12_000 * seasonal,
        "Vehicles & fuel": np.full(n, 11_000.0),
        "Insurance": np.full(n, 9_000.0),
        "Software & tools": np.full(n, 4_500.0),
        "Other": np.full(n, 5_000.0),
    }
    rows = []
    for i, month in enumerate(months):
        for category, base in categories.items():
            amount = float(np.asarray(base, dtype=float)[i] * rng.normal(1.0, 0.08))
            rows.append(
                {
                    "date": month.date().isoformat(),
                    "category": category,
                    "amount": round(max(amount, 0.0), 2),
                }
            )
    expenses = pd.DataFrame(rows)
    expenses["date"] = pd.to_datetime(expenses["date"])
    return expenses


def generate_cash(
    rng: np.random.Generator, jobs: pd.DataFrame, expenses: pd.DataFrame
) -> pd.DataFrame:
    """Weekly cash balances derived from operating flows.

    Inflows: ~96% of the week's job revenue collected that week.
    Outflows: week's COGS + the week's share of that month's overhead.
    """
    week_starts = pd.date_range("2024-09-30", "2026-09-28", freq="W-MON")

    jobs = jobs.copy()
    jobs["week"] = jobs["date"].dt.to_period("W").dt.start_time
    weekly_rev = jobs.groupby("week")["revenue"].sum()
    weekly_cogs = jobs.groupby("week")["cogs"].sum()

    expenses = expenses.copy()
    expenses["month"] = expenses["date"].dt.to_period("M")
    monthly_exp = expenses.groupby("month")["amount"].sum()

    balances, inflows, outflows = [], [], []
    balance = OPENING_CASH
    for ws in week_starts:
        rev = float(weekly_rev.get(ws, 0.0))
        cogs = float(weekly_cogs.get(ws, 0.0))
        month_key = pd.Period(ws, freq="M")
        month_exp = float(monthly_exp.get(month_key, 0.0))
        weeks_in_month = len(pd.date_range(month_key.start_time, month_key.end_time, freq="W-MON")) or 4
        inflow = rev * float(rng.normal(0.96, 0.02))
        outflow = cogs + month_exp / weeks_in_month
        balance = max(balance + inflow - outflow, CASH_FLOOR)
        balances.append(round(balance, 2))
        inflows.append(round(inflow, 2))
        outflows.append(round(outflow, 2))

    return pd.DataFrame(
        {
            "week_start": week_starts.date.astype(str),
            "cash_inflow": inflows,
            "cash_outflow": outflows,
            "balance": balances,
        }
    )


def generate_pipeline(rng: np.random.Generator) -> pd.DataFrame:
    """Point-in-time snapshot of the sales pipeline as of the dataset end."""
    n = 140
    stages = rng.choice(
        ["Lead", "Qualified", "Proposal", "Won", "Lost"],
        size=n,
        p=[0.34, 0.25, 0.18, 0.15, 0.08],
    )
    mean_age = {"Lead": 12, "Qualified": 22, "Proposal": 34, "Won": 46, "Lost": 40}
    rows = []
    for i, stage in enumerate(stages):
        value = float(rng.lognormal(mean=np.log(4200), sigma=0.70))
        age = int(max(1, rng.exponential(mean_age[stage])))
        created = END - pd.Timedelta(days=int(rng.integers(1, 180)))
        rows.append(
            {
                "deal_id": f"D-{i + 1:04d}",
                "stage": stage,
                "value": round(value, 2),
                "age_days": age,
                "region": rng.choice(REGIONS, p=REGION_WEIGHTS),
                "created_date": created.date().isoformat(),
            }
        )
    pipeline = pd.DataFrame(rows)
    pipeline["created_date"] = pd.to_datetime(pipeline["created_date"])
    return pipeline


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(SEED)

    jobs = generate_jobs(rng)
    expenses = generate_expenses(rng)
    cash = generate_cash(rng, jobs, expenses)
    pipeline = generate_pipeline(rng)

    jobs.to_csv(DATA_DIR / "jobs.csv", index=False)
    expenses.to_csv(DATA_DIR / "expenses.csv", index=False)
    cash.to_csv(DATA_DIR / "cash.csv", index=False)
    pipeline.to_csv(DATA_DIR / "pipeline.csv", index=False)

    months = jobs["date"].dt.to_period("M").nunique()
    margin = (jobs["revenue"].sum() - jobs["cogs"].sum()) / jobs["revenue"].sum()
    print(f"jobs.csv      {len(jobs):>7,} rows   ({months} months)")
    print(f"expenses.csv  {len(expenses):>7,} rows")
    print(f"cash.csv      {len(cash):>7,} rows   (weekly)")
    print(f"pipeline.csv  {len(pipeline):>7,} rows   (snapshot)")
    print(f"total revenue ${jobs['revenue'].sum():,.0f}   gross margin {margin:.1%}")


if __name__ == "__main__":
    main()

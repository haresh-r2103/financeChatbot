"""
Sample data generator for FinanceBot.

Generates three CSV files:
  1. sample_data.csv          — 1 year, monthly, with an expense anomaly in July
  2. sample_data_2yr.csv      — 2 years, monthly, gradual margin improvement
  3. sample_data_quarterly.csv — quarterly P&L with department breakdown

Run:  python generate_data.py
"""
import pandas as pd
import numpy as np

np.random.seed(42)

MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]
QUARTER_MAP = {m: f"Q{(i // 3) + 1}" for i, m in enumerate(MONTHS)}


def _round(x, nearest=100):
    return int(round(x / nearest) * nearest)


# ─────────────────────────────────────────────────────────────────
# 1.  Single-year monthly data (12 rows)
# ─────────────────────────────────────────────────────────────────
def make_annual():
    rows = []
    base = 50_000
    for i, month in enumerate(MONTHS):
        seasonal = 1 + 0.15 * np.sin((i - 2) * np.pi / 6)
        growth   = 1 + 0.04 * i
        revenue  = _round(base * seasonal * growth * np.random.normal(1, 0.04))

        exp_ratio = 0.62 - 0.005 * i + np.random.normal(0, 0.015)
        expenses  = _round(revenue * max(exp_ratio, 0.45))

        # July anomaly: one-off equipment purchase inflates expenses
        if month == "July":
            expenses = _round(expenses * 1.45)

        profit = revenue - expenses
        rows.append({
            "month":             month,
            "quarter":           QUARTER_MAP[month],
            "revenue":           revenue,
            "expenses":          expenses,
            "profit":            profit,
            "profit_margin_pct": round(profit / revenue * 100, 2),
            "marketing_spend":   _round(expenses * 0.20),
            "operations_cost":   _round(expenses * 0.50),
            "salaries":          _round(expenses * 0.30),
            "units_sold":        max(1, int(revenue / 45 + np.random.normal(0, 30))),
            "new_customers":     max(0, int(80 + i * 8 + np.random.normal(0, 10))),
            "customer_churn":    max(0, int(12 + np.random.normal(0, 3))),
        })
    return pd.DataFrame(rows)


# ─────────────────────────────────────────────────────────────────
# 2.  Two-year monthly data (24 rows) — profit dip mid-year 2
# ─────────────────────────────────────────────────────────────────
def make_two_year():
    rows = []
    base = 45_000
    for year in [2023, 2024]:
        for i, month in enumerate(MONTHS):
            t = (year - 2023) * 12 + i
            seasonal = 1 + 0.18 * np.sin((i - 2) * np.pi / 6)
            growth   = 1 + 0.025 * t
            revenue  = _round(base * seasonal * growth * np.random.normal(1, 0.035))

            # Year 2: rising cost pressure in Q2-Q3 (supply chain crunch)
            if year == 2024 and 3 <= i <= 8:
                exp_ratio = 0.68 + np.random.normal(0, 0.02)
            else:
                exp_ratio = 0.60 - 0.003 * t + np.random.normal(0, 0.015)

            expenses = _round(revenue * max(exp_ratio, 0.44))
            profit   = revenue - expenses
            rows.append({
                "year":              year,
                "month":             month,
                "period":            f"{month[:3]} {year}",
                "quarter":           QUARTER_MAP[month],
                "revenue":           revenue,
                "expenses":          expenses,
                "profit":            profit,
                "profit_margin_pct": round(profit / revenue * 100, 2),
                "cogs":              _round(expenses * 0.40),
                "marketing_spend":   _round(expenses * 0.18),
                "operations_cost":   _round(expenses * 0.27),
                "salaries":          _round(expenses * 0.15),
                "units_sold":        max(1, int(revenue / 42 + np.random.normal(0, 25))),
                "new_customers":     max(0, int(70 + t * 6 + np.random.normal(0, 12))),
            })
    return pd.DataFrame(rows)


# ─────────────────────────────────────────────────────────────────
# 3.  Quarterly data with department revenue split (8 rows)
# ─────────────────────────────────────────────────────────────────
def make_quarterly():
    rows = []
    quarters = ["Q1 2024", "Q2 2024", "Q3 2024", "Q4 2024",
                "Q1 2025", "Q2 2025", "Q3 2025", "Q4 2025"]
    base = 160_000
    for i, q in enumerate(quarters):
        revenue_product  = _round(base * (1 + 0.05 * i) * np.random.normal(1, 0.04), 1000)
        revenue_services = _round(base * 0.45 * (1 + 0.07 * i) * np.random.normal(1, 0.05), 1000)
        revenue_subscr   = _round(base * 0.20 * (1 + 0.10 * i) * np.random.normal(1, 0.03), 1000)
        revenue = revenue_product + revenue_services + revenue_subscr

        expenses = _round(revenue * (0.60 - 0.01 * i + np.random.normal(0, 0.02)), 1000)
        profit   = revenue - expenses
        rows.append({
            "quarter":              q,
            "revenue":              revenue,
            "revenue_product":      revenue_product,
            "revenue_services":     revenue_services,
            "revenue_subscriptions":revenue_subscr,
            "expenses":             expenses,
            "profit":               profit,
            "profit_margin_pct":    round(profit / revenue * 100, 2),
            "ebitda":               _round(profit * 1.12, 1000),
            "headcount":            int(42 + i * 3),
            "revenue_per_employee": _round(revenue / (42 + i * 3), 100),
        })
    return pd.DataFrame(rows)


# ─────────────────────────────────────────────────────────────────
# Write files
# ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    files = {
        "sample_data.csv":             make_annual(),
        "sample_data_2yr.csv":         make_two_year(),
        "sample_data_quarterly.csv":   make_quarterly(),
    }

    for fname, df in files.items():
        df.to_csv(fname, index=False)
        rev_col = "revenue"
        exp_col = "expenses"
        total_r = df[rev_col].sum()
        total_e = df[exp_col].sum()
        total_p = total_r - total_e
        print(f"[{fname}]")
        print(f"  Rows    : {len(df)}")
        print(f"  Columns : {list(df.columns)}")
        print(f"  Revenue : ${total_r:,.0f}")
        print(f"  Expenses: ${total_e:,.0f}")
        print(f"  Profit  : ${total_p:,.0f}  ({total_p/total_r*100:.1f}% margin)")
        print()

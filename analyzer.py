"""
Finance analyzer: totals, monthly trends, and anomaly detection.
Anomalies are flagged using the IQR (interquartile range) method — robust
against outliers and requires no external ML library.
"""
import pandas as pd


MONTH_ORDER = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def analyze(
    df: pd.DataFrame,
    revenue_col: str,
    expense_col: str,
    month_col: str | None = None,
) -> dict:
    df = df.copy()
    df["_profit"] = df[revenue_col] - df[expense_col]

    return {
        "totals": _totals(df, revenue_col, expense_col),
        "monthly_trends": _monthly_trends(df, revenue_col, expense_col, month_col),
        "anomalies": _detect_anomalies(df, revenue_col, expense_col, month_col),
    }


# ---------------------------------------------------------------------------
# Section helpers
# ---------------------------------------------------------------------------

def _totals(df: pd.DataFrame, rev: str, exp: str) -> dict:
    revenue = df[rev]
    expenses = df[exp]
    profit = df["_profit"]

    total_rev = revenue.sum()
    total_exp = expenses.sum()
    total_profit = profit.sum()

    return {
        "revenue": {
            "total": _r(total_rev),
            "mean": _r(revenue.mean()),
            "median": _r(revenue.median()),
            "std_dev": _r(revenue.std()),
        },
        "expenses": {
            "total": _r(total_exp),
            "mean": _r(expenses.mean()),
            "median": _r(expenses.median()),
            "std_dev": _r(expenses.std()),
        },
        "profit": {
            "total": _r(total_profit),
            "mean": _r(profit.mean()),
            "median": _r(profit.median()),
            "std_dev": _r(profit.std()),
        },
        "profit_margin_pct": _r((total_profit / total_rev) * 100) if total_rev else 0.0,
        "expense_ratio_pct": _r((total_exp / total_rev) * 100) if total_rev else 0.0,
    }


def _monthly_trends(
    df: pd.DataFrame,
    rev: str,
    exp: str,
    month_col: str | None,
) -> dict:
    rows = _build_row_list(df, rev, exp, month_col)

    # Month-over-month growth rates (revenue & profit)
    rev_values = [r["revenue"] for r in rows]
    profit_values = [r["profit"] for r in rows]

    for i, row in enumerate(rows):
        row["revenue_mom_pct"] = (
            _r(((rev_values[i] - rev_values[i - 1]) / abs(rev_values[i - 1])) * 100)
            if i > 0 and rev_values[i - 1] != 0 else None
        )
        row["profit_mom_pct"] = (
            _r(((profit_values[i] - profit_values[i - 1]) / abs(profit_values[i - 1])) * 100)
            if i > 0 and profit_values[i - 1] != 0 else None
        )

    best = max(rows, key=lambda r: r["profit"])
    worst = min(rows, key=lambda r: r["profit"])

    return {
        "months": rows,
        "best_month": best["month"],
        "worst_month": worst["month"],
        "avg_monthly_revenue_growth_pct": _r(
            pd.Series([r["revenue_mom_pct"] for r in rows if r["revenue_mom_pct"] is not None]).mean()
        ),
    }


def _detect_anomalies(
    df: pd.DataFrame,
    rev: str,
    exp: str,
    month_col: str | None,
) -> dict:
    """
    IQR-based anomaly detection on revenue, expenses, and profit.
    A value is flagged as an anomaly if it falls below Q1 - 1.5*IQR
    or above Q3 + 1.5*IQR.
    """
    series_map = {
        "revenue": df[rev],
        "expenses": df[exp],
        "profit": df["_profit"],
    }

    flags: dict[str, list[dict]] = {"revenue": [], "expenses": [], "profit": []}

    for metric, series in series_map.items():
        q1, q3 = series.quantile(0.25), series.quantile(0.75)
        iqr = q3 - q1
        lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr

        for idx, val in series.items():
            if val < lower or val > upper:
                label = _row_label(df, idx, month_col)
                flags[metric].append({
                    "row": label,
                    "value": _r(val),
                    "direction": "high" if val > upper else "low",
                    "lower_bound": _r(lower),
                    "upper_bound": _r(upper),
                    "deviation_pct": _r(
                        ((val - series.mean()) / series.std()) * 100
                        if series.std() else 0
                    ),
                })

    total_anomalies = sum(len(v) for v in flags.values())
    return {
        "total_anomalies_found": total_anomalies,
        "method": "IQR (Q1 - 1.5*IQR  /  Q3 + 1.5*IQR)",
        "by_metric": flags,
    }


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def _build_row_list(df, rev, exp, month_col):
    if month_col and month_col in df.columns:
        # Sort by calendar order if values match month names, else as-is
        unique_months = df[month_col].tolist()
        if all(m in MONTH_ORDER for m in unique_months):
            df = df.copy()
            df["_month_order"] = df[month_col].map(MONTH_ORDER.index)
            df = df.sort_values("_month_order")

        rows = []
        for _, row in df.iterrows():
            rows.append({
                "month": str(row[month_col]),
                "revenue": _r(row[rev]),
                "expenses": _r(row[exp]),
                "profit": _r(row["_profit"]),
                "profit_margin_pct": _r((row["_profit"] / row[rev]) * 100) if row[rev] else 0.0,
            })
        return rows

    # No month column — use row index
    return [
        {
            "month": f"Row {i + 1}",
            "revenue": _r(row[rev]),
            "expenses": _r(row[exp]),
            "profit": _r(row["_profit"]),
            "profit_margin_pct": _r((row["_profit"] / row[rev]) * 100) if row[rev] else 0.0,
        }
        for i, (_, row) in enumerate(df.iterrows())
    ]


def _row_label(df: pd.DataFrame, idx, month_col: str | None) -> str:
    if month_col and month_col in df.columns:
        return str(df.at[idx, month_col])
    return f"Row {idx + 1}"


def _r(val) -> float:
    """Round to 2 decimal places, handle NaN gracefully."""
    try:
        return round(float(val), 2)
    except (TypeError, ValueError):
        return 0.0

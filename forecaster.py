"""
Revenue forecasting using scikit-learn.

Strategy
--------
1. Encode each row as a time-step index (t = 0, 1, 2 …).
2. Fit THREE models on [revenue ~ t]:
   - Linear Regression       (straight trend line)
   - Polynomial Regression   (degree-2 curve, handles acceleration)
   - Ridge Regression        (regularised linear, more stable on small data)
3. Pick the best model by lowest RMSE on the training data.
4. Predict t+1, t+2, t+3 with the winner.
5. Return predictions, model comparison, and confidence intervals
   (mean ± 1.96 × residual std  →  ~95 % interval).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import PolynomialFeatures, StandardScaler
from sklearn.metrics import mean_squared_error

from analyzer import MONTH_ORDER


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def forecast_revenue(
    df: pd.DataFrame,
    revenue_col: str,
    month_col: str | None = None,
    periods: int = 3,
) -> dict:
    """
    Train models on historical revenue and forecast `periods` steps ahead.

    Returns a dict with:
      - best_model        name of the winning model
      - model_comparison  RMSE + R² for all three models
      - historical        list of {month, revenue, fitted} for training rows
      - forecast          list of {month, predicted_revenue, lower_95, upper_95}
      - trend             'growth' | 'decline' | 'flat'
    """
    series, labels = _extract_series(df, revenue_col, month_col)
    n = len(series)

    if n < 3:
        raise ValueError("Need at least 3 data points to forecast.")

    X = np.arange(n).reshape(-1, 1).astype(float)
    y = series.astype(float)

    models = _build_models()
    results = {}
    for name, model in models.items():
        model.fit(X, y)
        y_pred = model.predict(X)
        rmse = float(np.sqrt(mean_squared_error(y, y_pred)))
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - y.mean()) ** 2)
        r2 = float(1 - ss_res / ss_tot) if ss_tot else 0.0
        results[name] = {"model": model, "rmse": round(rmse, 2), "r2": round(r2, 4)}

    best_name = min(results, key=lambda k: results[k]["rmse"])
    best_model = results[best_name]["model"]

    # Residual std on best model → confidence interval
    residuals = y - best_model.predict(X)
    residual_std = float(np.std(residuals))

    # Historical fitted values
    fitted = best_model.predict(X)
    historical = [
        {
            "month": labels[i],
            "actual_revenue": round(float(y[i]), 2),
            "fitted_revenue": round(float(fitted[i]), 2),
        }
        for i in range(n)
    ]

    # Forecast future steps
    X_future = np.arange(n, n + periods).reshape(-1, 1).astype(float)
    future_preds = best_model.predict(X_future)
    future_labels = _next_month_labels(labels, periods)

    forecast = [
        {
            "month": future_labels[i],
            "predicted_revenue": round(float(future_preds[i]), 2),
            "lower_95": round(float(future_preds[i] - 1.96 * residual_std), 2),
            "upper_95": round(float(future_preds[i] + 1.96 * residual_std), 2),
        }
        for i in range(periods)
    ]

    # Simple trend direction from slope of linear component
    trend = _trend_label(float(y[0]), float(y[-1]))

    return {
        "best_model": best_name,
        "model_comparison": {
            name: {"rmse": v["rmse"], "r2": v["r2"]}
            for name, v in results.items()
        },
        "historical": historical,
        "forecast": forecast,
        "trend": trend,
        "data_points_used": n,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_models() -> dict:
    return {
        "LinearRegression": LinearRegression(),
        "PolynomialRegression(deg=2)": Pipeline([
            ("poly", PolynomialFeatures(degree=2, include_bias=False)),
            ("scaler", StandardScaler()),
            ("reg", LinearRegression()),
        ]),
        "Ridge": Pipeline([
            ("scaler", StandardScaler()),
            ("reg", Ridge(alpha=1.0)),
        ]),
    }


def _extract_series(
    df: pd.DataFrame,
    revenue_col: str,
    month_col: str | None,
) -> tuple[np.ndarray, list[str]]:
    """Return (revenue_array, label_list) in chronological order."""
    if month_col and month_col in df.columns:
        months = df[month_col].tolist()
        # Sort by calendar order if values are month names
        if all(m in MONTH_ORDER for m in months):
            df = df.copy()
            df["_order"] = df[month_col].map(MONTH_ORDER.index)
            df = df.sort_values("_order")
        labels = df[month_col].astype(str).tolist()
    else:
        labels = [f"Period {i + 1}" for i in range(len(df))]

    return df[revenue_col].to_numpy(dtype=float), labels


def _next_month_labels(past_labels: list[str], n: int) -> list[str]:
    """
    If past labels are calendar month names, continue the sequence.
    Otherwise return 'Period N+1', 'Period N+2' …
    """
    if past_labels and past_labels[-1] in MONTH_ORDER:
        last_idx = MONTH_ORDER.index(past_labels[-1])
        return [MONTH_ORDER[(last_idx + 1 + i) % 12] for i in range(n)]
    last_num = len(past_labels)
    return [f"Period {last_num + i + 1}" for i in range(n)]


def _trend_label(first: float, last: float) -> str:
    pct = ((last - first) / abs(first) * 100) if first else 0
    if pct > 5:
        return "growth"
    if pct < -5:
        return "decline"
    return "flat"

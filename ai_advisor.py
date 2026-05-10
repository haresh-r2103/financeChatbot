"""
AI financial advisor powered by Google Gemini.

Improvements over original:
- Retry logic with exponential backoff
- Timeout handling
- Graceful fallback when JSON parsing fails
- Better system prompt for finance domain
- Proper logging
"""
from __future__ import annotations

import json
import logging
import os
import time

from google import genai
from google.genai import types
import pandas as pd

from analyzer import analyze
from forecaster import forecast_revenue

log = logging.getLogger("financebot.ai")

_SYSTEM_PROMPT = """\
You are a senior financial analyst AI assistant working for a CFO-level audience.

You will be given a structured JSON report containing:
- Company financial totals (revenue, expenses, profit)
- Monthly trends with month-over-month growth rates
- Anomaly detection results (IQR-based)
- ML-based revenue forecast for the next 3 months

Your job is to answer the user's question with precise, data-driven reasoning.

## Output format (STRICT JSON — no markdown, no prose outside the JSON)

{
  "profit_health": "good | warning | critical",
  "summary": "<2-3 sentence plain-English overview of the financial situation>",
  "root_causes": [
    {
      "cause": "<short label>",
      "evidence": "<what in the data supports this>",
      "severity": "high | medium | low"
    }
  ],
  "suggestions": [
    {
      "action": "<concrete, actionable recommendation>",
      "expected_impact": "<what metric improves and by roughly how much>",
      "priority": "immediate | short_term | long_term"
    }
  ],
  "outlook": "<forward-looking statement based on the forecast data>"
}

Rules:
- Every claim must cite a specific number or trend from the data.
- Root causes must be ordered by severity (high first).
- Suggestions must be ordered by priority (immediate first).
- Do NOT invent data not present in the report.
- Return ONLY valid JSON. No ```json fences, no extra keys, no trailing commas.
- If the data doesn't support root causes or suggestions, use empty arrays.
"""

MAX_RETRIES = 2
RETRY_DELAY = 1.5  # seconds


def ask_advisor(
    df: pd.DataFrame,
    revenue_col: str,
    expense_col: str,
    month_col: str | None,
    question: str = "Why is my profit decreasing?",
) -> dict:
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError(
            "Gemini API key not found. Set GEMINI_API_KEY (or GOOGLE_API_KEY) in your .env file."
        )

    # 1. Gather context
    analysis = analyze(df, revenue_col, expense_col, month_col)
    try:
        fcast = forecast_revenue(df, revenue_col, month_col, periods=3)
    except ValueError:
        fcast = {"note": "Not enough data for forecasting"}

    # 2. Build report payload
    report = {
        "user_question": question,
        "financial_report": {
            "totals": analysis["totals"],
            "monthly_trends": analysis["monthly_trends"],
            "anomalies": analysis["anomalies"],
            "forecast": fcast,
        },
    }

    user_message = (
        "Here is the company financial report:\n\n"
        + json.dumps(report, indent=2)
        + "\n\nPlease answer the question and provide your structured JSON response."
    )

    # 3. Call Gemini with retry
    client = genai.Client(api_key=api_key)
    raw_text = None
    last_error = None

    for attempt in range(1, MAX_RETRIES + 2):
        try:
            log.info("Gemini call attempt %d/%d", attempt, MAX_RETRIES + 1)
            response = client.models.generate_content(
                model="gemini-1.5-flash",
                contents=user_message,
                config=types.GenerateContentConfig(
                    system_instruction=_SYSTEM_PROMPT,
                    temperature=0.3,
                    max_output_tokens=2048,
                ),
            )

            if not response or not response.text:
                raise ValueError("Empty response from Gemini API")

            raw_text = response.text.strip()
            break

        except Exception as exc:
            last_error = exc
            log.warning("Gemini attempt %d failed: %s", attempt, exc)

            # Fail fast for invalid API keys; retries won't help.
            err_text = str(exc)
            if "API_KEY_INVALID" in err_text or "API key not valid" in err_text:
                raise ValueError(
                    "Invalid Gemini API key. Update GEMINI_API_KEY in .env with a valid key from https://aistudio.google.com/apikey and restart the backend."
                ) from exc

            if "RESOURCE_EXHAUSTED" in err_text or "Quota exceeded" in err_text:
                raise ValueError(
                    "Gemini quota exceeded or unavailable for this project. Enable billing/check quotas in Google AI Studio and try again. See https://ai.google.dev/gemini-api/docs/rate-limits"
                ) from exc

            if attempt <= MAX_RETRIES:
                time.sleep(RETRY_DELAY * attempt)
            else:
                raise ValueError(
                    f"Gemini API error after {MAX_RETRIES + 1} attempts: {last_error}"
                ) from exc

    if not raw_text:
        raise ValueError("Gemini returned an empty response")

    # 4. Parse JSON response (strip markdown fences if present)
    cleaned = raw_text
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[-1]
        cleaned = cleaned.rsplit("```", 1)[0].strip()

    try:
        advice = json.loads(cleaned)
    except json.JSONDecodeError:
        log.warning("Gemini response was not valid JSON, building fallback")
        # Fallback: wrap raw text as a summary
        advice = {
            "profit_health": "warning",
            "summary": raw_text[:500],
            "root_causes": [],
            "suggestions": [],
            "outlook": "Unable to parse structured response. Please try rephrasing your question.",
        }

    return {
        "advice": advice,
        "data_context": {
            "months_analyzed": len(analysis["monthly_trends"]["months"]),
            "best_month": analysis["monthly_trends"]["best_month"],
            "worst_month": analysis["monthly_trends"]["worst_month"],
            "total_anomalies": analysis["anomalies"]["total_anomalies_found"],
            "forecast_trend": fcast.get("trend"),
            "model_used": "gemini-1.5-flash",
        },
    }

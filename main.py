"""
FinanceBot API — FastAPI backend
"""
import logging
import io
import os
import uuid
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv
import pandas as pd

load_dotenv()

from typing import Optional
from storage import store_dataframe, get_dataframe, list_uploads
from analyzer import analyze
from forecaster import forecast_revenue
from ai_advisor import ask_advisor
from auth import register_user, login_user

# ── Logging ──────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(levelname)-7s │ %(name)s │ %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("financebot")

# ── App ──────────────────────────────────────────────────────────
app = FastAPI(title="Finance Bot API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Global exception handler ────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    log.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {exc}"},
    )


# ── Models ───────────────────────────────────────────────────────
class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class ChatRequest(BaseModel):
    question: str
    file_id: Optional[str] = None
    revenue_col: Optional[str] = None
    expense_col: Optional[str] = None
    month_col: Optional[str] = None


# ── Health check ─────────────────────────────────────────────────
@app.get("/health")
def health():
    gemini_key_present = bool(
        os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    )
    return {
        "status": "ok",
        "gemini_configured": gemini_key_present,
    }


# ── Auth ─────────────────────────────────────────────────────────
@app.post("/auth/register")
def auth_register(body: RegisterRequest):
    log.info("Register attempt: %s", body.email)
    try:
        return register_user(body.name, body.email, body.password)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/auth/login")
def auth_login(body: LoginRequest):
    log.info("Login attempt: %s", body.email)
    try:
        return login_user(body.email, body.password)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


# ── Upload ───────────────────────────────────────────────────────
@app.post("/upload")
async def upload_csv(file: UploadFile = File(...)):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported")

    contents = await file.read()
    try:
        df = pd.read_csv(io.StringIO(contents.decode("utf-8")))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse CSV: {e}")

    if df.empty:
        raise HTTPException(status_code=400, detail="CSV file is empty")

    file_id = str(uuid.uuid4())
    store_dataframe(file_id, df, file.filename)
    log.info("Uploaded %s → %s (%d rows)", file.filename, file_id, len(df))

    return {
        "file_id": file_id,
        "filename": file.filename,
        "rows": len(df),
        "columns": list(df.columns),
    }


# ── Summary ──────────────────────────────────────────────────────
@app.get("/summary/{file_id}")
def get_summary(
    file_id: str,
    revenue_col: Optional[str] = None,
    expense_col: Optional[str] = None,
):
    entry = get_dataframe(file_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="File not found")

    df: pd.DataFrame = entry["df"]
    numeric_cols = df.select_dtypes(include="number").columns.tolist()

    revenue_col = revenue_col or _detect_col(numeric_cols, ["revenue", "income", "sales", "turnover"])
    expense_col = expense_col or _detect_col(numeric_cols, ["expense", "cost", "expenditure", "spending"])

    if not revenue_col or revenue_col not in df.columns:
        raise HTTPException(
            status_code=422,
            detail=f"Revenue column not found. Available numeric columns: {numeric_cols}",
        )
    if not expense_col or expense_col not in df.columns:
        raise HTTPException(
            status_code=422,
            detail=f"Expense column not found. Available numeric columns: {numeric_cols}",
        )

    revenue = df[revenue_col].dropna()
    expenses = df[expense_col].dropna()
    profit = revenue - expenses

    return {
        "file_id": file_id,
        "filename": entry["filename"],
        "rows_analyzed": len(df),
        "columns_used": {"revenue": revenue_col, "expense": expense_col},
        "revenue": {
            "total": round(float(revenue.sum()), 2),
            "mean": round(float(revenue.mean()), 2),
            "min": round(float(revenue.min()), 2),
            "max": round(float(revenue.max()), 2),
        },
        "expenses": {
            "total": round(float(expenses.sum()), 2),
            "mean": round(float(expenses.mean()), 2),
            "min": round(float(expenses.min()), 2),
            "max": round(float(expenses.max()), 2),
        },
        "profit": {
            "total": round(float(profit.sum()), 2),
            "mean": round(float(profit.mean()), 2),
            "min": round(float(profit.min()), 2),
            "max": round(float(profit.max()), 2),
            "profitable_periods": int((profit > 0).sum()),
            "loss_periods": int((profit < 0).sum()),
        },
        "profit_margin_pct": round(float((profit.sum() / revenue.sum()) * 100), 2)
        if revenue.sum() != 0
        else 0.0,
    }


# ── Analyze ──────────────────────────────────────────────────────
@app.get("/analyze/{file_id}")
def analyze_file(
    file_id: str,
    revenue_col: Optional[str] = None,
    expense_col: Optional[str] = None,
    month_col: Optional[str] = None,
):
    entry = get_dataframe(file_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="File not found")

    df = entry["df"]
    numeric_cols = df.select_dtypes(include="number").columns.tolist()

    revenue_col = revenue_col or _detect_col(numeric_cols, ["revenue", "income", "sales", "turnover"])
    expense_col = expense_col or _detect_col(numeric_cols, ["expense", "cost", "expenditure", "spending"])
    month_col = month_col or _detect_col(list(df.columns), ["month", "date", "period", "week"])

    if not revenue_col or revenue_col not in df.columns:
        raise HTTPException(
            status_code=422,
            detail=f"Revenue column not found. Available numeric columns: {numeric_cols}",
        )
    if not expense_col or expense_col not in df.columns:
        raise HTTPException(
            status_code=422,
            detail=f"Expense column not found. Available numeric columns: {numeric_cols}",
        )

    result = analyze(df, revenue_col, expense_col, month_col)
    return {
        "file_id": file_id,
        "filename": entry["filename"],
        "columns_used": {"revenue": revenue_col, "expense": expense_col, "month": month_col},
        **result,
    }


# ── Forecast ─────────────────────────────────────────────────────
@app.get("/forecast/{file_id}")
def forecast(
    file_id: str,
    revenue_col: Optional[str] = None,
    month_col: Optional[str] = None,
    periods: int = 3,
):
    entry = get_dataframe(file_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="File not found")

    df = entry["df"]
    numeric_cols = df.select_dtypes(include="number").columns.tolist()

    revenue_col = revenue_col or _detect_col(numeric_cols, ["revenue", "income", "sales", "turnover"])
    month_col = month_col or _detect_col(list(df.columns), ["month", "date", "period", "week"])

    if not revenue_col or revenue_col not in df.columns:
        raise HTTPException(
            status_code=422,
            detail=f"Revenue column not found. Available numeric columns: {numeric_cols}",
        )
    if periods < 1 or periods > 12:
        raise HTTPException(status_code=422, detail="periods must be between 1 and 12")

    try:
        result = forecast_revenue(df, revenue_col, month_col, periods)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    return {
        "file_id": file_id,
        "filename": entry["filename"],
        "columns_used": {"revenue": revenue_col, "month": month_col},
        **result,
    }


# ── Ask AI (GET — kept for backward compat) ─────────────────────
@app.get("/ask/{file_id}")
def ask_get(
    file_id: str,
    question: str = "Why is my profit decreasing?",
    revenue_col: Optional[str] = None,
    expense_col: Optional[str] = None,
    month_col: Optional[str] = None,
):
    return _ask_impl(file_id, question, revenue_col, expense_col, month_col)


# ── Ask AI (POST — preferred for chat) ──────────────────────────
@app.post("/ask")
def ask_post(body: ChatRequest):
    if not body.file_id:
        raise HTTPException(status_code=400, detail="file_id is required")
    return _ask_impl(
        body.file_id, body.question,
        body.revenue_col, body.expense_col, body.month_col,
    )


def _ask_impl(
    file_id: str,
    question: str,
    revenue_col: Optional[str],
    expense_col: Optional[str],
    month_col: Optional[str],
):
    entry = get_dataframe(file_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="File not found")

    if not os.environ.get("GEMINI_API_KEY"):
        raise HTTPException(status_code=503, detail="GEMINI_API_KEY environment variable not set")

    if not question or not question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    df = entry["df"]
    numeric_cols = df.select_dtypes(include="number").columns.tolist()

    revenue_col = revenue_col or _detect_col(numeric_cols, ["revenue", "income", "sales", "turnover"])
    expense_col = expense_col or _detect_col(numeric_cols, ["expense", "cost", "expenditure", "spending"])
    month_col = month_col or _detect_col(list(df.columns), ["month", "date", "period", "week"])

    if not revenue_col or revenue_col not in df.columns:
        raise HTTPException(
            status_code=422,
            detail=f"Revenue column not found. Available numeric columns: {numeric_cols}",
        )
    if not expense_col or expense_col not in df.columns:
        raise HTTPException(
            status_code=422,
            detail=f"Expense column not found. Available numeric columns: {numeric_cols}",
        )

    log.info("AI Ask: file=%s q=%s", file_id[:8], question[:60])

    try:
        result = ask_advisor(df, revenue_col, expense_col, month_col, question)
    except ValueError as e:
        log.error("AI advisor error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "file_id": file_id,
        "filename": entry["filename"],
        "question": question,
        **result,
    }


# ── List uploads ─────────────────────────────────────────────────
@app.get("/uploads")
def list_all_uploads():
    return {"uploads": list_uploads()}


# ── Column info ──────────────────────────────────────────────────
@app.get("/columns/{file_id}")
def get_columns(file_id: str):
    entry = get_dataframe(file_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="File not found")
    df: pd.DataFrame = entry["df"]
    return {
        "file_id": file_id,
        "all_columns": list(df.columns),
        "numeric_columns": df.select_dtypes(include="number").columns.tolist(),
    }


# ── Serve frontend (production) ─────────────────────────────────
DIST = Path(__file__).parent / "frontend" / "dist"
if DIST.is_dir():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/{full_path:path}")
    def serve_spa(full_path: str):
        """Fallback: serve index.html for SPA client-side routing."""
        file = DIST / full_path
        if file.is_file():
            return FileResponse(file)
        return FileResponse(DIST / "index.html")


# ── Helpers ──────────────────────────────────────────────────────
def _detect_col(columns: list[str], keywords: list[str]) -> Optional[str]:
    for col in columns:
        if any(kw in col.lower() for kw in keywords):
            return col
    return None

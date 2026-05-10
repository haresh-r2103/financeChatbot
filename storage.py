"""In-memory store for uploaded DataFrames. Replace with a database for production."""
import pandas as pd
from datetime import datetime
from typing import Optional

_store: dict[str, dict] = {}


def store_dataframe(file_id: str, df: pd.DataFrame, filename: str) -> None:
    _store[file_id] = {
        "df": df,
        "filename": filename,
        "uploaded_at": datetime.utcnow().isoformat(),
    }


def get_dataframe(file_id: str) -> Optional[dict]:
    return _store.get(file_id)


def list_uploads() -> list[dict]:
    return [
        {
            "file_id": fid,
            "filename": entry["filename"],
            "rows": len(entry["df"]),
            "uploaded_at": entry["uploaded_at"],
        }
        for fid, entry in _store.items()
    ]

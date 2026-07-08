"""Génération d'identifiants et d'horodatages, partagée entre src/data.py et
src/collection_runner.py (aucune dépendance à Streamlit)."""

import uuid
from datetime import datetime, timezone


def new_id() -> str:
    return uuid.uuid4().hex[:12]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

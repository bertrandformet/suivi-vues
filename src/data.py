"""Chargement des données et logique métier (dossiers, regroupements, URLs suivies, relevés de vues)."""

from __future__ import annotations

import pandas as pd

from src import github_store as store
from src.ids import new_id as _new_id
from src.ids import now_iso as _now_iso
from src.paths import CONTENTS_PATH, DOSSIERS_PATH, PLATFORMS_PATH, SNAPSHOTS_PATH, TRACKED_URLS_PATH


def load_platforms() -> pd.DataFrame:
    return store.read_csv(PLATFORMS_PATH)


def load_dossiers() -> pd.DataFrame:
    return store.read_csv(DOSSIERS_PATH)


def load_contents() -> pd.DataFrame:
    return store.read_csv(CONTENTS_PATH)


def load_tracked_urls() -> pd.DataFrame:
    return store.read_csv(TRACKED_URLS_PATH)


def load_snapshots() -> pd.DataFrame:
    df = store.read_csv(SNAPSHOTS_PATH)
    if not df.empty:
        df["view_count"] = pd.to_numeric(df["view_count"], errors="coerce")
        df["recorded_at"] = pd.to_datetime(df["recorded_at"], errors="coerce")
        # entered_at est stocké en UTC (voir src/ids.now_iso) ; on le garde tz-aware
        # ici pour que l'affichage puisse le reconvertir vers l'heure de Paris.
        df["entered_at"] = pd.to_datetime(df["entered_at"], errors="coerce", utc=True)
    return df


def enriched_tracked_urls(dossier_id: str | None = None) -> pd.DataFrame:
    """tracked_urls jointes avec le nom de plateforme et le titre du contenu (si présent).

    Filtre optionnellement sur `dossier_id` (une URL suivie appartient à exactement un dossier).
    """
    urls = load_tracked_urls()
    if urls.empty:
        return urls
    if dossier_id is not None:
        urls = urls[urls["dossier_id"] == dossier_id]
        if urls.empty:
            return urls
    platforms = load_platforms().rename(columns={"id": "platform_id", "name": "platform_name"})
    contents = load_contents().rename(columns={"id": "content_id", "title": "content_title"})
    merged = urls.merge(platforms[["platform_id", "platform_name"]], on="platform_id", how="left")
    merged = merged.merge(contents[["content_id", "content_title"]], on="content_id", how="left")
    return merged


def add_dossier(name: str, description: str, user: str) -> str:
    dossier_id = _new_id()
    row = {
        "id": dossier_id,
        "name": name,
        "description": description,
        "created_by": user,
        "created_at": _now_iso(),
    }
    store.append_row(DOSSIERS_PATH, row, f"Ajout dossier: {name} (par {user})")
    return dossier_id


def add_content(title: str, description: str, user: str, dossier_id: str) -> str:
    content_id = _new_id()
    row = {
        "id": content_id,
        "title": title,
        "description": description,
        "dossier_id": dossier_id,
        "created_by": user,
        "created_at": _now_iso(),
    }
    store.append_row(CONTENTS_PATH, row, f"Ajout regroupement: {title} (par {user})")
    return content_id


def add_tracked_url(
    content_id: str | None,
    platform_id: str,
    url: str,
    label: str,
    user: str,
    dossier_id: str,
    collection_method: str = "manual",
) -> str:
    url_id = _new_id()
    row = {
        "id": url_id,
        "content_id": content_id or "",
        "platform_id": platform_id,
        "url": url,
        "label": label,
        "collection_method": collection_method,
        "dossier_id": dossier_id,
        "added_by": user,
        "added_at": _now_iso(),
    }
    store.append_row(TRACKED_URLS_PATH, row, f"Ajout URL suivie: {label} [{platform_id}] (par {user})")
    return url_id


def add_snapshot(
    tracked_url_id: str,
    recorded_at,
    view_count: int,
    user: str,
    source: str = "manual",
    note: str = "",
    url_label: str = "",
) -> str:
    snapshot_id = _new_id()
    recorded_at_str = recorded_at.isoformat() if hasattr(recorded_at, "isoformat") else str(recorded_at)
    row = {
        "id": snapshot_id,
        "tracked_url_id": tracked_url_id,
        "recorded_at": recorded_at_str,
        "view_count": int(view_count),
        "source": source,
        "note": note,
        "entered_by": user,
        "entered_at": _now_iso(),
    }
    label = url_label or tracked_url_id
    message = f"Vue: {label} — {recorded_at_str} — {view_count} vues ({source}, par {user})"
    store.append_row(SNAPSHOTS_PATH, row, message)
    return snapshot_id


def delete_snapshot(snapshot_id: str, user: str):
    store.remove_row(SNAPSHOTS_PATH, snapshot_id, f"Suppression relevé {snapshot_id} (par {user})")


def latest_per_url_and_date(snapshots: pd.DataFrame) -> pd.DataFrame:
    """Pour chaque (tracked_url_id, recorded_at), ne garde que la dernière saisie (entered_at)."""
    if snapshots.empty:
        return snapshots
    df = snapshots.copy()
    df["entered_at"] = pd.to_datetime(df["entered_at"], errors="coerce")
    df = df.sort_values("entered_at")
    return df.drop_duplicates(subset=["tracked_url_id", "recorded_at"], keep="last")

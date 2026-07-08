"""Client pur (sans Streamlit) pour l'API Contents de GitHub.

Utilisé à la fois par l'adaptateur Streamlit (src/github_store.py) et par le
script autonome de collecte (scripts/run_collection.py), pour n'avoir qu'un
seul chemin de lecture/écriture des CSV, quel que soit le déclencheur.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
from io import StringIO

import pandas as pd
import requests

API_ROOT = "https://api.github.com"


@dataclass
class GitHubConfig:
    token: str
    repo: str
    branch: str = "main"


class ConflictError(Exception):
    pass


def _headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }


def get_file(cfg: GitHubConfig, path: str):
    """Retourne (contenu_texte, sha) ou (None, None) si le fichier n'existe pas encore."""
    url = f"{API_ROOT}/repos/{cfg.repo}/contents/{path}"
    resp = requests.get(url, headers=_headers(cfg.token), params={"ref": cfg.branch}, timeout=15)
    if resp.status_code == 404:
        return None, None
    resp.raise_for_status()
    payload = resp.json()
    content = base64.b64decode(payload["content"]).decode("utf-8")
    return content, payload["sha"]


def put_file(cfg: GitHubConfig, path: str, content: str, sha: str | None, message: str) -> str:
    url = f"{API_ROOT}/repos/{cfg.repo}/contents/{path}"
    body = {
        "message": message,
        "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
        "branch": cfg.branch,
    }
    if sha:
        body["sha"] = sha
    resp = requests.put(url, headers=_headers(cfg.token), json=body, timeout=15)
    if resp.status_code == 409:
        raise ConflictError(f"Conflit d'écriture sur {path}")
    resp.raise_for_status()
    return resp.json()["content"]["sha"]


def read_csv(cfg: GitHubConfig, path: str) -> pd.DataFrame:
    content, _ = get_file(cfg, path)
    if content is None:
        return pd.DataFrame()
    return pd.read_csv(StringIO(content), dtype=str, keep_default_na=False)


def append_row(cfg: GitHubConfig, path: str, row: dict, message: str, retry: bool = True):
    """Ajoute une ligne au CSV distant (lecture fraîche + écriture, jamais de suppression/édition).

    Relit toujours l'état le plus récent avant d'écrire pour éviter d'écraser
    une modification concurrente ; retente une fois en cas de conflit de sha.
    """
    content, sha = get_file(cfg, path)
    if content is None:
        df = pd.DataFrame(columns=list(row.keys()))
    else:
        df = pd.read_csv(StringIO(content), dtype=str, keep_default_na=False)
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    csv_text = df.to_csv(index=False)
    try:
        put_file(cfg, path, csv_text, sha, message)
    except ConflictError:
        if not retry:
            raise
        return append_row(cfg, path, row, message, retry=False)
    return df

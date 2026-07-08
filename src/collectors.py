"""Collecteurs automatiques de vues, purs (aucune dépendance à Streamlit).

Chaque collecteur prend une URL (+ des options via **kwargs, ignorées si non
utilisées) et retourne un nombre de vues (int), ou lève une exception claire
en cas d'échec. Pour ajouter une future source automatique (quelle qu'elle
soit, pas forcément une des plateformes existantes), il suffit d'écrire une
fonction `collect_xxx(url, **kwargs)` et de l'enregistrer dans COLLECTORS.
"""

from __future__ import annotations

import re
from urllib.parse import urlparse

import requests

YOUTUBE_API_URL = "https://www.googleapis.com/youtube/v3/videos"

_YOUTUBE_PATTERNS = [
    re.compile(r"(?:youtube\.com/watch\?v=|youtube\.com/shorts/|youtube\.com/embed/|youtu\.be/)([A-Za-z0-9_-]{6,})"),
]

_PEERTUBE_PATTERN = re.compile(r"/(?:w|videos/watch)/([0-9a-fA-F-]{20,})")


class CollectorError(Exception):
    pass


def extract_youtube_id(url: str) -> str:
    for pattern in _YOUTUBE_PATTERNS:
        match = pattern.search(url)
        if match:
            return match.group(1)
    raise CollectorError(f"Impossible d'extraire l'ID YouTube depuis: {url}")


def extract_peertube_ref(url: str) -> tuple[str, str]:
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        raise CollectorError(f"URL PeerTube invalide: {url}")
    match = _PEERTUBE_PATTERN.search(parsed.path)
    if not match:
        raise CollectorError(f"Impossible d'extraire l'identifiant de la vidéo PeerTube depuis: {url}")
    instance = f"{parsed.scheme}://{parsed.netloc}"
    return instance, match.group(1)


def collect_youtube(url: str, api_key: str | None = None, **_kwargs) -> int:
    if not api_key:
        raise CollectorError("Clé API YouTube manquante (secrets[youtube][api_key]).")
    video_id = extract_youtube_id(url)
    resp = requests.get(
        YOUTUBE_API_URL,
        params={"part": "statistics", "id": video_id, "key": api_key},
        timeout=15,
    )
    resp.raise_for_status()
    items = resp.json().get("items", [])
    if not items:
        raise CollectorError(f"Vidéo YouTube introuvable ou privée: {video_id}")
    return int(items[0]["statistics"]["viewCount"])


def collect_peertube(url: str, **_kwargs) -> int:
    instance, video_uuid = extract_peertube_ref(url)
    resp = requests.get(f"{instance}/api/v1/videos/{video_uuid}", timeout=15)
    resp.raise_for_status()
    return int(resp.json()["views"])


COLLECTORS = {
    "youtube": collect_youtube,
    "peertube": collect_peertube,
}

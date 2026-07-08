"""Chemins des fichiers CSV de données dans le dépôt. Sans dépendance, partagé
entre le code Streamlit (src/data.py) et le runner de collecte autonome
(src/collection_runner.py, scripts/run_collection.py)."""

PLATFORMS_PATH = "data/platforms.csv"
CONTENTS_PATH = "data/contents.csv"
TRACKED_URLS_PATH = "data/tracked_urls.csv"
SNAPSHOTS_PATH = "data/snapshots.csv"

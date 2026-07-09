"""Cœur de la collecte automatique — pur (aucune dépendance à Streamlit).

Utilisé à la fois par le bouton "Lancer la collecte maintenant" du dashboard
(config issue de st.secrets) et par le script autonome scripts/run_collection.py
(config issue des variables d'environnement, pour la tâche planifiée GitHub
Actions). Un seul chemin d'écriture des relevés (via src/gh_api.py), quel que
soit le déclencheur.
"""

from __future__ import annotations

from src import gh_api
from src.collectors import COLLECTORS
from src.ids import new_id, now_iso
from src.paths import SNAPSHOTS_PATH, TRACKED_URLS_PATH


def run_collection(cfg: gh_api.GitHubConfig, api_keys: dict, actor: str, dossier_id: str | None = None) -> list[dict]:
    """Parcourt les URLs suivies dont collection_method a un collecteur enregistré,
    récupère la valeur, écrit un snapshot (source="auto"), et retourne un rapport
    par URL : {tracked_url_id, label, method, status: "ok"|"error", value|error}.

    Si `dossier_id` est fourni, ne collecte que les URLs de ce dossier (utilisé par le
    bouton manuel du dashboard, scopé au dossier ouvert). Sans `dossier_id` (cas de la
    tâche planifiée GitHub Actions), collecte tous les dossiers.
    """
    urls = gh_api.read_csv(cfg, TRACKED_URLS_PATH)
    report = []

    if urls.empty or "collection_method" not in urls.columns:
        return report

    eligible = urls[urls["collection_method"].isin(COLLECTORS.keys())]
    if dossier_id is not None:
        eligible = eligible[eligible["dossier_id"] == dossier_id]

    for _, row in eligible.iterrows():
        method = row["collection_method"]
        label = row["label"]
        collector = COLLECTORS[method]
        entry = {"tracked_url_id": row["id"], "label": label, "method": method}
        try:
            view_count = collector(row["url"], api_key=api_keys.get(method))
        except Exception as exc:  # une erreur par URL ne doit pas arrêter les autres
            entry["status"] = "error"
            entry["error"] = str(exc)
            report.append(entry)
            continue

        snapshot_row = {
            "id": new_id(),
            "tracked_url_id": row["id"],
            "recorded_at": now_iso()[:10],
            "view_count": view_count,
            "source": "auto",
            "note": f"Collecte automatique ({method})",
            "entered_by": actor,
            "entered_at": now_iso(),
        }
        message = f"Collecte auto: {label} — {snapshot_row['recorded_at']} — {view_count} vues ({method})"
        gh_api.append_row(cfg, SNAPSHOTS_PATH, snapshot_row, message)

        entry["status"] = "ok"
        entry["value"] = view_count
        report.append(entry)

    return report

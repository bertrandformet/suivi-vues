#!/usr/bin/env python3
"""Point d'entrée autonome de la collecte automatique (sans Streamlit).

Utilisé par la tâche planifiée GitHub Actions (.github/workflows/collect.yml).
Config lue depuis les variables d'environnement :
  GITHUB_TOKEN, GITHUB_REPO, GITHUB_BRANCH (optionnel, défaut "main")
  YOUTUBE_API_KEY (optionnel — les URLs YouTube échoueront proprement si absent)
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import gh_api  # noqa: E402
from src.collection_runner import run_collection  # noqa: E402


def main() -> int:
    cfg = gh_api.GitHubConfig(
        token=os.environ["GITHUB_TOKEN"],
        repo=os.environ["GITHUB_REPO"],
        branch=os.environ.get("GITHUB_BRANCH", "main"),
    )
    api_keys = {"youtube": os.environ.get("YOUTUBE_API_KEY")}

    report = run_collection(cfg, api_keys, actor="github-actions")

    if not report:
        print("Aucune URL suivie n'est configurée pour la collecte automatique.")
        return 0

    ok = [r for r in report if r["status"] == "ok"]
    errors = [r for r in report if r["status"] == "error"]

    for r in ok:
        print(f"OK    {r['label']} ({r['method']}): {r['value']} vues")
    for r in errors:
        print(f"ERROR {r['label']} ({r['method']}): {r['error']}")

    print(f"\n{len(ok)} relevé(s) enregistré(s), {len(errors)} erreur(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

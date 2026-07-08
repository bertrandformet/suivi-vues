"""Adaptateur Streamlit au-dessus de src/gh_api.py : source la config depuis
st.secrets et ajoute la mise en cache. Le dépôt GitHub sert de base de
données : chaque écriture crée un commit, ce qui donne un historique
d'audit gratuit sans dépendance externe.
"""

from __future__ import annotations

import streamlit as st

from src import gh_api

ConflictError = gh_api.ConflictError


def get_config() -> gh_api.GitHubConfig:
    gh = st.secrets["github"]
    return gh_api.GitHubConfig(gh["token"], gh["repo"], gh.get("branch", "main"))


@st.cache_data(ttl=60, show_spinner=False)
def read_csv(path: str):
    return gh_api.read_csv(get_config(), path)


def append_row(path: str, row: dict, message: str):
    df = gh_api.append_row(get_config(), path, row, message)
    read_csv.clear()
    return df


def remove_row(path: str, row_id: str, message: str):
    df = gh_api.remove_row(get_config(), path, row_id, message)
    read_csv.clear()
    return df

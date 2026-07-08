"""Authentification à deux comptes fixes (admin / lecteur) via streamlit-authenticator."""

import streamlit as st
import streamlit_authenticator as stauth

FIELDS = {
    "Form name": "Connexion",
    "Username": "Identifiant",
    "Password": "Mot de passe",
    "Login": "Se connecter",
}

ROLE_LABELS = {"editeur": "éditeur", "lecteur": "lecteur"}


def _credentials_dict() -> dict:
    raw = st.secrets["auth"]["credentials"]["usernames"]
    return {
        "usernames": {
            username: {"name": info["name"], "password": info["password"]}
            for username, info in raw.items()
        }
    }


def _roles() -> dict:
    raw = st.secrets["auth"]["credentials"]["usernames"]
    return {username: info["role"] for username, info in raw.items()}


def get_authenticator() -> stauth.Authenticate:
    cookie = st.secrets["auth"]["cookie"]
    return stauth.Authenticate(
        _credentials_dict(),
        cookie["name"],
        cookie["key"],
        cookie.get("expiry_days", 30),
    )


def login():
    """Affiche le formulaire de connexion. Retourne (name, username, role) si connecté, sinon None."""
    authenticator = get_authenticator()

    if not st.session_state.get("authentication_status"):
        _, center, _ = st.columns([1, 1, 1])
        with center:
            st.markdown(
                "<div style='text-align:center;margin-bottom:8px'>"
                "<div style='font-weight:700;font-size:20px'>Suivi Vues</div>"
                "<div class='svv-muted'>Suivi des vues et écoutes des contenus surveillés</div>"
                "</div>",
                unsafe_allow_html=True,
            )
            authenticator.login(location="main", fields=FIELDS)
            status = st.session_state.get("authentication_status")
            if status is False:
                st.error("Identifiant ou mot de passe incorrect.")
            else:
                st.markdown(
                    "<div class='svv-muted' style='text-align:center;font-size:12.5px'>"
                    "Accès réservé — contactez l'administrateur pour obtenir un compte."
                    "</div>",
                    unsafe_allow_html=True,
                )
        return None

    username = st.session_state["username"]
    name = st.session_state["name"]
    role = _roles().get(username, "lecteur")
    st.session_state["role"] = role

    with st.sidebar:
        if role != "editeur":
            st.markdown(
                "<div class='svv-muted' style='font-size:13px;margin-bottom:10px'>"
                "Consultation seule — la saisie et la gestion des URLs sont réservées aux éditeurs."
                "</div>",
                unsafe_allow_html=True,
            )
        badge_class = "svv-badge-editeur" if role == "editeur" else "svv-badge-lecteur"
        st.markdown(
            f"<div style='display:flex;align-items:center;gap:8px;margin-bottom:8px'>"
            f"<span>{name}</span>"
            f"<span class='svv-badge {badge_class}'>{ROLE_LABELS.get(role, role)}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )
        authenticator.logout("Se déconnecter", "sidebar")

    return name, username, role


def is_editeur() -> bool:
    return st.session_state.get("role") == "editeur"

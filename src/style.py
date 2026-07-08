"""CSS léger transversal (nombres tabulaires, gris conforme WCAG AA) et
utilitaires de formatage FR, appliqués sur toutes les pages."""

import streamlit as st

MUTED_TEXT = "#5D6B79"

_CSS = f"""
<style>
[data-testid="stMetricValue"], td, th {{
    font-variant-numeric: tabular-nums;
}}
.svv-muted {{ color: {MUTED_TEXT}; font-size: 0.92rem; }}
.svv-badge {{
    display: inline-flex; align-items: center; gap: 6px;
    font-size: 11px; font-weight: 600; letter-spacing: .04em; text-transform: uppercase;
    border-radius: 999px; padding: 2px 8px;
}}
.svv-badge-editeur {{ color: #33618F; background: #E7EEF5; border: 1px solid #C9D8E6; }}
.svv-badge-lecteur {{ color: {MUTED_TEXT}; background: #F0F0ED; border: 1px solid #DDDDD7; }}
</style>
"""


def inject():
    st.markdown(_CSS, unsafe_allow_html=True)


def format_number(value) -> str:
    try:
        return f"{int(value):,}".replace(",", " ")
    except (ValueError, TypeError):
        return str(value)


_MONTHS_FR = [
    "janv.", "févr.", "mars", "avr.", "mai", "juin",
    "juil.", "août", "sept.", "oct.", "nov.", "déc.",
]


def format_date_fr(date) -> str:
    """Formate une date en français ('19 janv. 2026') sans dépendre de la locale système."""
    return f"{date.day} {_MONTHS_FR[date.month - 1]} {date.year}"


def shorten_url(url: str, max_path: int = 18) -> str:
    """Raccourcit une URL pour l'affichage en table : domaine + début du chemin."""
    if not url:
        return url
    stripped = url.split("://", 1)[-1]
    domain, _, path = stripped.partition("/")
    if not path:
        return domain
    if len(path) > max_path:
        path = path[:max_path] + "…"
    return f"{domain}/{path}"


SOURCE_LABELS = {
    "manual": "saisie manuelle",
    "auto": "collecte auto",
    "import": "import CSV",
    "adjustment": "ajustement",
}


def render_footer():
    st.markdown(
        "<div style='margin-top:48px;padding-top:14px;border-top:1px solid #E4E3DF;"
        "font-size:12px;color:#8A94A0'>"
        "© 2026 Bertrand Formet — "
        "<a href='https://creativecommons.org/licenses/by/4.0/' target='_blank' style='color:#8A94A0'>"
        "Licence CC BY 4.0</a>"
        " — <a href='https://github.com/bertrandformet/suivi-vues' target='_blank' style='color:#8A94A0'>"
        "Code source sur GitHub</a></div>",
        unsafe_allow_html=True,
    )

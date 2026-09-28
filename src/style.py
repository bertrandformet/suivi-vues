"""CSS léger transversal (nombres tabulaires, gris conforme WCAG AA) et
utilitaires de formatage FR, appliqués sur toutes les pages."""

import html
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

MUTED_TEXT = "#5D6B79"
LOCAL_TZ = ZoneInfo("Europe/Paris")

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


def to_local(value):
    """Convertit un timestamp (aware, ou naïf supposé UTC — c'est le format de
    stockage de `entered_at`) vers l'heure de Paris, pour l'affichage uniquement."""
    if value is None or pd.isna(value):
        return value
    ts = pd.Timestamp(value)
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")
    return ts.tz_convert(LOCAL_TZ)


def format_datetime_fr(value) -> str:
    """Formate un timestamp en heure de Paris, ex. '9 juil. 2026 à 16:23'."""
    local = to_local(value)
    if local is None or pd.isna(local):
        return str(value)
    return f"{format_date_fr(local)} à {local:%H:%M}"


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


def render_comparison_table(df: pd.DataFrame):
    """Tableau HTML pour le comparateur de périodes : la composition d'un
    cumul thématique s'affiche en sous-texte sous son nom, dans la même
    cellule — st.dataframe ne permet pas ce genre de mise en forme par cellule.
    """
    header_cells = "".join(
        f"<th style='padding:6px 12px;font-size:12.5px;color:{MUTED_TEXT};"
        f"font-weight:600;text-align:{align}'>{label}</th>"
        for label, align in [
            ("Catégorie", "left"), ("Unité", "left"), ("Début", "right"),
            ("Fin", "right"), ("Évolution", "right"), ("Évolution (%)", "right"),
        ]
    )

    def fmt_int(value):
        return format_number(value) if pd.notna(value) else "—"

    rows = []
    for _, r in df.iterrows():
        composition = r.get("Composition") or ""
        sub = (
            f"<br><span style='font-size:11.5px;color:{MUTED_TEXT}'>{html.escape(composition)}</span>"
            if composition else ""
        )
        evol = r["Évolution"]
        evol_color = MUTED_TEXT
        if pd.notna(evol) and evol > 0:
            evol_color = "#1E7A46"
        elif pd.notna(evol) and evol < 0:
            evol_color = "#B3261E"
        evol_text = f"{evol:+,.0f}".replace(",", " ") if pd.notna(evol) else "—"
        pct = r["Évolution (%)"]
        pct_text = f"{pct:+.0f}%" if pd.notna(pct) else "—"
        rows.append(
            "<tr style='border-bottom:1px solid #EDEEF0;'>"
            f"<td style='padding:9px 12px;'>{html.escape(str(r['Catégorie']))}{sub}</td>"
            f"<td style='padding:9px 12px;color:{MUTED_TEXT};'>{html.escape(str(r['Unité']))}</td>"
            f"<td style='padding:9px 12px;text-align:right;font-variant-numeric:tabular-nums;'>{fmt_int(r['Début'])}</td>"
            f"<td style='padding:9px 12px;text-align:right;font-variant-numeric:tabular-nums;'>{fmt_int(r['Fin'])}</td>"
            f"<td style='padding:9px 12px;text-align:right;color:{evol_color};font-variant-numeric:tabular-nums;'>{evol_text}</td>"
            f"<td style='padding:9px 12px;text-align:right;color:{evol_color};font-variant-numeric:tabular-nums;'>{pct_text}</td>"
            "</tr>"
        )

    table_html = (
        "<table style='width:100%;border-collapse:collapse;font-size:14px;'>"
        f"<thead><tr style='border-bottom:1px solid #E4E3DF;'>{header_cells}</tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table>"
    )
    st.markdown(table_html, unsafe_allow_html=True)


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

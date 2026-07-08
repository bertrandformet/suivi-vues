import datetime as dt

import pandas as pd
import streamlit as st

from src import auth, data as data_layer, style

st.title("Ajouter un relevé")
st.caption(
    "Un relevé = la valeur du compteur d'une URL à une date donnée. "
    "Entrée pour enregistrer, la sélection est conservée pour la saisie en série."
)

if not auth.is_editeur():
    st.error("Réservé aux éditeurs.")
    style.render_footer()
    st.stop()

urls = data_layer.enriched_tracked_urls()
if urls.empty:
    st.info("Aucune URL suivie pour l'instant. Ajoutez-en une dans « Contenus & URLs ».")
    style.render_footer()
    st.stop()

urls = urls.copy()
urls["choice"] = urls.apply(
    lambda r: f"{r['label']} — {r['platform_name']}" + (f" ({r['content_title']})" if r["content_title"] else ""),
    axis=1,
)

snapshots = data_layer.load_snapshots()


def last_snapshot_for(url_id):
    if snapshots.empty:
        return None
    rows = snapshots[snapshots["tracked_url_id"] == url_id].sort_values("recorded_at")
    return None if rows.empty else rows.iloc[-1]


choice = st.selectbox("URL suivie", urls["choice"])
selected_row = urls[urls["choice"] == choice].iloc[0]
last = last_snapshot_for(selected_row["id"])
default_views = int(last["view_count"]) if last is not None else 0

if st.session_state.get("_last_url_choice") != choice:
    st.session_state["add_snapshot_views"] = default_views
    st.session_state["add_snapshot_note"] = ""
    st.session_state["_last_url_choice"] = choice

if last is not None:
    st.caption(
        f"Dernier relevé : **{style.format_number(last['view_count'])}** le "
        f"{style.format_date_fr(last['recorded_at'])} ({style.SOURCE_LABELS.get(last['source'], last['source'])})"
    )

with st.form("add_snapshot_form", clear_on_submit=False):
    c1, c2 = st.columns(2)
    with c1:
        recorded_at = st.date_input("Date du relevé", value=dt.date.today())
    with c2:
        view_count = st.number_input("Nombre de vues", min_value=0, step=1, key="add_snapshot_views")
    note = st.text_input("Note (optionnel)", placeholder="Ex : correction après export erroné", key="add_snapshot_note")
    submitted = st.form_submit_button("Enregistrer le relevé", type="primary")

st.markdown(
    "<div style='display:flex;gap:10px;align-items:flex-start;background:#FDF6EC;"
    "border:1px solid #EBDCC3;border-radius:8px;padding:12px 16px;font-size:13.5px;color:#6B5426;margin-top:14px'>"
    "<span>Si une valeur existe déjà pour cette date, l'enregistrement devient automatiquement un "
    "<strong>ajustement</strong> — pas besoin de case à cocher.</span></div>",
    unsafe_allow_html=True,
)

if submitted:
    recorded_ts = pd.Timestamp(recorded_at)
    existing = (
        snapshots[(snapshots["tracked_url_id"] == selected_row["id"]) & (snapshots["recorded_at"] == recorded_ts)]
        if not snapshots.empty
        else pd.DataFrame()
    )
    is_adjustment = not existing.empty

    data_layer.add_snapshot(
        tracked_url_id=selected_row["id"],
        recorded_at=recorded_at,
        view_count=view_count,
        user=st.session_state["username"],
        source="adjustment" if is_adjustment else "manual",
        note=note,
        url_label=selected_row["label"],
    )
    kind = "Ajustement enregistré" if is_adjustment else "Relevé enregistré"
    st.toast(f"{kind} — {selected_row['label']}, {style.format_date_fr(recorded_at)}, {style.format_number(view_count)} vues")
    st.session_state["add_snapshot_views"] = 0
    st.session_state["add_snapshot_note"] = ""
    st.rerun()

style.render_footer()

import pandas as pd
import streamlit as st

from src import auth, data as data_layer, github_store, style
from src.collectors import COLLECTORS
from src.collection_runner import run_collection

dossier_id = st.session_state["current_dossier_id"]

st.title("Collecte automatique")
st.caption(
    "URLs YouTube et PeerTube uniquement (API). Une tâche planifiée lance aussi la collecte chaque lundi à 06:00."
)

if not auth.is_editeur():
    st.error("Réservé aux éditeurs.")
    style.render_footer()
    st.stop()

urls = data_layer.enriched_tracked_urls(dossier_id)
eligible = urls[urls["collection_method"].isin(COLLECTORS.keys())] if not urls.empty else urls

if eligible.empty:
    st.info("Aucune URL n'est configurée en collecte automatique pour l'instant.")
    style.render_footer()
    st.stop()

snapshots = data_layer.load_snapshots()
auto_snapshots = snapshots[snapshots["source"] == "auto"] if not snapshots.empty else snapshots
auto_snapshots = (
    auto_snapshots[auto_snapshots["tracked_url_id"].isin(eligible["id"])] if not auto_snapshots.empty else auto_snapshots
)


def last_auto(url_id):
    if auto_snapshots.empty:
        return None
    rows = auto_snapshots[auto_snapshots["tracked_url_id"] == url_id].sort_values("recorded_at")
    return None if rows.empty else rows.iloc[-1]


rows = []
for _, r in eligible.iterrows():
    last = last_auto(r["id"])
    if last is not None:
        derniere = f"{style.format_date_fr(last['recorded_at'])} · {style.format_number(last['view_count'])}"
        statut = "Collecté"
    else:
        derniere = "—"
        statut = "Jamais collecté"
    rows.append({
        "Libellé": r["label"], "Plateforme": r["platform_name"], "URL": style.shorten_url(r["url"]),
        "Dernière collecte": derniere, "Statut": statut,
    })

st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

last_run = auto_snapshots["entered_at"].max() if not auto_snapshots.empty else None
last_run_text = f"Dernière exécution : {style.format_datetime_fr(last_run)}" if last_run is not None else "Aucune exécution pour l'instant"

col1, col2 = st.columns([1, 3])
with col1:
    run_clicked = st.button("Lancer la collecte maintenant", type="primary")
with col2:
    st.caption(last_run_text)

if run_clicked:
    cfg = github_store.get_config()
    api_keys = {"youtube": st.secrets.get("youtube", {}).get("api_key")}
    with st.status("Collecte en cours…", expanded=True) as status:
        report = run_collection(cfg, api_keys, actor=st.session_state["username"], dossier_id=dossier_id)
        ok = [r for r in report if r["status"] == "ok"]
        errors = [r for r in report if r["status"] == "error"]
        status.update(label=f"{len(ok)} URL(s) collectée(s), {len(errors)} échec(s)", state="complete")

    if ok:
        st.dataframe(
            [{"URL": r["label"], "Méthode": r["method"], "Vues": r["value"]} for r in ok],
            use_container_width=True, hide_index=True,
        )
    if errors:
        st.warning(f"{len(errors)} erreur(s).")
        st.dataframe(
            [{"URL": r["label"], "Méthode": r["method"], "Erreur": r["error"]} for r in errors],
            use_container_width=True, hide_index=True,
        )

style.render_footer()

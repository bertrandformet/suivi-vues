import streamlit as st

from src import auth, data as data_layer, github_store, style
from src.collectors import COLLECTORS

dossier_id = st.session_state["current_dossier_id"]

st.title("Éléments suivis & URLs")
st.caption(
    "Un élément suivi rassemble ses URLs sur les différentes plateformes. "
    "Créez l'élément suivi d'abord, rattachez-lui ensuite ses URLs."
)

if not auth.is_editeur():
    st.error("Réservé aux éditeurs.")
    style.render_footer()
    st.stop()

tab_contents, tab_urls = st.tabs(["Créer un élément suivi", "Ajouter un item suivi"])

with tab_contents:
    with st.form("add_content_form", clear_on_submit=True):
        title = st.text_input("Titre de l'élément suivi")
        description = st.text_area("Description (optionnel)")
        submitted = st.form_submit_button("Créer l'élément suivi", type="primary")
    if submitted and title:
        try:
            data_layer.add_content(title, description, st.session_state["username"], dossier_id)
        except github_store.ConflictError:
            st.error("Une autre modification vient d'être enregistrée en même temps. Réessayez.")
        else:
            st.toast(f"Élément suivi « {title} » créé.")

with tab_urls:
    platforms = data_layer.load_platforms()
    all_contents = data_layer.load_contents()
    contents = all_contents[all_contents["dossier_id"] == dossier_id] if not all_contents.empty else all_contents

    platform_choice = st.selectbox("Plateforme", platforms["name"])
    platform_id = platforms.loc[platforms["name"] == platform_choice, "id"].iloc[0]
    collection_method = platform_id if platform_id in COLLECTORS else "manual"
    method_text = "Automatique — déduite de la plateforme" if collection_method != "manual" else "Manuel — aucune collecte automatique pour cette plateforme"
    st.caption(f"Méthode de collecte : {method_text}")

    with st.form("add_url_form", clear_on_submit=True):
        url = st.text_input("URL")
        label = st.text_input("Libellé", placeholder="Ex : Épisode 12 — YouTube")
        content_options = ["Aucun (URL indépendante)"] + contents["title"].tolist()
        content_choice = st.selectbox("Rattacher à un élément suivi", content_options)
        submitted = st.form_submit_button("Ajouter l'item", type="primary")

    if submitted and url and label:
        content_id = None
        if content_choice != "Aucun (URL indépendante)":
            content_id = contents.loc[contents["title"] == content_choice, "id"].iloc[0]
        try:
            data_layer.add_tracked_url(
                content_id, platform_id, url, label, st.session_state["username"], dossier_id, collection_method
            )
        except github_store.ConflictError:
            st.error("Une autre modification vient d'être enregistrée en même temps. Réessayez.")
        else:
            st.toast(f"Item « {label} » ajouté pour {platform_choice}.")

    st.subheader("Items suivis")
    st.caption("Le libellé se modifie directement dans le tableau (double-clic sur la cellule).")
    tracked = data_layer.enriched_tracked_urls(dossier_id)
    if not tracked.empty:
        display = tracked.copy()
        display["content_title"] = display["content_title"].fillna("—")
        display["url"] = display["url"].apply(style.shorten_url)
        display["collection_method"] = display["collection_method"].apply(
            lambda m: "Auto" if m in COLLECTORS else "Manuel"
        )
        display = display.sort_values(["content_title", "label"]).reset_index(drop=True)
        display_cols = ["id", "label", "platform_name", "content_title", "url", "collection_method", "added_by", "added_at"]
        display = display[[c for c in display_cols if c in display.columns]]
        edited = st.data_editor(
            display,
            use_container_width=True,
            hide_index=True,
            disabled=[c for c in display.columns if c != "label"],
            column_config={
                "id": None,
                "label": "Libellé",
                "platform_name": "Plateforme",
                "content_title": "Élément suivi",
                "url": "URL",
                "collection_method": "Méthode",
                "added_by": "Ajouté par",
                "added_at": "Ajouté le",
            },
            key="tracked_urls_editor",
        )
        changed = edited[edited["label"] != display["label"]]
        if not changed.empty:
            if st.button(f"Enregistrer {len(changed)} libellé(s) modifié(s)", type="primary"):
                try:
                    for _, row in changed.iterrows():
                        data_layer.update_tracked_url_label(row["id"], row["label"], st.session_state["username"])
                except github_store.ConflictError:
                    st.error("Une autre modification vient d'être enregistrée en même temps. Réessayez.")
                else:
                    st.toast(f"{len(changed)} libellé(s) mis à jour.")
                    st.rerun()

style.render_footer()

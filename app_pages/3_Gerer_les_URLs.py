import streamlit as st

from src import auth, data as data_layer, style
from src.collectors import COLLECTORS

st.title("Contenus & URLs suivies")
st.caption(
    "Un contenu regroupe ses URLs sur les différentes plateformes. "
    "Créez le contenu d'abord, rattachez-lui ensuite ses URLs."
)

if not auth.is_editeur():
    st.error("Réservé aux éditeurs.")
    style.render_footer()
    st.stop()

tab_contents, tab_urls = st.tabs(["Créer un contenu", "Ajouter une URL suivie"])

with tab_contents:
    with st.form("add_content_form", clear_on_submit=True):
        title = st.text_input("Titre du contenu")
        description = st.text_area("Description (optionnel)")
        submitted = st.form_submit_button("Créer le contenu", type="primary")
    if submitted and title:
        data_layer.add_content(title, description, st.session_state["username"])
        st.toast(f"Contenu « {title} » créé.")

with tab_urls:
    platforms = data_layer.load_platforms()
    contents = data_layer.load_contents()

    platform_choice = st.selectbox("Plateforme", platforms["name"])
    platform_id = platforms.loc[platforms["name"] == platform_choice, "id"].iloc[0]
    collection_method = platform_id if platform_id in COLLECTORS else "manual"
    method_text = "Automatique — déduite de la plateforme" if collection_method != "manual" else "Manuel — aucune collecte automatique pour cette plateforme"
    st.caption(f"Méthode de collecte : {method_text}")

    with st.form("add_url_form", clear_on_submit=True):
        url = st.text_input("URL")
        label = st.text_input("Libellé", placeholder="Ex : Épisode 12 — YouTube")
        content_options = ["Aucun (URL indépendante)"] + contents["title"].tolist()
        content_choice = st.selectbox("Rattacher à un contenu", content_options)
        submitted = st.form_submit_button("Ajouter l'URL", type="primary")

    if submitted and url and label:
        content_id = None
        if content_choice != "Aucun (URL indépendante)":
            content_id = contents.loc[contents["title"] == content_choice, "id"].iloc[0]
        data_layer.add_tracked_url(
            content_id, platform_id, url, label, st.session_state["username"], collection_method
        )
        st.toast(f"URL « {label} » ajoutée pour {platform_choice}.")

    st.subheader("URLs suivies")
    tracked = data_layer.enriched_tracked_urls()
    if not tracked.empty:
        display = tracked.copy()
        display["content_title"] = display["content_title"].fillna("—")
        display["url"] = display["url"].apply(style.shorten_url)
        display["collection_method"] = display["collection_method"].apply(
            lambda m: "Auto" if m in COLLECTORS else "Manuel"
        )
        display = display.sort_values(["content_title", "label"])
        display_cols = ["label", "platform_name", "content_title", "url", "collection_method", "added_by", "added_at"]
        st.dataframe(
            display[[c for c in display_cols if c in display.columns]],
            use_container_width=True,
            hide_index=True,
            column_config={
                "label": "Libellé",
                "platform_name": "Plateforme",
                "content_title": "Contenu",
                "url": "URL",
                "collection_method": "Méthode",
                "added_by": "Ajouté par",
                "added_at": "Ajouté le",
            },
        )

style.render_footer()

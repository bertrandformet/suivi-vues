import streamlit as st

from src import auth, data as data_layer, style

st.set_page_config(page_title="Suivi Vues", page_icon="📊", layout="wide")
style.inject()

result = auth.login()
if result is None:
    st.stop()

name, username, role = result

dossiers = data_layer.load_dossiers()


def _create_dossier_form(key_suffix: str):
    with st.form(f"create_dossier_form_{key_suffix}", clear_on_submit=True):
        new_name = st.text_input("Nom du dossier", placeholder="Ex : IA")
        new_desc = st.text_area("Description (optionnel)")
        if st.form_submit_button("Créer", type="primary") and new_name:
            new_dossier_id = data_layer.add_dossier(new_name, new_desc, username)
            st.session_state["current_dossier_id"] = new_dossier_id
            st.rerun()


with st.sidebar:
    if dossiers.empty:
        if role == "editeur":
            st.info("Aucun dossier pour l'instant. Créez-en un pour commencer.")
            with st.popover("+ Créer un dossier"):
                _create_dossier_form("first")
        else:
            st.info("Aucun dossier disponible pour l'instant.")
        st.stop()

    dossier_names = dossiers["name"].tolist()
    current_id = st.session_state.get("current_dossier_id")
    default_index = 0
    if current_id in dossiers["id"].values:
        default_index = int(dossiers.index[dossiers["id"] == current_id][0])
    selected_name = st.selectbox("Dossier", dossier_names, index=default_index)
    st.session_state["current_dossier_id"] = dossiers.loc[dossiers["name"] == selected_name, "id"].iloc[0]

    if role == "editeur":
        with st.popover("+ Nouveau dossier"):
            _create_dossier_form("new")

lecture_pages = [
    st.Page("app_pages/1_Tableau_de_bord.py", title="Tableau de bord", default=True),
]
edition_pages = [
    st.Page("app_pages/2_Ajouter_une_vue.py", title="Ajouter un relevé"),
    st.Page("app_pages/3_Gerer_les_URLs.py", title="Regroupements & URLs"),
    st.Page("app_pages/4_Importer_un_fichier.py", title="Importer des relevés"),
    st.Page("app_pages/5_Collecte_automatique.py", title="Collecte automatique"),
]

pages = lecture_pages + (edition_pages if role == "editeur" else [])
navigation = st.navigation(pages)
navigation.run()

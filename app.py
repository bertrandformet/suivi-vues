import streamlit as st

from src import auth, style

st.set_page_config(page_title="Suivi Vues", page_icon="📊", layout="wide")
style.inject()

result = auth.login()
if result is None:
    st.stop()

name, username, role = result

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

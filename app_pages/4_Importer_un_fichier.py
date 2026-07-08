import pandas as pd
import streamlit as st

from src import auth, data as data_layer

st.title("Importer des relevés")
st.caption("Fichier CSV ou Excel exporté depuis une plateforme. Les lignes sont vérifiées avant d'être enregistrées.")

if not auth.is_editeur():
    st.error("Réservé aux éditeurs.")
    st.stop()

with st.expander("Format attendu"):
    st.markdown(
        "| Colonne | Description |\n"
        "|---|---|\n"
        "| `date` | AAAA-MM-JJ — ex : 2026-01-19 |\n"
        "| `url` | doit correspondre à une URL suivie existante (ou son libellé) |\n"
        "| `vues` | nombre entier ≥ 0 |\n"
        "| `note` | optionnelle |\n"
    )
    template = "date,url,vues,note\n2026-01-19,https://exemple.org/episode-12,510,\n"
    st.download_button("Télécharger le modèle CSV", template, file_name="modele_relevés.csv", mime="text/csv")

urls = data_layer.enriched_tracked_urls()
if urls.empty:
    st.info("Aucune URL suivie pour l'instant. Ajoutez-en une dans « Contenus & URLs » avant d'importer.")
    st.stop()

uploaded = st.file_uploader("Déposez votre fichier ici", type=["csv", "xlsx"])
if not uploaded:
    st.stop()

if uploaded.name.endswith(".xlsx"):
    raw = pd.read_excel(uploaded)
else:
    raw = pd.read_csv(uploaded)

st.subheader("Aperçu")
st.dataframe(raw.head(5), use_container_width=True, hide_index=True)

mode = st.radio(
    "Ce fichier concerne...",
    ["une seule URL suivie", "plusieurs URLs (une colonne identifie l'URL/le libellé)"],
)

columns = raw.columns.tolist()
date_col = st.selectbox("Colonne date", columns)
views_col = st.selectbox("Colonne nombre de vues", columns)

url_col = None
single_url_choice = None
urls = urls.copy()
urls["choice"] = urls.apply(
    lambda r: f"{r['label']} — {r['platform_name']}" + (f" ({r['content_title']})" if r["content_title"] else ""),
    axis=1,
)

if mode == "une seule URL suivie":
    single_url_choice = st.selectbox("URL suivie concernée", urls["choice"])
else:
    url_col = st.selectbox("Colonne identifiant l'URL (correspond à l'URL ou au libellé saisi)", columns)

if st.button("Vérifier le fichier"):
    working = raw[[date_col, views_col] + ([url_col] if url_col else [])].copy()
    working.columns = ["recorded_at", "view_count"] + (["identifier"] if url_col else [])

    if mode != "une seule URL suivie":
        lookup = pd.concat([
            urls[["id", "url"]].rename(columns={"url": "identifier"}),
            urls[["id", "label"]].rename(columns={"label": "identifier"}),
        ])
        working = working.merge(lookup, on="identifier", how="left")
    else:
        row = urls[urls["choice"] == single_url_choice].iloc[0]
        working["id"] = row["id"]

    working["_parsed_date"] = pd.to_datetime(working["recorded_at"], errors="coerce")
    working["_parsed_views"] = pd.to_numeric(working["view_count"], errors="coerce")

    def error_reason(r):
        if pd.isna(r["id"]):
            return "URL non reconnue"
        if pd.isna(r["_parsed_date"]):
            return "Date invalide"
        if pd.isna(r["_parsed_views"]) or r["_parsed_views"] < 0:
            return "Nombre de vues invalide"
        return None

    working["_error"] = working.apply(error_reason, axis=1)
    valid = working[working["_error"].isna()].copy()
    errors = working[working["_error"].notna()].copy()

    st.markdown(f"**{len(valid)} ligne(s) valide(s)**, {len(errors)} erreur(s)")
    if not errors.empty:
        st.dataframe(
            errors[["recorded_at", "view_count", "_error"]].rename(columns={"_error": "Motif"}),
            use_container_width=True,
            hide_index=True,
        )

    valid["recorded_at"] = valid["_parsed_date"].dt.date
    valid["view_count"] = valid["_parsed_views"].astype(int)
    st.session_state["import_preview"] = valid[["id", "recorded_at", "view_count"]]

if "import_preview" in st.session_state:
    preview = st.session_state["import_preview"]
    if not preview.empty and st.button("Confirmer l'import", type="primary"):
        label_by_id = urls.set_index("id")["label"].to_dict()
        for _, r in preview.iterrows():
            data_layer.add_snapshot(
                tracked_url_id=r["id"],
                recorded_at=r["recorded_at"],
                view_count=r["view_count"],
                user=st.session_state["username"],
                source="import",
                note=f"Import : {uploaded.name}",
                url_label=label_by_id.get(r["id"], ""),
            )
        st.toast(f"{len(preview)} relevé(s) importé(s).")
        del st.session_state["import_preview"]

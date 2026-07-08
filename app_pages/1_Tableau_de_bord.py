import pandas as pd
import streamlit as st

from src import auth, charts, data as data_layer, style

st.title("Évolution des vues")

df = charts.build_view_dataset()

if df.empty:
    st.info("Aucun relevé de vues pour l'instant. Ajoutez une URL suivie et un premier relevé.")
    style.render_footer()
    st.stop()

n_contents = data_layer.load_contents().shape[0]
n_urls = data_layer.load_tracked_urls().shape[0]
auto_snapshots = df[df["source"] == "auto"]
last_collection = pd.to_datetime(auto_snapshots["entered_at"]).max() if not auto_snapshots.empty else None
context_bits = [f"{n_contents} contenu(s) suivi(s)", f"{n_urls} URL(s)"]
if last_collection is not None:
    context_bits.append(f"dernière collecte le {style.format_date_fr(last_collection)}")
st.caption(" · ".join(context_bits))

col1, col2, col3 = st.columns(3)
with col1:
    contents = ["Tous"] + sorted(df["content_title"].dropna().unique().tolist())
    content_filter = st.selectbox("Contenu", contents)
with col2:
    platforms = ["Toutes"] + sorted(df["platform_name"].dropna().unique().tolist())
    platform_filter = st.selectbox("Plateforme", platforms)
with col3:
    group_by = st.selectbox("Une courbe par", ["label", "platform_name"], format_func=lambda x: "URL suivie" if x == "label" else "Plateforme")

filtered = df.copy()
if content_filter != "Tous":
    filtered = filtered[filtered["content_title"] == content_filter]
if platform_filter != "Toutes":
    filtered = filtered[filtered["platform_name"] == platform_filter]

fig = charts.evolution_chart(filtered, group_by=group_by)
if fig:
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Aucune donnée pour ces filtres.")

st.subheader("Dernier relevé par plateforme")
st.caption("La couleur indique le contenu, pas la plateforme.")
bar_fig = charts.latest_by_platform_chart(filtered)
if bar_fig:
    st.plotly_chart(bar_fig, use_container_width=True)


@st.dialog("Confirmer la suppression")
def confirm_delete_snapshot(snapshot_id, label):
    st.write("Supprimer définitivement ce relevé ?")
    st.caption(label)
    st.caption(
        "Cette action est irréversible dans l'application "
        "(l'historique reste consultable dans les commits GitHub du dépôt)."
    )
    c1, c2 = st.columns(2)
    if c1.button("Annuler", use_container_width=True):
        st.rerun()
    if c2.button("Supprimer définitivement", type="primary", use_container_width=True):
        data_layer.delete_snapshot(snapshot_id, st.session_state["username"])
        st.toast("Relevé supprimé.")
        st.rerun()


with st.expander("Journal des relevés (audit)"):
    display = filtered.copy()
    display["source"] = display["source"].map(style.SOURCE_LABELS).fillna(display["source"]).str.capitalize()
    display_cols = ["recorded_at", "label", "platform_name", "content_title", "view_count", "source", "note", "entered_by", "entered_at"]
    st.dataframe(
        display[display_cols].sort_values("recorded_at", ascending=False),
        use_container_width=True,
        hide_index=True,
        column_config={
            "recorded_at": "Date",
            "label": "URL",
            "platform_name": "Plateforme",
            "content_title": "Contenu",
            "view_count": st.column_config.NumberColumn("Vues", format="%d"),
            "source": "Source",
            "note": "Note",
            "entered_by": "Saisi par",
            "entered_at": "Saisi le",
        },
    )

    if auth.is_editeur() and not filtered.empty:
        st.divider()
        ordered = filtered.sort_values("recorded_at", ascending=False)
        option_labels = {
            row["id_x"]: (
                f"{style.format_date_fr(row['recorded_at'])} — {row['label']} — "
                f"{style.format_number(row['view_count'])} vues "
                f"({style.SOURCE_LABELS.get(row['source'], row['source'])})"
            )
            for _, row in ordered.iterrows()
        }
        col_a, col_b = st.columns([3, 1])
        with col_a:
            to_delete = st.selectbox(
                "Supprimer un relevé erroné",
                list(option_labels.keys()),
                format_func=lambda k: option_labels[k],
            )
        with col_b:
            st.write("")
            st.write("")
            if st.button("Supprimer", use_container_width=True):
                confirm_delete_snapshot(to_delete, option_labels[to_delete])

style.render_footer()

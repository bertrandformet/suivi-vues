import pandas as pd
import streamlit as st

from src import charts, data as data_layer, style

st.title("Évolution des vues")

df = charts.build_view_dataset()

if df.empty:
    st.info("Aucun relevé de vues pour l'instant. Ajoutez une URL suivie et un premier relevé.")
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

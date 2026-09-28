import streamlit as st

from src import auth, charts, data as data_layer, github_store, style

dossier_id = st.session_state["current_dossier_id"]

st.title("Tableau de suivi")

df = charts.build_view_dataset(dossier_id)

if df.empty:
    st.info("Aucun relevé pour l'instant. Ajoutez une URL suivie et un premier relevé.")
    style.render_footer()
    st.stop()

contents = data_layer.load_contents()
contents_in_dossier = contents[contents["dossier_id"] == dossier_id] if not contents.empty else contents
urls = data_layer.load_tracked_urls()
urls_in_dossier = urls[urls["dossier_id"] == dossier_id] if not urls.empty else urls

n_contents = contents_in_dossier.shape[0]
n_urls = urls_in_dossier.shape[0]
auto_snapshots = df[df["source"] == "auto"]
last_collection = auto_snapshots["entered_at"].max() if not auto_snapshots.empty else None
context_bits = [f"{n_contents} élément(s) suivi(s)", f"{n_urls} URL(s)"]
if last_collection is not None:
    context_bits.append(f"dernière collecte le {style.format_date_fr(style.to_local(last_collection))}")
st.caption(" · ".join(context_bits))

col1, col2 = st.columns(2)
with col1:
    platforms = ["Toutes"] + sorted(df["platform_name"].dropna().unique().tolist())
    platform_filter = st.selectbox("Plateforme", platforms)
with col2:
    group_by = st.selectbox(
        "Une courbe par", ["platform_name", "label"],
        format_func=lambda x: "URL suivie (détail)" if x == "label" else "Plateforme (cumulé)",
    )

filtered = df.copy()
if platform_filter != "Toutes":
    filtered = filtered[filtered["platform_name"] == platform_filter]

if group_by == "platform_name":
    totals = charts.platform_and_group_totals_dataset(filtered)
    fig = charts.platform_totals_chart(totals)
else:
    fig = charts.evolution_chart(filtered, group_by=group_by)
if fig:
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": True, "displaylogo": False})
else:
    st.info("Aucune donnée pour ces filtres.")

st.subheader("Dernier relevé par plateforme")
st.caption("Chaque barre est divisée par élément suivi : survolez un segment pour voir lequel.")
bar_fig = charts.latest_by_platform_chart(filtered)
if bar_fig:
    st.plotly_chart(bar_fig, use_container_width=True, config={"displayModeBar": True, "displaylogo": False})

st.subheader("Données cumulées")
st.caption("Additionne les totaux de plusieurs plateformes au choix (ex : YouTube + PeerTube + Canotech).")
available_platforms = sorted(df["platform_name"].dropna().unique().tolist())
calc_platforms = st.multiselect(
    "Plateformes à additionner", available_platforms, placeholder="Choisir des plateformes",
)
if calc_platforms:
    calc_df = df[df["platform_name"].isin(calc_platforms)]
    calc_units = calc_df["platform_unit"].dropna().unique().tolist()
    if len(calc_units) > 1:
        st.warning(
            f"Unités différentes mélangées ({', '.join(calc_units)}) : "
            "le total combiné n'a pas de sens direct, à interpréter avec prudence."
        )
    calc_totals = charts.combined_totals_dataset(calc_df)
    if calc_totals.empty:
        st.info("Aucune donnée pour cette combinaison.")
    else:
        latest_total = calc_totals.sort_values("recorded_at").iloc[-1]["total"]
        unit_label = calc_units[0] if len(calc_units) == 1 else ""
        st.metric(f"Total combiné — {' + '.join(calc_platforms)}", f"{style.format_number(latest_total)} {unit_label}")
        calc_fig = charts.combined_total_chart(calc_totals)
        if calc_fig:
            st.plotly_chart(calc_fig, use_container_width=True, config={"displayModeBar": True, "displaylogo": False})

st.subheader("Comparateur de périodes")
st.caption(
    "Valeur au début et à la fin d'une période, avec évolution en % — "
    "plateformes et cumuls thématiques inclus."
)
all_totals = charts.platform_and_group_totals_dataset(df)
if all_totals.empty:
    st.info("Pas assez de données pour comparer des périodes.")
else:
    min_date = df["recorded_at"].min().date()
    max_date = df["recorded_at"].max().date()
    pc1, pc2 = st.columns(2)
    with pc1:
        period_start = st.date_input("Début de période", value=min_date, min_value=min_date, max_value=max_date)
    with pc2:
        period_end = st.date_input("Fin de période", value=max_date, min_value=min_date, max_value=max_date)

    comparison = charts.period_comparison(all_totals, period_start, period_end)
    if comparison.empty:
        st.info("Aucune donnée sur cette période.")
    else:
        st.dataframe(
            comparison,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Début": st.column_config.NumberColumn(format="%d"),
                "Fin": st.column_config.NumberColumn(format="%d"),
                "Évolution": st.column_config.NumberColumn(format="%+d"),
                "Évolution (%)": st.column_config.NumberColumn(format="%+.0f%%"),
            },
        )


@st.dialog("Confirmer la suppression")
def confirm_delete_snapshot(snapshot_id, label, is_current):
    st.write("Supprimer définitivement ce relevé ?")
    st.caption(label)
    if not is_current:
        st.warning(
            "Ce relevé a déjà été remplacé par un ajustement plus récent pour la même date : "
            "il n'apparaît pas sur le graphique. Le supprimer ne changera donc rien à l'affichage."
        )
    st.caption(
        "Cette action est irréversible dans l'application "
        "(l'historique reste consultable dans les commits GitHub du dépôt)."
    )
    c1, c2 = st.columns(2)
    if c1.button("Annuler", use_container_width=True):
        st.rerun()
    if c2.button("Supprimer définitivement", type="primary", use_container_width=True):
        try:
            data_layer.delete_snapshot(snapshot_id, st.session_state["username"])
        except github_store.ConflictError:
            st.error("Une autre modification vient d'être enregistrée en même temps. Réessayez.")
        else:
            st.toast("Relevé supprimé.")
            st.rerun()


journal_df = charts.all_snapshots_dataset(dossier_id)
if platform_filter != "Toutes":
    journal_df = journal_df[journal_df["platform_name"] == platform_filter]

current_ids = set(df["id_snapshot"])
journal_df = journal_df.copy()
journal_df["is_current"] = journal_df["id_snapshot"].isin(current_ids)

st.subheader("Journal des relevés")
with st.expander("Afficher le détail"):
    st.caption(
        "Historique complet, y compris les relevés remplacés par un ajustement ultérieur. "
        "« Remplacé » signifie que ce relevé n'apparaît plus sur les graphiques ci-dessus, "
        "une saisie plus récente existant pour la même date."
    )
    display = journal_df.copy()
    display["source"] = display["source"].map(style.SOURCE_LABELS).fillna(display["source"]).str.capitalize()
    display["statut"] = display["is_current"].map({True: "Actuel", False: "Remplacé"})
    display["entered_at"] = display["entered_at"].apply(style.to_local)
    display_cols = ["recorded_at", "label", "platform_name", "content_title", "view_count", "statut", "source", "note", "entered_by", "entered_at"]
    st.dataframe(
        display[display_cols].sort_values("recorded_at", ascending=False),
        use_container_width=True,
        hide_index=True,
        column_config={
            "recorded_at": st.column_config.DateColumn("Date", format="D MMM YYYY"),
            "label": "URL",
            "platform_name": "Plateforme",
            "content_title": "Élément suivi",
            "view_count": st.column_config.NumberColumn("Valeur", format="%d"),
            "statut": "Statut",
            "source": "Source",
            "note": "Note",
            "entered_by": "Saisi par",
            "entered_at": st.column_config.DatetimeColumn("Saisi le", format="D MMM YYYY, HH:mm"),
        },
    )

    if auth.is_editeur() and not journal_df.empty:
        st.divider()
        ordered = journal_df.sort_values("recorded_at", ascending=False)
        option_labels = {
            row["id_snapshot"]: (
                f"{style.format_date_fr(row['recorded_at'])} — {row['label']} — "
                f"{style.format_number(row['view_count'])} {row.get('platform_unit', 'vues')} "
                f"({style.SOURCE_LABELS.get(row['source'], row['source'])})"
                + ("" if row["is_current"] else " — remplacé, absent du graphique")
            )
            for _, row in ordered.iterrows()
        }
        current_by_id = dict(zip(journal_df["id_snapshot"], journal_df["is_current"]))
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
                confirm_delete_snapshot(to_delete, option_labels[to_delete], current_by_id[to_delete])

style.render_footer()

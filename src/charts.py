"""Construction des graphiques Plotly pour le tableau de bord.

La couleur code toujours le contenu (jamais la plateforme) : une couleur
stable par contenu, déclinée sur toutes ses URLs, pour rester lisible à
mesure que le nombre de plateformes suivies augmente.
"""

from __future__ import annotations

import pandas as pd
import plotly.express as px

from src import data as data_layer
from src import palette
from src import style


def _add_date_label(df: pd.DataFrame) -> pd.DataFrame:
    """Ajoute une colonne `recorded_at_fr` (date en français, pour l'info-bulle
    uniquement). L'axe X reste un vrai axe temporel continu (`recorded_at`) :
    l'espacement doit être proportionnel au temps réel écoulé entre deux
    relevés, sinon la pente de la courbe ne reflète plus le vrai rythme
    d'évolution (ex. 4 relevés rapprochés en octobre puis un saut de plusieurs
    mois ne doivent pas occuper le même espace visuel)."""
    df["recorded_at_fr"] = df["recorded_at"].apply(style.format_date_fr)
    return df


def _french_date_axis(fig):
    """Un tick par mois (format mm/aaaa, numérique — Plotly.js n'a pas de
    locale FR embarquée pour les noms de mois). L'axe reste temporel continu
    (proportionnel au temps réel) ; seuls les ticks affichés sont mensuels."""
    fig.update_xaxes(tickformat="%m/%Y", dtick="M1", tickangle=-45)


def _enrich_snapshots(snapshots: pd.DataFrame, dossier_id: str | None = None) -> pd.DataFrame:
    """Jointe des relevés avec le libellé/plateforme/contenu/dossier de leur URL suivie.

    Suffixes explicites (plutôt que de laisser pandas déduire `id_x`/`id_y`) :
    la colonne `id` du relevé devient `id_snapshot`, celle de l'URL `id_url`.
    Filtre optionnellement sur `dossier_id` (un relevé hérite du dossier de son URL).
    """
    if snapshots.empty:
        return snapshots
    urls = data_layer.enriched_tracked_urls()
    merged = snapshots.merge(
        urls[[
            "id", "label", "url", "platform_name", "platform_unit", "platform_group",
            "content_title", "content_id", "dossier_id",
        ]],
        left_on="tracked_url_id",
        right_on="id",
        how="left",
        suffixes=("_snapshot", "_url"),
    )
    if dossier_id is not None:
        merged = merged[merged["dossier_id"] == dossier_id]
        if merged.empty:
            return merged
    merged["content_label"] = merged["content_title"].fillna(merged["label"])
    merged["color_key"] = merged.apply(palette.color_key, axis=1)
    return merged


def build_view_dataset(dossier_id: str | None = None) -> pd.DataFrame:
    """Relevés dédupliqués (dernière saisie par URL/date) enrichis avec plateforme et contenu.

    Destiné aux graphiques : une seule valeur par (URL, date), utile pour tracer
    une courbe cohérente. Pour l'historique complet (y compris les valeurs
    remplacées par un ajustement), voir `all_snapshots_dataset`.
    """
    snapshots = data_layer.latest_per_url_and_date(data_layer.load_snapshots())
    if snapshots.empty:
        return snapshots
    return _enrich_snapshots(snapshots, dossier_id=dossier_id).sort_values("recorded_at")


def all_snapshots_dataset(dossier_id: str | None = None) -> pd.DataFrame:
    """Tous les relevés enrichis, sans déduplication — pour le journal d'audit.

    Contrairement à `build_view_dataset`, conserve les entrées remplacées par un
    ajustement ultérieur, pour que le journal reflète réellement qui a saisi quoi.
    """
    snapshots = data_layer.load_snapshots()
    if snapshots.empty:
        return snapshots
    return _enrich_snapshots(snapshots, dossier_id=dossier_id).sort_values("recorded_at")


def evolution_chart(df: pd.DataFrame, group_by: str = "label"):
    """Courbe d'évolution, une ligne par `group_by` (label ou platform_name), colorée
    par contenu, avec un marqueur à chaque relevé, une légende et une info-bulle
    (contenu, date, valeur, unité) au survol."""
    if df.empty:
        return None

    df = _add_date_label(df.copy())

    color_map = palette.build_color_map(df.sort_values("recorded_at")["color_key"])
    group_color = df.groupby(group_by)["color_key"].first().map(color_map).to_dict()

    fig = px.line(
        df,
        x="recorded_at",
        y="view_count",
        color=group_by,
        color_discrete_map=group_color,
        markers=True,
        custom_data=["content_label", "platform_unit", "recorded_at_fr"],
    )
    fig.update_traces(
        mode="lines+markers",
        marker=dict(size=6),
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>%{customdata[2]}<br>"
            "%{y:,.0f} %{customdata[1]}<extra>%{fullData.name}</extra>"
        ),
    )
    fig.update_layout(
        showlegend=True,
        legend_title_text="",
        xaxis_title="",
        yaxis_title="",
        hovermode="closest",
    )
    fig.update_xaxes(showgrid=False)
    _french_date_axis(fig)
    fig.update_yaxes(showgrid=True, gridcolor="#EDEEF0", zeroline=False, rangemode="tozero")
    return fig


def _pivot_ffill(df: pd.DataFrame) -> pd.DataFrame:
    """Pivote les relevés (une colonne par élément suivi) et reporte la dernière
    valeur connue à chaque date où au moins un élément a un nouveau relevé —
    sans ça, une somme sur plusieurs éléments baisserait artificiellement dès
    qu'un seul d'entre eux n'a pas de relevé ce jour-là."""
    pivot = df.pivot_table(index="recorded_at", columns="tracked_url_id", values="view_count", aggfunc="last")
    return pivot.sort_index().ffill()


def _drop_flat_runs(totals: pd.Series) -> pd.Series:
    """Ne garde que les points où la valeur change vraiment (premier point de
    chaque palier) — sinon le report de la dernière valeur connue entre deux
    relevés réels (nécessaire pour que la somme reste correcte) dessine des
    segments plats parasites au lieu de relier directement les vrais relevés."""
    totals = totals.dropna()
    if totals.empty:
        return totals
    changed = totals.diff().fillna(1) != 0
    return totals[changed]


def platform_totals_dataset(df: pd.DataFrame) -> pd.DataFrame:
    """Somme, par plateforme et par date, de la dernière valeur connue de chaque
    élément suivi de cette plateforme."""
    if df.empty:
        return df
    pivot = _pivot_ffill(df)
    url_info = df.drop_duplicates("tracked_url_id").set_index("tracked_url_id")[["platform_name", "platform_unit"]]

    rows = []
    for platform_name, group in url_info.groupby("platform_name"):
        unit = group["platform_unit"].iloc[0]
        totals = pivot[group.index].sum(axis=1, min_count=1)
        for recorded_at, total in _drop_flat_runs(totals).items():
            rows.append({
                "recorded_at": recorded_at, "platform_name": platform_name,
                "platform_unit": unit, "total": total, "detail": "",
            })
    return pd.DataFrame(rows)


GROUP_LABEL_PREFIX = "Cumul — "


def group_totals_dataset(df: pd.DataFrame) -> pd.DataFrame:
    """Somme, par groupe thématique de plateformes (colonne `group` de
    `platforms.csv`) et par date, de la dernière valeur connue de chaque élément
    suivi. Les plateformes sans groupe assigné n'apparaissent pas ici.

    Mêmes colonnes que `platform_totals_dataset` (`platform_name` porte ici le
    nom du groupe, préfixé pour se distinguer dans la légende) pour pouvoir
    concaténer les deux et les tracer ensemble sur le même graphique, à côté
    des plateformes individuelles. `detail` liste les plateformes cumulées."""
    if df.empty:
        return df
    df = df[df["platform_group"].fillna("") != ""]
    if df.empty:
        return df
    pivot = _pivot_ffill(df)
    url_info = df.drop_duplicates("tracked_url_id").set_index("tracked_url_id")[
        ["platform_group", "platform_unit", "platform_name"]
    ]

    rows = []
    for group_name, group in url_info.groupby("platform_group"):
        units = group["platform_unit"].unique().tolist()
        unit = units[0] if len(units) == 1 else "/".join(units)
        detail = " + ".join(sorted(group["platform_name"].unique())) + "<br>"
        totals = pivot[group.index].sum(axis=1, min_count=1)
        for recorded_at, total in _drop_flat_runs(totals).items():
            rows.append({
                "recorded_at": recorded_at, "platform_name": GROUP_LABEL_PREFIX + group_name,
                "platform_unit": unit, "total": total, "detail": detail,
            })
    return pd.DataFrame(rows)


def platform_and_group_totals_dataset(df: pd.DataFrame) -> pd.DataFrame:
    """Totaux par plateforme, augmentés des totaux par groupe thématique
    (colonne `group` de `platforms.csv`) tracés sur le même graphique."""
    platform_rows = platform_totals_dataset(df)
    group_rows = group_totals_dataset(df)
    if group_rows.empty:
        return platform_rows
    if platform_rows.empty:
        return group_rows
    return pd.concat([platform_rows, group_rows], ignore_index=True)


def period_comparison(totals: pd.DataFrame, start_date, end_date) -> pd.DataFrame:
    """Pour chaque plateforme/groupe thématique (sortie de
    `platform_and_group_totals_dataset`), la valeur au début et à la fin d'une
    période choisie (dernière valeur connue à ou avant chaque date — même
    logique de report que les graphiques), plus l'évolution absolue et en %."""
    if totals.empty:
        return totals
    start_ts = pd.Timestamp(start_date)
    end_ts = pd.Timestamp(end_date)

    rows = []
    for name, group in totals.groupby("platform_name"):
        group = group.sort_values("recorded_at")
        unit = group["platform_unit"].iloc[0]
        before_start = group[group["recorded_at"] <= start_ts]
        before_end = group[group["recorded_at"] <= end_ts]
        val_start = before_start["total"].iloc[-1] if not before_start.empty else None
        val_end = before_end["total"].iloc[-1] if not before_end.empty else None
        if val_start is None and val_end is None:
            continue
        delta = (val_end - val_start) if (val_start is not None and val_end is not None) else None
        pct = (delta / val_start * 100) if (delta is not None and val_start) else None
        rows.append({
            "Plateforme": name, "Unité": unit,
            "Début": val_start, "Fin": val_end,
            "Évolution": delta, "Évolution (%)": pct,
        })
    return pd.DataFrame(rows).sort_values("Plateforme")


def combined_totals_dataset(df: pd.DataFrame) -> pd.DataFrame:
    """Somme combinée de tous les éléments suivis présents dans `df` (toutes
    plateformes confondues), pour un total "à la carte" choisi par l'utilisateur
    plutôt qu'un découpage fixe par plateforme."""
    if df.empty:
        return df
    pivot = _pivot_ffill(df)
    totals = _drop_flat_runs(pivot.sum(axis=1, min_count=1))
    return pd.DataFrame({"recorded_at": totals.index, "total": totals.values})


def combined_total_chart(df: pd.DataFrame):
    """Courbe d'évolution d'un total combiné (calculateur multi-plateformes)."""
    if df.empty:
        return None
    df = _add_date_label(df.copy())

    fig = px.line(df, x="recorded_at", y="total", markers=True, custom_data=["recorded_at_fr"])
    fig.update_traces(
        mode="lines+markers",
        marker=dict(size=6, color="#33618F"),
        line=dict(color="#33618F"),
        hovertemplate="%{customdata[0]}<br>%{y:,.0f}<extra></extra>",
    )
    fig.update_layout(xaxis_title="", yaxis_title="", hovermode="closest")
    fig.update_xaxes(showgrid=False)
    _french_date_axis(fig)
    fig.update_yaxes(showgrid=True, gridcolor="#EDEEF0", zeroline=False, rangemode="tozero")
    return fig


def platform_totals_chart(df: pd.DataFrame):
    """Courbe d'évolution des totaux par plateforme (somme de tous les éléments suivis)."""
    if df.empty:
        return None

    df = _add_date_label(df.copy())

    fig = px.line(
        df, x="recorded_at", y="total", color="platform_name",
        markers=True, custom_data=["platform_unit", "detail", "recorded_at_fr"],
    )
    fig.update_traces(
        mode="lines+markers",
        marker=dict(size=6),
        hovertemplate=(
            "<b>%{fullData.name}</b><br>%{customdata[1]}"
            "%{customdata[2]}<br>%{y:,.0f} %{customdata[0]}<extra></extra>"
        ),
    )
    fig.update_layout(showlegend=True, legend_title_text="", xaxis_title="", yaxis_title="", hovermode="closest")
    fig.update_xaxes(showgrid=False)
    _french_date_axis(fig)
    fig.update_yaxes(showgrid=True, gridcolor="#EDEEF0", zeroline=False, rangemode="tozero")
    return fig


def latest_by_platform_chart(df: pd.DataFrame):
    """Barres horizontales : dernier relevé connu par plateforme, colorées par contenu,
    avec le total de la plateforme annoté en bout de barre."""
    if df.empty:
        return None
    latest = df.sort_values("recorded_at").drop_duplicates(subset=["tracked_url_id"], keep="last")
    color_map = palette.build_color_map(latest["color_key"])
    order = latest.groupby("platform_name")["view_count"].sum().sort_values().index.tolist()

    fig = px.bar(
        latest,
        x="view_count",
        y="platform_name",
        category_orders={"platform_name": order},
        color="color_key",
        color_discrete_map=color_map,
        orientation="h",
        custom_data=["content_label", "view_count", "platform_unit"],
    )
    fig.update_traces(
        hovertemplate="<b>%{customdata[0]}</b><br>%{customdata[1]:,.0f} %{customdata[2]}<extra></extra>",
    )
    fig.update_layout(showlegend=False, xaxis_title="", yaxis_title="")
    fig.update_xaxes(rangemode="tozero")

    totals = latest.groupby("platform_name").agg(total=("view_count", "sum"), unit=("platform_unit", "first"))
    for platform_name, row in totals.iterrows():
        fig.add_annotation(
            x=row["total"], y=platform_name,
            text=f"<b>{style.format_number(row['total'])} {row['unit']}</b>",
            showarrow=False, xanchor="left", xshift=8, align="left",
            font=dict(size=12, color="#2B2E33"),
        )
    return fig

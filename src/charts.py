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


def _french_date_ticks(fig, dates):
    """Force les ticks de l'axe X aux seules dates de relevé réelles, formatées en
    français — Plotly.js n'a pas de locale FR embarquée, on formate donc nous-mêmes
    plutôt que de laisser afficher des mois en anglais."""
    ticks = sorted(pd.Timestamp(d) for d in pd.Series(dates).dropna().unique())
    fig.update_xaxes(
        tickvals=ticks,
        ticktext=[style.format_date_fr(d) for d in ticks],
        tickangle=-45,
    )


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
        urls[["id", "label", "url", "platform_name", "platform_unit", "content_title", "content_id", "dossier_id"]],
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

    df = df.copy()
    df["recorded_at_fr"] = df["recorded_at"].apply(style.format_date_fr)

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
    fig.update_yaxes(showgrid=True, gridcolor="#EDEEF0", zeroline=False, rangemode="tozero")
    _french_date_ticks(fig, df["recorded_at"])
    return fig


def platform_totals_dataset(df: pd.DataFrame) -> pd.DataFrame:
    """Somme, par plateforme et par date, de la dernière valeur connue de chaque
    élément suivi (report de la dernière valeur pour les éléments non mis à jour
    à cette date précise — sinon la somme baisserait artificiellement)."""
    if df.empty:
        return df
    pivot = df.pivot_table(index="recorded_at", columns="tracked_url_id", values="view_count", aggfunc="last")
    pivot = pivot.sort_index().ffill()

    url_info = df.drop_duplicates("tracked_url_id").set_index("tracked_url_id")[["platform_name", "platform_unit"]]

    rows = []
    for platform_name, group in url_info.groupby("platform_name"):
        unit = group["platform_unit"].iloc[0]
        totals = pivot[group.index].sum(axis=1, min_count=1)
        for recorded_at, total in totals.dropna().items():
            rows.append({
                "recorded_at": recorded_at, "platform_name": platform_name,
                "platform_unit": unit, "total": total,
            })
    return pd.DataFrame(rows)


def platform_totals_chart(df: pd.DataFrame):
    """Courbe d'évolution des totaux par plateforme (somme de tous les éléments suivis)."""
    if df.empty:
        return None

    df = df.copy()
    df["recorded_at_fr"] = df["recorded_at"].apply(style.format_date_fr)

    fig = px.line(
        df, x="recorded_at", y="total", color="platform_name",
        markers=True, custom_data=["platform_unit", "recorded_at_fr"],
    )
    fig.update_traces(
        mode="lines+markers",
        marker=dict(size=6),
        hovertemplate="<b>%{fullData.name}</b><br>%{customdata[1]}<br>%{y:,.0f} %{customdata[0]}<extra></extra>",
    )
    fig.update_layout(showlegend=True, legend_title_text="", xaxis_title="", yaxis_title="", hovermode="closest")
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, gridcolor="#EDEEF0", zeroline=False, rangemode="tozero")
    _french_date_ticks(fig, df["recorded_at"])
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
        text="view_count",
        hover_data={"content_label": True, "color_key": False, "view_count": True},
    )
    fig.update_traces(texttemplate="%{text:,.0f}")
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

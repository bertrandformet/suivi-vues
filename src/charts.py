"""Construction des graphiques Plotly pour le tableau de bord.

La couleur code toujours le contenu (jamais la plateforme) : une couleur
stable par contenu, déclinée sur toutes ses URLs, pour rester lisible à
mesure que le nombre de plateformes suivies augmente.
"""

import pandas as pd
import plotly.express as px

from src import data as data_layer
from src import palette


def build_view_dataset() -> pd.DataFrame:
    """Relevés dédupliqués (dernière saisie par URL/date) enrichis avec plateforme et contenu."""
    snapshots = data_layer.latest_per_url_and_date(data_layer.load_snapshots())
    if snapshots.empty:
        return snapshots
    urls = data_layer.enriched_tracked_urls()
    merged = snapshots.merge(
        urls[["id", "label", "url", "platform_name", "content_title", "content_id"]],
        left_on="tracked_url_id",
        right_on="id",
        how="left",
    )
    merged["content_label"] = merged["content_title"].fillna(merged["label"])
    merged["color_key"] = merged.apply(palette.color_key, axis=1)
    return merged.sort_values("recorded_at")


def evolution_chart(df: pd.DataFrame, group_by: str = "label"):
    """Courbe d'évolution des vues, une ligne par `group_by` (label ou platform_name),
    colorée par contenu, avec étiquettes directes en bout de ligne (pas de légende)."""
    if df.empty:
        return None

    color_map = palette.build_color_map(df.sort_values("recorded_at")["color_key"])
    group_color = df.groupby(group_by)["color_key"].first().map(color_map).to_dict()

    fig = px.line(
        df,
        x="recorded_at",
        y="view_count",
        color=group_by,
        color_discrete_map=group_color,
        markers=False,
    )
    fig.update_traces(mode="lines")
    fig.update_layout(
        showlegend=False,
        xaxis_title="",
        yaxis_title="",
        hovermode="x unified",
        margin=dict(r=170),
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, gridcolor="#EDEEF0", zeroline=False)

    for trace_name, group in df.groupby(group_by):
        last = group.sort_values("recorded_at").iloc[-1]
        color = group_color.get(trace_name, "#33618F")
        fig.add_scatter(
            x=[last["recorded_at"]], y=[last["view_count"]],
            mode="markers", marker=dict(color=color, size=7),
            showlegend=False, hoverinfo="skip",
        )
        fig.add_annotation(
            x=last["recorded_at"], y=last["view_count"],
            text=f"<b>{trace_name}</b><br>{last['view_count']:,.0f}".replace(",", " "),
            showarrow=False, xanchor="left", xshift=10, align="left",
            font=dict(color=color, size=12),
        )
    return fig


def latest_by_platform_chart(df: pd.DataFrame):
    """Barres horizontales : dernier relevé connu par plateforme, colorées par contenu."""
    if df.empty:
        return None
    latest = df.sort_values("recorded_at").drop_duplicates(subset=["tracked_url_id"], keep="last")
    color_map = palette.build_color_map(latest["color_key"])

    fig = px.bar(
        latest.sort_values("view_count"),
        x="view_count",
        y="platform_name",
        color="color_key",
        color_discrete_map=color_map,
        orientation="h",
        text="view_count",
        hover_data={"content_label": True, "color_key": False, "view_count": True},
    )
    fig.update_traces(texttemplate="%{text:,.0f}")
    fig.update_layout(showlegend=False, xaxis_title="", yaxis_title="")
    return fig

"""Palette catégorielle stable par contenu (pas par plateforme), même
luminosité/chroma pour rester sobre. La plateforme est toujours indiquée par
du texte, jamais par la couleur (recommandation d'accessibilité)."""

PALETTE = [
    "#33618F",  # bleu
    "#8A6136",  # ocre
    "#3F7D69",  # vert sourd
    "#7A5A8C",  # mauve
    "#A24B4B",  # terracotta
    "#5C6B39",  # olive
    "#4C5B8F",  # indigo
    "#8F6B33",  # brun clair
]


def build_color_map(keys) -> dict:
    """Associe une couleur stable à chaque clé (content_id, ou id d'URL
    indépendante), dans l'ordre de première apparition."""
    ordered = list(dict.fromkeys(k for k in keys if k))
    return {key: PALETTE[i % len(PALETTE)] for i, key in enumerate(ordered)}


def color_key(row) -> str:
    """Clé de regroupement couleur : le contenu si présent, sinon l'URL elle-même."""
    content_id = row.get("content_id")
    if content_id:
        return content_id
    return row.get("tracked_url_id") or row.get("id")

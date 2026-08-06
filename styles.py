# -*- coding: utf-8 -*-
"""
styles.py — Extraction des styles QGIS (couleur, épaisseur, opacité...) et
conversion vers un format directement exploitable par Leaflet côté web.
"""

import logging

from qgis.core import QgsWkbTypes

from .qt_compat import qenum

logger = logging.getLogger(__name__)

MM_TO_PX = 3.78  # approximation mm -> px pour les épaisseurs/tailles QGIS

STYLE_PAR_DEFAUT = {
    "color": "#3388ff",
    "fillColor": "#3388ff",
    "weight": 1.0,
    "opacity": 1.0,
    "fillOpacity": 0.6,
    "radius": 6,
    "dashArray": None,
}


def extraire_style_symbole(symbol, geom_type):
    """Extrait fillColor, color, weight, opacity, fillOpacity, radius depuis un symbole QGIS.

    IMPORTANT : le curseur "Opacité" global du symbole (symbol.opacity(), réglable
    en haut du panneau Symbologie dans QGIS) est un MULTIPLICATEUR appliqué par-dessus
    la couleur du symbole — ce n'est pas la même chose que l'alpha de la couleur de
    remplissage elle-même. Les deux doivent être combinés, sinon un utilisateur qui
    règle la transparence via ce curseur (plutôt que via la couleur) voit son réglage
    totalement ignoré à l'export (fillOpacity resterait à 1.0 même si la couche est
    affichée à 50% de transparence dans QGIS).
    """
    style = dict(STYLE_PAR_DEFAUT)

    if not symbol or symbol.symbolLayerCount() == 0:
        return style

    sl = symbol.symbolLayer(0)

    opacite_globale = 1.0
    try:
        opacite_globale = symbol.opacity()
    except Exception as exc:
        logger.debug("Impossible de lire l'opacité du symbole : %s", exc)
    style["opacity"] = round(opacite_globale, 2)

    # ── POLYGONE ──
    if geom_type == qenum(QgsWkbTypes, "GeometryType", "PolygonGeometry"):
        if hasattr(sl, "fillColor") and sl.fillColor().isValid():
            c = sl.fillColor()
            style["fillColor"] = c.name()
            style["fillOpacity"] = round(
                (c.alpha() / 255.0) * opacite_globale, 2
            )
        else:
            style["fillColor"] = "#000000"
            style["fillOpacity"] = 0.0
        if hasattr(sl, "strokeColor") and sl.strokeColor().isValid():
            stroke = sl.strokeColor()
            style["color"] = stroke.name()
            style["opacity"] = round(
                (stroke.alpha() / 255.0) * opacite_globale, 2
            )
        elif hasattr(sl, "color") and sl.color().isValid():
            style["color"] = sl.color().name()
        if hasattr(sl, "strokeWidth"):
            try:
                style["weight"] = max(sl.strokeWidth() * MM_TO_PX, 0.5)
            except Exception as exc:
                logger.debug(
                    "Impossible de lire l'épaisseur du contour (polygone) : %s",
                    exc,
                )

    # ── LIGNE ──
    elif geom_type == qenum(QgsWkbTypes, "GeometryType", "LineGeometry"):
        couleur_ligne = None
        if hasattr(sl, "color") and sl.color().isValid():
            couleur_ligne = sl.color()
        if not couleur_ligne or not couleur_ligne.isValid():
            try:
                couleur_ligne = symbol.color()
            except Exception as exc:
                logger.debug(
                    "Impossible de lire la couleur de secours de la ligne : %s",
                    exc,
                )
        if couleur_ligne and couleur_ligne.isValid():
            style["color"] = couleur_ligne.name()
            style["opacity"] = round(
                (couleur_ligne.alpha() / 255.0) * opacite_globale, 2
            )
        if hasattr(sl, "width"):
            try:
                style["weight"] = max(sl.width() * MM_TO_PX, 1.0)
            except Exception as exc:
                logger.debug(
                    "Impossible de lire la largeur de la ligne : %s", exc
                )
        style["fillOpacity"] = 0.0

    # ── POINT ──
    else:
        if hasattr(sl, "color") and sl.color().isValid():
            c = sl.color()
            style["fillColor"] = c.name()
            style["color"] = c.name()
            style["fillOpacity"] = round(
                (c.alpha() / 255.0) * opacite_globale, 2
            )
        if hasattr(sl, "strokeColor") and sl.strokeColor().isValid():
            stroke = sl.strokeColor()
            style["color"] = stroke.name()
            style["opacity"] = round(
                (stroke.alpha() / 255.0) * opacite_globale, 2
            )
        try:
            style["radius"] = max(sl.size() * MM_TO_PX / 2.0, 3)
        except Exception as exc:
            logger.debug("Impossible de lire la taille du point : %s", exc)

    return style


def normaliser_valeur_classification(val):
    """Normalise une valeur de classification pour comparaison stable."""
    if val is None:
        return ""
    if isinstance(val, bool):
        return "true" if val else "false"
    if isinstance(val, (int, float)):
        f = float(val)
        if f.is_integer():
            return str(int(f))
        return repr(f).rstrip("0").rstrip(".") if "." in repr(f) else repr(f)
    # .strip() : indispensable pour les champs PostgreSQL de type "character(n)"
    return str(val).strip()


def construire_carte_styles_renderer(renderer, geom_type):
    """Construit une carte {valeur: style} (ou {'__plages__': [...]}) à partir du renderer QGIS."""
    carte = {}
    style_defaut = None

    try:
        if hasattr(renderer, "categories"):
            for cat in renderer.categories():
                symbol = cat.symbol()
                if symbol:
                    style = extraire_style_symbole(symbol, geom_type)
                    carte[normaliser_valeur_classification(cat.value())] = (
                        style
                    )
                    if cat.value() in (None, ""):
                        style_defaut = style

        elif hasattr(renderer, "ranges"):
            plages = []
            for rang in renderer.ranges():
                symbol = rang.symbol()
                if symbol:
                    style = extraire_style_symbole(symbol, geom_type)
                    plages.append(
                        (rang.lowerValue(), rang.upperValue(), style)
                    )
            carte["__plages__"] = plages

        elif hasattr(renderer, "symbol") and renderer.symbol():
            style = extraire_style_symbole(renderer.symbol(), geom_type)
            carte["default"] = style
            style_defaut = style

        elif hasattr(renderer, "rootRule"):
            rules = renderer.rootRule().children()
            if rules and rules[0].symbol():
                style_defaut = extraire_style_symbole(
                    rules[0].symbol(), geom_type
                )

    except Exception as exc:
        logger.debug(
            "Impossible de construire la carte des styles depuis le renderer : %s",
            exc,
        )

    if not style_defaut:
        style_defaut = dict(STYLE_PAR_DEFAUT)
    return carte, style_defaut


def lookup_style(carte_styles, style_defaut, renderer, feature):
    """Retrouve le style correspondant à une entité donnée selon le mode de classification du renderer."""
    try:
        if hasattr(renderer, "categories") and hasattr(
            renderer, "classAttribute"
        ):
            val = normaliser_valeur_classification(
                feature[renderer.classAttribute()]
            )
            return carte_styles.get(val, style_defaut)

        elif "__plages__" in carte_styles:
            attr = (
                renderer.classAttribute()
                if hasattr(renderer, "classAttribute")
                else None
            )
            if attr:
                try:
                    val = float(feature[attr])
                    for low, high, style in carte_styles["__plages__"]:
                        if low <= val <= high:
                            return style
                except (TypeError, ValueError):
                    pass

        elif "default" in carte_styles:
            return carte_styles["default"]

    except Exception as exc:
        logger.debug(
            "Impossible de retrouver le style pour l'entité, style par défaut utilisé : %s",
            exc,
        )
    return style_defaut

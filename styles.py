# -*- coding: utf-8 -*-
"""
styles.py — Extraction des styles QGIS (couleur, épaisseur, opacité...) et
conversion vers un format directement exploitable par Leaflet côté web.
"""

from qgis.core import QgsWkbTypes

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
    """Extrait fillColor, color, weight, opacity, fillOpacity, radius depuis un symbole QGIS."""
    style = dict(STYLE_PAR_DEFAUT)

    if not symbol or symbol.symbolLayerCount() == 0:
        return style

    sl = symbol.symbolLayer(0)

    try:
        op = symbol.opacity()
        style["opacity"] = round(op, 2)
    except Exception:
        pass

    # ── POLYGONE ──
    if geom_type == QgsWkbTypes.PolygonGeometry:
        if hasattr(sl, "fillColor") and sl.fillColor().isValid():
            c = sl.fillColor()
            style["fillColor"] = c.name()
            style["fillOpacity"] = round(c.alpha() / 255.0, 2)
        else:
            style["fillColor"] = "#000000"
            style["fillOpacity"] = 0.0
        if hasattr(sl, "strokeColor") and sl.strokeColor().isValid():
            style["color"] = sl.strokeColor().name()
        elif hasattr(sl, "color") and sl.color().isValid():
            style["color"] = sl.color().name()
        if hasattr(sl, "strokeWidth"):
            try:
                style["weight"] = max(sl.strokeWidth() * MM_TO_PX, 0.5)
            except Exception:
                pass

    # ── LIGNE ──
    elif geom_type == QgsWkbTypes.LineGeometry:
        couleur_ligne = None
        if hasattr(sl, "color") and sl.color().isValid():
            couleur_ligne = sl.color()
        if not couleur_ligne or not couleur_ligne.isValid():
            try:
                couleur_ligne = symbol.color()
            except Exception:
                pass
        if couleur_ligne and couleur_ligne.isValid():
            style["color"] = couleur_ligne.name()
        if hasattr(sl, "width"):
            try:
                style["weight"] = max(sl.width() * MM_TO_PX, 1.0)
            except Exception:
                pass
        style["fillOpacity"] = 0.0

    # ── POINT ──
    else:
        if hasattr(sl, "color") and sl.color().isValid():
            c = sl.color()
            style["fillColor"] = c.name()
            style["color"] = c.name()
        if hasattr(sl, "strokeColor") and sl.strokeColor().isValid():
            style["color"] = sl.strokeColor().name()
        try:
            style["radius"] = max(sl.size() * MM_TO_PX / 2.0, 3)
        except Exception:
            pass

    return style


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
                    carte[str(cat.value())] = style
                    if cat.value() in (None, ""):
                        style_defaut = style

        elif hasattr(renderer, "ranges"):
            plages = []
            for rang in renderer.ranges():
                symbol = rang.symbol()
                if symbol:
                    style = extraire_style_symbole(symbol, geom_type)
                    plages.append(
                        (rang.lowerValue(), rang.upperValue(), style))
            carte["__plages__"] = plages

        elif hasattr(renderer, "symbol") and renderer.symbol():
            style = extraire_style_symbole(renderer.symbol(), geom_type)
            carte["default"] = style
            style_defaut = style

        elif hasattr(renderer, "rootRule"):
            rules = renderer.rootRule().children()
            if rules and rules[0].symbol():
                style_defaut = extraire_style_symbole(
                    rules[0].symbol(), geom_type)

    except Exception:
        pass

    if not style_defaut:
        style_defaut = dict(STYLE_PAR_DEFAUT)
    return carte, style_defaut


def lookup_style(carte_styles, style_defaut, renderer, feature):
    """Retrouve le style correspondant à une entité donnée selon le mode de classification du renderer."""
    try:
        if hasattr(
                renderer,
                "categories") and hasattr(
                renderer,
                "classAttribute"):
            val = (
                str(feature[renderer.classAttribute()])
                if feature[renderer.classAttribute()] is not None
                else ""
            )
            return carte_styles.get(val, style_defaut)

        elif "__plages__" in carte_styles:
            attr = renderer.classAttribute() if hasattr(
                renderer, "classAttribute") else None
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

    except Exception:
        pass
    return style_defaut

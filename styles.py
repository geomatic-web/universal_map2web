# -*- coding: utf-8 -*-
"""
styles.py — Extraction des styles QGIS (couleur, épaisseur, opacité...) et
conversion vers un format directement exploitable par Leaflet côté web.
"""

import logging
import os

from qgis.core import (
    QgsExpression,
    QgsExpressionContext,
    QgsSymbolLayerUtils,
    QgsUnitTypes,
    QgsWkbTypes,
)
from qgis.PyQt.QtCore import QSize

from .qt_compat import qenum

logger = logging.getLogger(__name__)

MM_TO_PX = 3.78  # approximation mm -> px pour les épaisseurs/tailles QGIS
TAILLE_MOTIF_MIN_PX = 8
TAILLE_MOTIF_MAX_PX = 48
TAILLE_MOTIF_DEFAUT_PX = 16

STYLE_PAR_DEFAUT = {
    "color": "#3388ff",
    "fillColor": "#3388ff",
    "weight": 1.0,
    "opacity": 1.0,
    "fillOpacity": 0.6,
    "radius": 6,
    "dashArray": None,
}


def _generer_tuile_motif(symbol_layer, nom_fichier_couche, styles_dir, suffixe):
    """Génère une tuile PNG (fond transparent) pour UNE couche de symbole
    polygone secondaire (hachure, grille de points, glyphe TTF, SVG externe...),
    afin de pouvoir la rejouer en motif répété (pattern SVG) sur la carte web.

    Renvoie {'img': 'styles_images/...png', 'taille': <px>} ou None si la
    génération échoue (dégradation silencieuse : le motif est alors simplement
    absent côté carte, sans casser l'export).
    """
    try:
        taille_px = TAILLE_MOTIF_DEFAUT_PX
        if hasattr(symbol_layer, "size"):
            try:
                taille_mm = symbol_layer.size()
                if taille_mm and taille_mm > 0:
                    taille_px = taille_mm * MM_TO_PX
            except Exception as exc:
                logger.debug(
                    "Impossible de lire la taille de la couche de motif : %s",
                    exc,
                )
        # Ajoute l'espacement ("graphic-margin") si lisible, pour que la tuile
        # corresponde à une unité de répétition complète et non juste au glyphe.
        if hasattr(symbol_layer, "distanceX") and hasattr(symbol_layer, "distanceY"):
            try:
                taille_px = max(
                    taille_px,
                    (symbol_layer.distanceX() or 0) * MM_TO_PX,
                    (symbol_layer.distanceY() or 0) * MM_TO_PX,
                )
            except Exception as exc:
                logger.debug("Impossible de lire l'espacement du motif : %s", exc)
        taille_px = int(
            round(min(max(taille_px, TAILLE_MOTIF_MIN_PX), TAILLE_MOTIF_MAX_PX))
        )

        os.makedirs(styles_dir, exist_ok=True)
        img_name = f"motif_{nom_fichier_couche}_{suffixe}.png"
        img_path = os.path.join(styles_dir, img_name)

        pixmap = QgsSymbolLayerUtils.symbolLayerPreviewPixmap(
            symbol_layer,
            QgsUnitTypes.RenderUnit.RenderPixels,
            QSize(taille_px, taille_px),
        )
        if pixmap is None or pixmap.isNull():
            return None
        pixmap.save(img_path, "PNG")

        return {"img": f"styles_images/{img_name}", "taille": taille_px}

    except Exception as exc:
        logger.debug("Impossible de générer la tuile de motif '%s' : %s", suffixe, exc)
        return None


def taille_canevas_icone(symbol, taille_min=24):
    """Calcule une taille de canevas (px, carré) juste assez grande pour
    contenir l'aperçu d'un symbole ponctuel QGIS sans le rogner.

    IMPORTANT : `symbolPreviewPixmap()` ne redimensionne pas le symbole pour
    remplir le QSize demandé — il le dessine à sa taille physique réelle
    (mm -> px, via MM_TO_PX) et centre ce rendu dans le canevas. Un canevas
    trop grand par rapport à cette taille réelle ne rogne plus rien, mais
    noie le glyphe dans une marge vide : une fois ce PNG réduit à la petite
    taille d'affichage de la légende/carte, le symbole paraît minuscule.
    La marge ajoutée ici doit donc rester modeste — juste de quoi absorber
    l'arrondi et un éventuel décalage (`offset`), pas un gonflement large
    du canevas.
    """
    taille_px = taille_min
    try:
        if hasattr(symbol, "size") and symbol.size() > 0:
            # Marge modeste (25 %) pour ne pas rogner un symbole légèrement
            # allongé/tourné, sans le diluer dans un canevas surdimensionné.
            taille_px = max(taille_min, int(round(symbol.size() * MM_TO_PX * 1.25)))
    except Exception as exc:
        logger.debug("Impossible de lire la taille du symbole : %s", exc)

    try:
        sl0 = symbol.symbolLayer(0) if symbol.symbolLayerCount() > 0 else None
        if sl0 is not None and hasattr(sl0, "offset"):
            offset = sl0.offset()
            # Marge ciblée = 2x l'ampleur réelle du décalage (couvre les deux
            # directions), pas un doublement généralisé du canevas.
            marge_offset = max(abs(offset.x()), abs(offset.y())) * MM_TO_PX * 2.0
            if marge_offset > 0:
                taille_px = int(round(taille_px + marge_offset))
    except Exception as exc:
        logger.debug("Impossible de lire le décalage du symbole : %s", exc)

    return taille_px


def _generer_icone_point(symbol, nom_fichier_couche, styles_dir, suffixe, taille=24):
    """Génère l'aperçu PNG d'un symbole de point, dimensionné au plus près
    de sa taille réelle (voir `taille_canevas_icone`) pour ne pas le
    diluer une fois réduit à la taille d'affichage sur la carte.
    """
    try:
        os.makedirs(styles_dir, exist_ok=True)

        taille_px = taille_canevas_icone(symbol, taille_min=taille)

        img_name = f"icone_{nom_fichier_couche}_{suffixe}.png"
        img_path = os.path.join(styles_dir, img_name)

        pixmap = QgsSymbolLayerUtils.symbolPreviewPixmap(
            symbol, QSize(taille_px, taille_px)
        )
        if pixmap is None or pixmap.isNull():
            return None

        pixmap.save(img_path, "PNG")
        return f"styles_images/{img_name}"

    except Exception as exc:
        logger.debug("Impossible de générer l'icône de point '%s' : %s", suffixe, exc)
        return None


def extraire_proprietes_icone(symbol, symbol_layer=None, taille_min_web=30):
    """Calcule les dimensions (size) et l'ancrage (anchor) pour Leaflet.
    Agrandit automatiquement les icônes trop petites pour le web.
    """
    try:
        sl = (
            symbol_layer
            if symbol_layer
            else (
                symbol.symbolLayer(0)
                if symbol and symbol.symbolLayerCount() > 0
                else None
            )
        )

        taille_qgis = (
            symbol.size() if hasattr(symbol, "size") and symbol.size() > 0 else 6.0
        )
        w_px = taille_qgis * MM_TO_PX
        h_px = w_px

        # Gestion du ratio hauteur/largeur
        if sl and hasattr(sl, "aspectRatio") and sl.aspectRatio() > 0:
            h_px = w_px / sl.aspectRatio()

        # Si le symbole est trop petit pour un écran web, on rééchelonne
        facteur = 1.0
        max_dim = max(w_px, h_px)
        if max_dim < taille_min_web:
            facteur = taille_min_web / max_dim

        w_px = max(int(round(w_px * facteur)), taille_min_web)
        h_px = max(int(round(h_px * facteur)), taille_min_web)

        # Ancrage au centre par défaut
        anchor_x = w_px / 2.0
        anchor_y = h_px / 2.0

        # Prise en compte de l'offset QGIS
        if sl and hasattr(sl, "offset"):
            offset = sl.offset()
            anchor_x -= offset.x() * MM_TO_PX * facteur
            anchor_y -= offset.y() * MM_TO_PX * facteur

        return {
            "size": [w_px, h_px],
            "anchor": [int(round(anchor_x)), int(round(anchor_y))],
        }

    except Exception as exc:
        logger.debug("Erreur lors de l'extraction des dimensions d'icône : %s", exc)
        return {"size": [32, 32], "anchor": [16, 32]}


def extraire_style_symbole(symbol, geom_type, contexte_motifs=None):
    """Extrait fillColor, color, weight, opacity, fillOpacity, radius, icone et iconeProps

    depuis un symbole QGIS.
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
            style["fillOpacity"] = round((c.alpha() / 255.0) * opacite_globale, 2)
        else:
            style["fillColor"] = "#000000"
            style["fillOpacity"] = 0.0
        if hasattr(sl, "strokeColor") and sl.strokeColor().isValid():
            stroke = sl.strokeColor()
            style["color"] = stroke.name()
            style["opacity"] = round((stroke.alpha() / 255.0) * opacite_globale, 2)
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
                if (
                    hasattr(sl, "widthUnit")
                    and sl.widthUnit() == QgsUnitTypes.RenderUnit.RenderPixels
                ):
                    style["weight"] = max(sl.width(), 1.0)
                else:
                    style["weight"] = max(sl.width() * MM_TO_PX, 1.0)
            except Exception as exc:
                logger.debug("Impossible de lire la largeur de la ligne : %s", exc)
        style["fillOpacity"] = 0.0

        # Extraction du style de pointillés/tirets (dashArray)
        try:
            if hasattr(sl, "useCustomDashPattern") and sl.useCustomDashPattern():
                dash_vec = (
                    sl.customDashVector() if hasattr(sl, "customDashVector") else []
                )
                if dash_vec:
                    pattern = [max(int(round(x * MM_TO_PX)), 1) for x in dash_vec]
                    style["dashArray"] = ", ".join(map(str, pattern))
            elif hasattr(sl, "penStyle"):
                ps_val = int(sl.penStyle())
                if ps_val == 2:
                    style["dashArray"] = "6, 6"
                elif ps_val == 3:
                    style["dashArray"] = "2, 4"
                elif ps_val == 4:
                    style["dashArray"] = "6, 4, 2, 4"
                elif ps_val == 5:
                    style["dashArray"] = "6, 4, 2, 4, 2, 4"
        except Exception as exc:
            logger.debug(
                "Impossible d'extraire le motif de tirets de la ligne : %s", exc
            )

    # ── POINT ──
    else:
        if hasattr(sl, "color") and sl.color().isValid():
            c = sl.color()
            style["fillColor"] = c.name()
            style["color"] = c.name()
            style["fillOpacity"] = round((c.alpha() / 255.0) * opacite_globale, 2)
        if hasattr(sl, "strokeColor") and sl.strokeColor().isValid():
            stroke = sl.strokeColor()
            style["color"] = stroke.name()
            style["opacity"] = round((stroke.alpha() / 255.0) * opacite_globale, 2)
        try:
            style["radius"] = max(sl.size() * MM_TO_PX / 2.0, 3)
        except Exception as exc:
            logger.debug("Impossible de lire la taille du point : %s", exc)

        # Génération de l'icône PNG et des dimensions d'ancrage pour Leaflet
        if contexte_motifs is not None:
            nom_fichier_couche, styles_dir, prefixe = contexte_motifs
            icone = _generer_icone_point(
                symbol, nom_fichier_couche, styles_dir, prefixe
            )
            if icone:
                style["icone"] = icone
                style["iconeProps"] = extraire_proprietes_icone(symbol, sl)

    # ── Motifs de remplissage supplémentaires (polygones uniquement) ──
    if (
        contexte_motifs is not None
        and geom_type == qenum(QgsWkbTypes, "GeometryType", "PolygonGeometry")
        and symbol.symbolLayerCount() > 1
    ):
        nom_fichier_couche, styles_dir, prefixe = contexte_motifs
        motifs = []
        for idx_couche in range(1, symbol.symbolLayerCount()):
            try:
                sl_motif = symbol.symbolLayer(idx_couche)
            except Exception as exc:
                logger.debug(
                    "Impossible d'accéder à la couche de motif %s : %s",
                    idx_couche,
                    exc,
                )
                continue
            tuile = _generer_tuile_motif(
                sl_motif,
                nom_fichier_couche,
                styles_dir,
                f"{prefixe}_{idx_couche}",
            )
            if tuile:
                motifs.append(tuile)
        if motifs:
            style["motifs"] = motifs

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


def _aplatir_regles_renderer(
    rule_node, geom_type, filtre_parent, out, nom_fichier_couche=None, styles_dir=None
):
    """Parcourt récursivement l'arbre de règles d'un renderer 'Basé sur des règles'
    QGIS et ajoute à `out` une entrée par règle porteuse d'un symbole : son
    expression de filtre compilée (combinée avec celles de ses règles parentes,
    comme le fait QGIS), un indicateur 'règle sinon' (ElseFilter), et son style.
    """
    for regle in rule_node.children():
        try:
            filtre_regle = regle.filterExpression() or ""
        except Exception as exc:
            logger.debug("Impossible de lire le filtre de la règle : %s", exc)
            filtre_regle = ""

        est_else = False
        try:
            est_else = bool(regle.isElse())
        except Exception as exc:
            logger.debug(
                "Impossible de savoir si la règle est une règle 'sinon' : %s", exc
            )

        if filtre_parent and filtre_regle:
            filtre_combine = "(%s) AND (%s)" % (filtre_parent, filtre_regle)
        else:
            filtre_combine = filtre_parent or filtre_regle

        symbole = regle.symbol()
        if symbole:
            expression = None
            if filtre_combine and not est_else:
                try:
                    expression = QgsExpression(filtre_combine)
                    if expression.hasParserError():
                        logger.debug(
                            "Expression de règle invalide ignorée (%s) : %s",
                            filtre_combine,
                            expression.parserErrorString(),
                        )
                        expression = None
                except Exception as exc:
                    logger.debug(
                        "Impossible de compiler l'expression de règle '%s' : %s",
                        filtre_combine,
                        exc,
                    )
                    expression = None

            contexte_motifs = None
            if nom_fichier_couche and styles_dir:
                contexte_motifs = (
                    nom_fichier_couche,
                    styles_dir,
                    f"regle{len(out)}",
                )

            out.append(
                {
                    "expression": expression,
                    "est_else": est_else,
                    "style": extraire_style_symbole(
                        symbole, geom_type, contexte_motifs
                    ),
                }
            )

        # Règles imbriquées (héritent du filtre de leur parent, comme dans QGIS)
        try:
            a_des_enfants = len(regle.children()) > 0
        except Exception:
            a_des_enfants = False
        if a_des_enfants:
            _aplatir_regles_renderer(
                regle,
                geom_type,
                filtre_combine,
                out,
                nom_fichier_couche,
                styles_dir,
            )


def _carte_a_des_motifs(carte, style_defaut):
    """Indique si la carte de styles (ou le style par défaut) contient au moins
    un motif de remplissage supplémentaire — utile pour savoir si la couche a
    besoin d'un rendu SVG (seul capable d'afficher des motifs en pattern) côté
    carte web plutôt que du Canvas (plus rapide mais sans support de motif).
    """
    if style_defaut and "motifs" in style_defaut:
        return True
    for cle, valeur in carte.items():
        if cle == "__plages__":
            for item in valeur:
                if len(item) == 3 and item[2] and "motifs" in item[2]:
                    return True
        elif cle == "__regles__":
            for regle in valeur:
                if "motifs" in (regle.get("style") or {}):
                    return True
        elif isinstance(valeur, dict) and "motifs" in valeur:
            return True
    return False


def construire_carte_styles_renderer(
    renderer, geom_type, nom_fichier_couche=None, styles_dir=None
):
    """Construit une carte {valeur: style} (ou {'__plages__': [...]}) à partir du renderer QGIS.

    `nom_fichier_couche` et `styles_dir`, si fournis, activent la génération de
    tuiles PNG pour les motifs de remplissage polygone (cf. `extraire_style_symbole`).

    Renvoie (carte_styles, style_defaut, a_des_motifs).
    """
    carte = {}
    style_defaut = None

    def _contexte(prefixe):
        if nom_fichier_couche and styles_dir:
            return (nom_fichier_couche, styles_dir, prefixe)
        return None

    try:
        if hasattr(renderer, "categories"):
            for idx, cat in enumerate(renderer.categories()):
                symbol = cat.symbol()
                if symbol:
                    style = extraire_style_symbole(
                        symbol, geom_type, _contexte(f"cat{idx}")
                    )
                    carte[normaliser_valeur_classification(cat.value())] = style
                    if cat.value() in (None, ""):
                        style_defaut = style

        elif hasattr(renderer, "ranges"):
            plages = []
            for idx, rang in enumerate(renderer.ranges()):
                symbol = rang.symbol()
                if symbol:
                    style = extraire_style_symbole(
                        symbol, geom_type, _contexte(f"rang{idx}")
                    )
                    plages.append((rang.lowerValue(), rang.upperValue(), style))
            carte["__plages__"] = plages

        elif hasattr(renderer, "symbol") and renderer.symbol():
            style = extraire_style_symbole(
                renderer.symbol(), geom_type, _contexte("default")
            )
            carte["default"] = style
            style_defaut = style

        elif hasattr(renderer, "rootRule"):
            regles = []
            _aplatir_regles_renderer(
                renderer.rootRule(),
                geom_type,
                "",
                regles,
                nom_fichier_couche,
                styles_dir,
            )
            if regles:
                carte["__regles__"] = regles
                # Style par défaut : la règle 'sinon' si elle existe, sinon la
                # première règle rencontrée (mieux que STYLE_PAR_DEFAUT générique).
                for r in regles:
                    if r["est_else"]:
                        style_defaut = r["style"]
                        break
                if style_defaut is None:
                    style_defaut = regles[0]["style"]

    except Exception as exc:
        logger.debug(
            "Impossible de construire la carte des styles depuis le renderer : %s",
            exc,
        )

    if not style_defaut:
        style_defaut = dict(STYLE_PAR_DEFAUT)

    a_des_motifs = _carte_a_des_motifs(carte, style_defaut)
    return carte, style_defaut, a_des_motifs


def lookup_style(carte_styles, style_defaut, renderer, feature):
    """Retrouve le style correspondant à une entité donnée selon le mode de classification du renderer."""
    try:
        if hasattr(renderer, "categories") and hasattr(renderer, "classAttribute"):
            val = normaliser_valeur_classification(feature[renderer.classAttribute()])
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

        elif "__regles__" in carte_styles:
            contexte = QgsExpressionContext()
            contexte.setFeature(feature)
            style_sinon = None
            for regle in carte_styles["__regles__"]:
                if regle["est_else"]:
                    if style_sinon is None:
                        style_sinon = regle["style"]
                    continue
                expression = regle["expression"]
                if expression is None:
                    continue
                try:
                    if bool(expression.evaluate(contexte)):
                        return regle["style"]
                except Exception as exc:
                    logger.debug("Erreur d'évaluation d'une règle de style : %s", exc)
            if style_sinon is not None:
                return style_sinon

        elif "default" in carte_styles:
            return carte_styles["default"]

    except Exception as exc:
        logger.debug(
            "Impossible de retrouver le style pour l'entité, style par défaut utilisé : %s",
            exc,
        )
    return style_defaut

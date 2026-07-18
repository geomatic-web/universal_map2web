# -*- coding: utf-8 -*-
"""
legend.py — Génération des miniatures PNG de légende (points et lignes catégorisés)
à partir du renderer/symbologie QGIS d'une couche.

NOTE DE CORRECTION : le fichier d'origine contenait un bloc de code dupliqué et
orphelin (résidu d'un copier-coller) qui utilisait la variable `nom_fichier_couche`
sans qu'elle ne soit jamais définie ni passée en paramètre, d'où les erreurs
flake8 F821 "undefined name 'nom_fichier_couche'". Ce module ne conserve que la
version correcte de la fonction, où le nom de fichier est bien reçu en paramètre.
"""

import os

from qgis.core import QgsSymbolLayerUtils, QgsWkbTypes
from qgis.PyQt.QtCore import QSize


def extraire_icones_symbologie(layer, nom_fichier_couche, styles_dir):
    """Génère des miniatures PNG pour la légende des points et lignes.

    Args:
        layer: la couche vecteur QGIS.
        nom_fichier_couche: nom de fichier (déjà nettoyé) identifiant la couche,
            utilisé pour préfixer les fichiers PNG générés et éviter les collisions
            entre couches.
        styles_dir: dossier de sortie où écrire les images (créé si nécessaire).
    """
    icones_exportees = []
    if layer.geometryType() == QgsWkbTypes.GeometryType.PolygonGeometry:
        return icones_exportees

    renderer = layer.renderer()
    if not renderer:
        return icones_exportees

    os.makedirs(styles_dir, exist_ok=True)

    def _exporter_icone(symbol, suffixe):
        img_name = f"icon_{nom_fichier_couche}_{suffixe}.png"
        img_path = os.path.join(styles_dir, img_name)
        pixmap = QgsSymbolLayerUtils.symbolPreviewPixmap(symbol, QSize(24, 24))
        pixmap.save(img_path, "PNG")
        return f"styles_images/{img_name}"

    if hasattr(renderer, "categories") and len(renderer.categories()) > 0:
        for idx, cat in enumerate(renderer.categories()):
            label = cat.label() if cat.label() else str(cat.value())
            symbol = cat.symbol()
            if symbol:
                icones_exportees.append(
                    {
                        "valeur": str(cat.value()),
                        "label": label,
                        "img_path": _exporter_icone(symbol, str(idx)),
                    }
                )

    elif hasattr(renderer, "ranges") and len(renderer.ranges()) > 0:
        for idx, rang in enumerate(renderer.ranges()):
            label = rang.label() if rang.label() else f"{
                rang.lowerValue():.2f} – {
                rang.upperValue():.2f}"
            symbol = rang.symbol()
            if symbol:
                icones_exportees.append(
                    {
                        "valeur": str(rang.lowerValue()),
                        "label": label,
                        "img_path": _exporter_icone(symbol, f"grad_{idx}"),
                    }
                )

    elif hasattr(renderer, "rootRule"):
        for idx, rule in enumerate(renderer.rootRule().children()):
            label = rule.label() if rule.label() else f"Règle {idx + 1}"
            symbol = rule.symbol()
            if symbol:
                icones_exportees.append(
                    {
                        "valeur": label,
                        "label": label,
                        "img_path": _exporter_icone(symbol, f"rule_{idx}"),
                    }
                )

    elif hasattr(renderer, "symbol") and renderer.symbol():
        symbol = renderer.symbol()
        icones_exportees.append(
            {
                "valeur": "default",
                "label": layer.name(),
                "img_path": _exporter_icone(symbol, "unique"),
            }
        )

    return icones_exportees

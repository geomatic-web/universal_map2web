# -*- coding: utf-8 -*-
"""
utils.py — Petits utilitaires génériques sans dépendance à l'interface QGIS.
"""

from qgis.core import QgsMapLayer, QgsWkbTypes

# Caractères remplacés par "_" lors de la génération d'un nom de fichier sûr
_CARACTERES_SPECIAUX = [
    " ",
    "/",
    "\\",
    ":",
    "*",
    "?",
    '"',
    "<",
    ">",
    "|",
    "é",
    "è",
    "ê",
    "à",
    "â",
    "î",
    "ô",
    "û",
    "ç",
    "(",
    ")",
    "[",
    "]",
    "{",
    "}",
    ";",
    ",",
]


def clean_filename(name):
    """Convertit un nom de couche QGIS en nom de fichier sûr pour le système de fichiers."""
    for char in _CARACTERES_SPECIAUX:
        name = name.replace(char, "_")
    while "__" in name:
        name = name.replace("__", "_")
    return name.strip("_")


def get_geometry_type(layer):
    """Retourne le type de géométrie lisible d'une couche QGIS (ou 'Inconnu')."""
    if layer.type() != QgsMapLayer.VectorLayer:
        return "Inconnu"
    return QgsWkbTypes.geometryType(layer.wkbType())

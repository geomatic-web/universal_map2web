# -*- coding: utf-8 -*-
"""
geojson.py — Conversion d'une couche vecteur QGIS en GeoJSON (EPSG:4326), avec
injection du style QGIS résolu par entité (utile pour un rendu Leaflet fidèle).
"""

import json

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsProject,
)

from .styles import (
    construire_carte_styles_renderer,
    lookup_style,
    normaliser_valeur_classification,
)


def layer_to_geojson(
    layer, popup_fields=None, nom_fichier_couche=None, styles_dir=None
):
    """Convertit une couche vecteur QGIS en FeatureCollection GeoJSON (WGS84).

    `nom_fichier_couche`/`styles_dir` sont optionnels : s'ils sont fournis, les
    motifs de remplissage polygone (hachures, grilles de points...) sont
    exportés en tuiles PNG et rattachés aux styles (cf. styles.py).

    Renvoie (feature_collection, a_des_motifs).
    """
    features = []
    crs_dest = QgsCoordinateReferenceSystem("EPSG:4326")
    transform = QgsCoordinateTransform(layer.crs(), crs_dest, QgsProject.instance())

    renderer = layer.renderer()
    geom_type = layer.geometryType()
    attribut_classification = (
        renderer.classAttribute() if hasattr(renderer, "classAttribute") else None
    )

    carte_styles, style_defaut, a_des_motifs = construire_carte_styles_renderer(
        renderer, geom_type, nom_fichier_couche, styles_dir
    )

    for feature in layer.getFeatures():
        geom = feature.geometry()
        if geom and not geom.isEmpty():
            geom.transform(transform)
            geojson_geom = json.loads(geom.asJson())

            props = {}
            champs_a_exporter = (
                popup_fields if popup_fields else [f.name() for f in layer.fields()]
            )
            for field_name in champs_a_exporter:
                if layer.fields().indexOf(field_name) != -1:
                    val = feature[field_name]
                    props[field_name] = str(val) if val is not None else ""

            val_classe = (
                normaliser_valeur_classification(feature[attribut_classification])
                if (
                    attribut_classification
                    and feature[attribut_classification] is not None
                )
                else "default"
            )
            props["_qgis_class_val"] = val_classe

            style = lookup_style(carte_styles, style_defaut, renderer, feature)
            props["_qgis_style"] = style

            features.append(
                {
                    "type": "Feature",
                    "geometry": geojson_geom,
                    "properties": props,
                }
            )

    feature_collection = {
        "type": "FeatureCollection",
        "crs": {"type": "name", "properties": {"name": "EPSG:4326"}},
        "features": features,
    }
    return feature_collection, a_des_motifs

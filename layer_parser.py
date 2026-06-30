# -*- coding: utf-8 -*-

import json
from qgis.core import QgsMapLayer, QgsSymbol


def layer_to_geojson(layer, popup_fields=None):
    """Convertit une couche vectorielle en GeoJSON avec métadonnées de style QGIS"""
    if layer.type() != QgsMapLayer.VectorLayer:
        return {'type': 'FeatureCollection', 'features': []}

    features = []
    crs = layer.crs().authid()
    renderer = layer.renderer()

    for feature in layer.getFeatures():
        geom = feature.geometry()
        if not geom or geom.isEmpty():
            continue

        geojson_geom = json.loads(geom.asJson())

        # Extraire les propriétés d'attributs configurées
        props = {}
        champs = popup_fields if popup_fields else [
            f.name() for f in layer.fields()]
        for field_name in champs:
            if layer.fields().indexOf(field_name) != -1:
                value = feature[field_name]
                props[field_name] = str(value) if value is not None else ""

        # --- CORRECTION 1 : EXTRACTION CACHÉE DU STYLE RÉEL DE L'ENTITÉ ---
        style_entite = extraire_style_complet_entite(layer, feature, renderer)

        props["_qgis_color"] = style_entite["color"]
        props["_qgis_weight"] = style_entite["weight"]
        props["_qgis_opacity"] = style_entite["opacity"]
        props["_qgis_fill_opacity"] = style_entite["fill_opacity"]

        # Injection systématique de la valeur de classe textuelle pour le
        # couplage Leaflet
        if renderer and hasattr(renderer, 'classAttribute'):
            class_attr = renderer.classAttribute()
            if class_attr:
                val = feature[class_attr]
                props["_qgis_class_val"] = str(
                    val).strip() if val is not None else "default"
        else:
            props["_qgis_class_val"] = "default"

        features.append({
            'type': 'Feature',
            'geometry': geojson_geom,
            'properties': props
        })

    return {
        'type': 'FeatureCollection',
        'crs': {'type': 'name', 'properties': {'name': crs}},
        'features': features
    }


def extraire_style_complet_entite(layer, feature, renderer):
    """Extrait l'ensemble des propriétés physiques calculées par QGIS pour une entité"""
    style = {
        "color": "#3388ff",
        "weight": 2.0,
        "opacity": 1.0,
        "fill_opacity": 0.55
    }

    if not renderer:
        return style

    try:
        # Évaluation du symbole dans le contexte propre de l'entité
        # (indispensable pour graduated/categorized)
        ctx = renderer.createExpressionContext(layer)
        ctx.setFeature(feature)
        symbol = renderer.symbolForFeature(feature, ctx)

        if symbol:
            # Récupération de la couleur principale du symbole global
            q_color = symbol.color()
            if q_color and q_color.isValid():
                style["color"] = q_color.name()
                style["opacity"] = q_color.alpha() / 255.0

            if symbol.symbolLayerCount() > 0:
                sl = symbol.symbolLayer(0)
                props = sl.properties()

                # Ajustement de l'épaisseur (Conversion mm vers Pixels pour le
                # Web : x3.78)
                if 'outline_width' in props:
                    style["weight"] = float(props['outline_width']) * 3.78
                elif 'width' in props:
                    style["weight"] = float(props['width']) * 3.78
                elif 'line_width' in props:
                    style["weight"] = float(props['line_width']) * 3.78

                # Gestion fine du niveau de transparence du remplissage
                if layer.geometryType() == 1:  # Mode Ligne
                    style["fill_opacity"] = 0.0
                # Remplissage transparent
                elif 'style' in props and props['style'] == 'no':
                    style["fill_opacity"] = 0.0
    except BaseException:
        pass

    return style

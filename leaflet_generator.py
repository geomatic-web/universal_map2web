# -*- coding: utf-8 -*-
"""
leaflet_generator.py — Construit le fichier app.js final d'un export à partir du
template statique templates/app.js, en y injectant les métadonnées des couches,
le fond de plan choisi et les blocs JS d'initialisation des outils Leaflet
optionnels (mesure, plein écran, géolocalisation, recherche, mini-carte, etc.).
"""

import json
import os

from .web_i18n import get_strings

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")

# (clé d'option du dialogue, lib CSS, lib JS) pour chaque outil optionnel
_LIBS_CDN = {
    "mesure": {
        "css": '\n    <link rel="stylesheet" href="https://unpkg.com/leaflet-measure@3.1.0/dist/leaflet-measure.css" />',
        "js": '\n    <script src="https://unpkg.com/leaflet-measure@3.1.0/dist/leaflet-measure.js"></script>',
    },
    "pleinecran": {
        "css": '\n    <link rel="stylesheet" href="https://unpkg.com/leaflet.fullscreen@1.6.0/Control.FullScreen.css" />',
        "js": '\n    <script src="https://unpkg.com/leaflet.fullscreen@1.6.0/Control.FullScreen.js"></script>',
    },
    "recherche": {
        "css": '\n    <link rel="stylesheet" href="https://unpkg.com/leaflet-control-geocoder/dist/Control.Geocoder.css" />',
        "js": '\n    <script src="https://unpkg.com/leaflet-control-geocoder/dist/Control.Geocoder.js"></script>',
    },
    "minimap": {
        "css": '\n    <link rel="stylesheet" href="https://unpkg.com/leaflet-minimap@3.6.1/dist/Control.MiniMap.min.css" />',
        "js": '\n    <script src="https://unpkg.com/leaflet-minimap@3.6.1/dist/Control.MiniMap.min.js"></script>',
    },
    "geoloc": {
        "css": '\n    <link rel="stylesheet" href="https://unpkg.com/leaflet.locatecontrol/dist/L.Control.Locate.min.css" />',
        "js": '\n    <script src="https://unpkg.com/leaflet.locatecontrol/dist/L.Control.Locate.min.js"></script>',
    },
}

# Le clustering est toujours chargé : on l'utilise pour toutes les couches
# ponctuelles.
_CLUSTER_CSS = (
    '\n    <link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.css" />'
    '\n    <link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.Default.css" />'
)
_CLUSTER_JS = '\n    <script src="https://unpkg.com/leaflet.markercluster@1.5.3/dist/leaflet.markercluster.js"></script>'


def build_extra_libs(options):
    """Construit les balises <link>/<script> CDN à insérer dans <head>, selon les
    outils optionnels activés dans le dialogue (options est un dict de booléens)."""
    extra_css = _CLUSTER_CSS
    extra_js = _CLUSTER_JS
    for cle, libs in _LIBS_CDN.items():
        if options.get(cle):
            extra_css += libs["css"]
            extra_js += libs["js"]
    return extra_css, extra_js


def build_outils_js(options, locale=None):
    """Construit le bloc JS d'initialisation des contrôles Leaflet optionnels,
    injecté dans app.js à la place du marqueur __OUTILS_JS__.
    Les libellés affichés (position, plein écran, recherche, impression...)
    suivent la langue de QGIS (locale 'fr' ou 'en')."""
    s = get_strings(locale)
    outils_js = ""

    if options.get("attribution", True):
        outils_js += (
            "\n        map.attributionControl.setPrefix('Leaflet | Universal Map2web');"
        )
    else:
        outils_js += "\n        map.removeControl(map.attributionControl);"

    if options.get("echelle", True):
        outils_js += "\n        L.control.scale({ imperial: false, metric: true, position: 'bottomleft' }).addTo(map);"

    if options.get("geoloc"):
        outils_js += (
            "\n        if (typeof L.control.locate !== 'undefined') { "
            "L.control.locate({ position: 'topleft', flyTo: true, strings: { title: %s } }).addTo(map); }"
            % json.dumps(s["my_position"], ensure_ascii=False)
        )

    if options.get("mesure"):
        outils_js += (
            "\n        if (typeof L.control.measure !== 'undefined') { "
            "L.control.measure({ primaryLengthUnit:'kilometers', secondaryLengthUnit:'meters', "
            "primaryAreaUnit:'sqkilometers', activeColor:'#4ecdc4', completedColor:'#4ecdc4' }).addTo(map); }"
        )

    if options.get("pleinecran"):
        outils_js += (
            "\n        if (typeof L.control.fullscreen !== 'undefined') { "
            "L.control.fullscreen({ title: %s, titleCancel: %s }).addTo(map); }"
            % (
                json.dumps(s["fullscreen_title"], ensure_ascii=False),
                json.dumps(s["fullscreen_cancel"], ensure_ascii=False),
            )
        )

    if options.get("recherche"):
        outils_js += (
            "\n        if (typeof L.Control.Geocoder !== 'undefined') { "
            "L.Control.geocoder({ defaultMarkGeocode: false, placeholder: %s }).addTo(map); }"
            % json.dumps(s["search_placeholder"], ensure_ascii=False)
        )

    if options.get("minimap"):
        outils_js += (
            "\n        if (typeof L.Control.MiniMap !== 'undefined') { "
            "var miniLayer = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png'); "
            "new L.Control.MiniMap(miniLayer, { toggleDisplay: true, minimized: false }).addTo(map); }"
        )

    if options.get("imprimer"):
        # Bouton d'impression natif Leaflet.Control (pas de dépendance externe
        # — fiable à 100%)
        outils_js += (
            "\n        var PrintControl = L.Control.extend({ options: { position: 'topleft' }, "
            "onAdd: function() { var c = L.DomUtil.create('div', 'leaflet-bar leaflet-control'); "
            "var btn = L.DomUtil.create('a', '', c); btn.innerHTML = '🖨️'; btn.href = '#'; "
            "btn.title = %s; L.DomEvent.on(btn, 'click', function(e) { "
            "L.DomEvent.stop(e); window.print(); }); return c; } }); map.addControl(new PrintControl());"
            % json.dumps(s["print_title"], ensure_ascii=False)
        )

    if options.get("mousepos"):
        outils_js += (
            "\n        map.on('mousemove', function(e) { var el = document.getElementById('mouse-pos'); "
            "if (el) el.textContent = 'Lat: ' + e.latlng.lat.toFixed(5) + "
            "'  Lng: ' + e.latlng.lng.toFixed(5); });"
        )

    return outils_js


def render_app_js(export_data, url_fond, options, output_path, locale=None):
    """Charge templates/app.js, remplace les marqueurs par les valeurs de cet export,
    et écrit le résultat dans output_path. `locale` ('fr'/'en') détermine la langue
    de l'interface de la carte exportée ; si None, elle est déduite de la langue
    actuelle de QGIS."""
    with open(os.path.join(TEMPLATES_DIR, "app.js"), "r", encoding="utf-8") as f:
        contenu = f.read()

    meta_couches_json = json.dumps(export_data, ensure_ascii=False)
    meta_couches_escaped = meta_couches_json.replace("\\", "\\\\").replace("'", "\\'")

    s = get_strings(locale)
    i18n_json = json.dumps(s, ensure_ascii=False)
    i18n_escaped = i18n_json.replace("\\", "\\\\").replace("'", "\\'")

    outils_js = build_outils_js(options, locale)

    contenu = contenu.replace("__META_COUCHES_JSON__", meta_couches_escaped)
    contenu = contenu.replace("__I18N_JSON__", i18n_escaped)
    contenu = contenu.replace("__URL_FOND__", url_fond)
    contenu = contenu.replace("__OUTILS_JS__", outils_js)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(contenu)

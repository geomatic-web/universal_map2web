# -*- coding: utf-8 -*-
import json
import os

from .web_i18n import get_strings

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")

# (clé d'option du dialogue, lib CSS, lib JS) pour chaque outil optionnel

_LIBS_CDN = {
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

    extra_css = _CLUSTER_CSS
    extra_js = _CLUSTER_JS
    for cle, libs in _LIBS_CDN.items():
        if options.get(cle):
            extra_css += libs["css"]
            extra_js += libs["js"]
    return extra_css, extra_js


def build_outils_js(options, locale=None):

    s = get_strings(locale)
    outils_js = ""

    if options.get("attribution", True):
        # Lien HTML actif vers ton site web officiel
        attribution_html = (
            '<a href="https://leafletjs.com" target="_blank">Leaflet</a> | '
            '<a href="https://geomatic-web.github.io/universal_map2web/" target="_blank" rel="noopener">Universal Map2web</a>'
        )
        outils_js += (
            f"\n        map.attributionControl.setPrefix('{attribution_html}');"
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

        outils_js += "\n        map.addControl(new MeasureControl());"

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
            "var geocodeurRecherche = L.Control.geocoder({ defaultMarkGeocode: false, placeholder: %s }).addTo(map); "
            "geocodeurRecherche.on('markgeocode', function(e) { "
            "var bbox = e.geocode.bbox; "
            "if (bbox) { map.fitBounds(bbox); } else { map.setView(e.geocode.center, 14); } "
            "L.marker(e.geocode.center).addTo(map).bindPopup(e.geocode.name).openPopup(); "
            "}); }" % json.dumps(s["search_placeholder"], ensure_ascii=False)
        )

    if options.get("minimap"):
        outils_js += (
            "\n        if (typeof L.Control.MiniMap !== 'undefined') { "
            "var miniLayer = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png'); "
            "new L.Control.MiniMap(miniLayer, { toggleDisplay: true, minimized: false }).addTo(map); }"
        )

    if options.get("imprimer"):
        # Bouton d'impression natif Leaflet.Control (pas de dépendance externe
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


def render_app_js(
    export_data, url_fond, options, output_path, locale=None, wms_layers=None
):

    with open(os.path.join(TEMPLATES_DIR, "app.js"), "r", encoding="utf-8") as f:
        contenu = f.read()

    meta_couches_json = json.dumps(export_data, ensure_ascii=False)
    meta_couches_escaped = meta_couches_json.replace("\\", "\\\\").replace("'", "\\'")

    s = get_strings(locale)
    i18n_json = json.dumps(s, ensure_ascii=False)
    i18n_escaped = i18n_json.replace("\\", "\\\\").replace("'", "\\'")

    outils_js = build_outils_js(options, locale)

    wms_layers_json = json.dumps(wms_layers or {}, ensure_ascii=False)
    wms_layers_escaped = wms_layers_json.replace("\\", "\\\\").replace("'", "\\'")

    contenu = contenu.replace("__META_COUCHES_JSON__", meta_couches_escaped)
    contenu = contenu.replace("__I18N_JSON__", i18n_escaped)
    contenu = contenu.replace("__URL_FOND__", url_fond)
    contenu = contenu.replace("__OUTILS_JS__", outils_js)
    contenu = contenu.replace("__WMS_LAYERS_JSON__", wms_layers_escaped)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(contenu)

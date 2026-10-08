# -*- coding: utf-8 -*-
"""
web_i18n.py — Chaînes de texte de l'interface de la carte EXPORTÉE (le HTML/JS
généré dans le dossier de sortie), séparées de la traduction du plugin QGIS
lui-même (qui passe par i18n/*.qm + QTranslator).

Ce module est indépendant du mécanisme Qt : les fichiers exportés sont de
simples fichiers statiques (HTML/CSS/JS) ouverts dans un navigateur, sans
accès à QTranslator. On fournit donc ici notre propre petit dictionnaire de
traduction FR/EN, choisi une fois au moment de l'export selon la langue
actuelle de QGIS.
"""

from qgis.PyQt.QtCore import QSettings

STRINGS = {
    "fr": {
        "html_lang": "fr",
        "toggle_sidebar_title": "Afficher / masquer le panneau",
        "base_configured": "Base configurée",
        "layers_control_title": "Calques",
        "layer_osm_label": "Carte OSM",
        "layer_sat_label": "Image satellite",
        "legend_title": "Légende &amp; Couches",
        "expand_all": "▾ Tout déplier",
        "collapse_all": "▸ Tout replier",
        "filter_title": "🔎 Filtre par attribut",
        "filter_layer_label": "Couche",
        "filter_choose_layer": "-- Choisir une couche --",
        "filter_field_label": "Champ",
        "filter_choose_field": "-- Choisir un champ --",
        "filter_operator_label": "Opérateur",
        "filter_value_label": "Valeur",
        "op_eq": "= (égal à)",
        "op_neq": "≠ (différent de)",
        "op_contains": "⊃ contient",
        "op_starts": "commence par",
        "op_gt": "&gt; (supérieur à)",
        "op_lt": "&lt; (inférieur à)",
        "op_gte": "≥ (supérieur ou égal)",
        "op_lte": "≤ (inférieur ou égal)",
        "filter_value_placeholder": "Saisir ou cliquer une valeur...",
        "apply": "✔ Appliquer",
        "reset": "✖ Réinitialiser",
        # app.js runtime strings
        "collapse_toggle_title": "Replier / déplier",
        "cluster_points_label": "Regrouper les points (cluster)",
        "no_entity_found": "⚠ Aucune entité trouvée.",
        "choose_layer_and_field": "⚠ Choisissez une couche et un champ.",
        "data_not_loaded": "⚠ Données non encore chargées.",
        "entities_found_prefix": "entité(s) trouvée(s) sur",
        "entities_highlighted_suffix": "— sélectionnée(s) en surbrillance sur la carte.",
        # Leaflet control tools
        "my_position": "Ma position",
        "measure_title": "Mesurer une distance",
        "measure_total_label": "Distance totale",
        "measure_area_title": "Mesurer une superficie",
        "measure_area_label": "Superficie",
        "measure_clear_title": "Effacer la mesure",
        "layer_load_error": "Impossible de charger cette couche (serveur injoignable ou bloqué par CORS).",
        "attr_table_btn_title": "Ouvrir la table attributaire",
        "zoom_layer_title": "Zoom sur la couche",
        "attr_table_title": "Table attributaire",
        "attr_table_instructions": "Survolez une ligne pour repérer l'objet sur la carte. Maintenez Ctrl en même temps pour zoomer dessus (ou cliquez la ligne).",
        "attr_table_export": "Exporter en CSV",
        "attr_table_close": "Fermer",
        "attr_table_search_ph": "Rechercher dans toutes les colonnes...",
        "attr_table_filter_ph": "Filtrer...",
        "attr_table_objects": "objet(s)",
        "attr_table_empty": "Aucune donnée.",
        "attr_table_prev": "Précédent",
        "attr_table_next": "Suivant",
        "attr_table_of": "sur",
        "fullscreen_title": "Plein écran",
        "fullscreen_cancel": "Quitter",
        "search_placeholder": "Rechercher une adresse...",
        "print_title": "Imprimer la carte",
    },
    "en": {
        "html_lang": "en",
        "toggle_sidebar_title": "Show / hide panel",
        "base_configured": "Configured basemap",
        "layers_control_title": "Layers",
        "layer_osm_label": "OSM Map",
        "layer_sat_label": "Satellite imagery",
        "legend_title": "Legend &amp; Layers",
        "expand_all": "▾ Expand all",
        "collapse_all": "▸ Collapse all",
        "filter_title": "🔎 Attribute filter",
        "filter_layer_label": "Layer",
        "filter_choose_layer": "-- Choose a layer --",
        "filter_field_label": "Field",
        "filter_choose_field": "-- Choose a field --",
        "filter_operator_label": "Operator",
        "filter_value_label": "Value",
        "op_eq": "= (equal to)",
        "op_neq": "≠ (different from)",
        "op_contains": "⊃ contains",
        "op_starts": "starts with",
        "op_gt": "&gt; (greater than)",
        "op_lt": "&lt; (less than)",
        "op_gte": "≥ (greater or equal)",
        "op_lte": "≤ (less or equal)",
        "filter_value_placeholder": "Type or click a value...",
        "apply": "✔ Apply",
        "reset": "✖ Reset",
        # app.js runtime strings
        "collapse_toggle_title": "Collapse / expand",
        "cluster_points_label": "Cluster points",
        "no_entity_found": "⚠ No feature found.",
        "choose_layer_and_field": "⚠ Choose a layer and a field.",
        "data_not_loaded": "⚠ Data not loaded yet.",
        "entities_found_prefix": "feature(s) found out of",
        "entities_highlighted_suffix": "— highlighted on the map.",
        # Leaflet control tools
        "my_position": "My location",
        "measure_title": "Measure a distance",
        "measure_total_label": "Total distance",
        "measure_area_title": "Measure an area",
        "measure_area_label": "Area",
        "measure_clear_title": "Clear measurement",
        "layer_load_error": "Could not load this layer (server unreachable or blocked by CORS).",
        "attr_table_btn_title": "Open attribute table",
        "zoom_layer_title": "Zoom to layer",
        "attr_table_title": "Attribute table",
        "attr_table_instructions": "Hover a row to locate the feature on the map. Hold Ctrl at the same time to zoom to it (or click the row).",
        "attr_table_export": "Export to CSV",
        "attr_table_close": "Close",
        "attr_table_search_ph": "Search all columns...",
        "attr_table_filter_ph": "Filter...",
        "attr_table_objects": "feature(s)",
        "attr_table_empty": "No data.",
        "attr_table_prev": "Previous",
        "attr_table_next": "Next",
        "attr_table_of": "of",
        "fullscreen_title": "Full screen",
        "fullscreen_cancel": "Exit",
        "search_placeholder": "Search an address...",
        "print_title": "Print the map",
    },
}


def get_locale():
    """Détecte 'fr' ou 'en' à partir de la langue actuelle de QGIS
    (même logique que UniversalMap2web.load_translation)."""
    settings = QSettings()
    locale = settings.value("locale/userLocale", "en_US")
    if locale:
        locale = locale.split(".")[0]
    return "fr" if locale and locale.startswith("fr") else "en"


def get_strings(locale=None):
    """Retourne le dictionnaire de chaînes pour la langue donnée (ou la
    langue actuelle de QGIS si non précisée)."""
    if locale is None:
        locale = get_locale()
    return STRINGS.get(locale, STRINGS["en"])

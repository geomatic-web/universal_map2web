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
        "fullscreen_title": "Plein écran",
        "fullscreen_cancel": "Quitter",
        "search_placeholder": "Rechercher une adresse...",
        "print_title": "Imprimer la carte",
    },
    "en": {
        "html_lang": "en",
        "toggle_sidebar_title": "Show / hide panel",
        "base_configured": "Configured basemap",
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

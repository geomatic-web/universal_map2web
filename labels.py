# -*- coding: utf-8 -*-
"""
labels.py — Extraction de la configuration d'étiquetage (labeling) QGIS d'une couche,
pour reproduire l'affichage des étiquettes côté Leaflet (tooltips permanents).
"""

import logging

logger = logging.getLogger(__name__)


def extraire_etiquettes(layer):
    """
    Extrait la configuration d'étiquetage QGIS (labeling) d'une couche,
    si l'étiquetage est activé. Retourne un dict exploitable côté Leaflet
    (champ à afficher, taille, couleur, police) ou None si pas d'étiquette.
    """
    try:
        if not layer.labelsEnabled():
            return None
        labeling = layer.labeling()
        if not labeling:
            return None

        # On essaie de lire les paramètres du premier "settings" disponible
        settings = None
        try:
            settings = labeling.settings()
        except Exception:
            # Rule-based labeling : on prend la première règle
            try:
                root = labeling.rootRule()
                enfants = root.children()
                if enfants:
                    settings = enfants[0].settings()
            except Exception:
                settings = None

        if not settings:
            return None

        champ_label = settings.fieldName
        text_format = settings.format()
        couleur = "#000000"
        taille = 10
        try:
            c = text_format.color()
            if c.isValid():
                couleur = c.name()
            taille = text_format.size()
            if taille <= 0:
                taille = 10
        except Exception as exc:
            logger.debug("Impossible de lire le format du texte de l'étiquette : %s", exc)

        return {
            "champ": champ_label,
            "couleur": couleur,
            # conversion approx pt -> px lisible web
            "taille": round(taille * 1.4, 1),
        }
    except Exception:
        return None

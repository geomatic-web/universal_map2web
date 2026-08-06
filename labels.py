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
    (champ, taille, couleur, police, tampon/buffer) ou None si pas d'étiquette.
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
        police = "sans-serif"

        # Données par défaut pour le tampon (Buffer)
        tampon_actif = False
        tampon_couleur = "#ffffff"
        tampon_taille = 1.0

        try:
            c = text_format.color()
            if c.isValid():
                couleur = c.name()
            taille = text_format.size()
            if taille <= 0:
                taille = 10

            # Police de caractères
            font = text_format.font()
            if font and font.family():
                police = font.family()

            # Extraction du Tampon (Buffer)
            buffer_settings = text_format.buffer()
            if buffer_settings and buffer_settings.enabled():
                tampon_actif = True
                bc = buffer_settings.color()
                if bc.isValid():
                    tampon_couleur = bc.name()

                # Taille du tampon ramenée à une valeur propre pour le CSS web
                sz = buffer_settings.size()
                tampon_taille = round(sz, 1) if sz > 0 else 1.0

        except Exception as exc:
            logger.debug(
                "Impossible de lire le format du texte de l'étiquette : %s",
                exc,
            )

        return {
            "champ": champ_label,
            "couleur": couleur,
            # conversion approx pt -> px lisible web
            "taille": round(taille * 1.4, 1),
            "police": police,
            "tampon_actif": tampon_actif,
            "tampon_couleur": tampon_couleur,
            "tampon_taille": tampon_taille,
        }
    except Exception:
        return None

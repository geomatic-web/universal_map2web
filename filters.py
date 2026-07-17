# -*- coding: utf-8 -*-
"""
filters.py — Logique côté Python liée au filtre par attribut de la carte exportée.

Le filtre interactif lui-même (sélection couche/champ/opérateur/valeur, mise en
surbrillance des entités trouvées) s'exécute côté client dans templates/app.js,
car il doit réagir instantanément sans recharger la page. Ce module ne contient
que les éléments préparés côté QGIS pour alimenter ce filtre : la liste des
opérateurs supportés (tenue synchronisée avec le menu déroulant HTML) et le
calcul des champs réellement filtrables d'une couche.
"""

# Doit rester synchronisé avec les <option> de #filtre-operateur dans
# templates/index.html et le switch() de appliquerFiltre() dans
# templates/app.js.
OPERATEURS_FILTRE = [
    ("eq", "= (égal à)"),
    ("neq", "≠ (différent de)"),
    ("contains", "⊃ contient"),
    ("starts", "commence par"),
    ("gt", "> (supérieur à)"),
    ("lt", "< (inférieur à)"),
    ("gte", "≥ (supérieur ou égal)"),
    ("lte", "≤ (inférieur ou égal)"),
]


def get_filterable_fields(popup_fields):
    """Retourne les champs réellement proposables dans le filtre (exclut les champs
    techniques internes préfixés par '_qgis_' injectés dans le GeoJSON)."""
    return [champ for champ in (popup_fields or []) if not champ.startswith("_qgis_")]

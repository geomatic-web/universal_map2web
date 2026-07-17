# -*- coding: utf-8 -*-
"""
__init__.py — Point de chargement standard d'un plugin QGIS.
QGIS appelle classFactory(iface) pour instancier le plugin.
"""


def classFactory(iface):
    from .universal_map2web import UniversalMap2web

    return UniversalMap2web(iface)

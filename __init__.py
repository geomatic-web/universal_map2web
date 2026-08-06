# -*- coding: utf-8 -*-
"""
__init__.py — Point de chargement standard d'un plugin QGIS.
"""


def classFactory(iface):
    from .universal_map2web import UniversalMap2web

    return UniversalMap2web(iface)

# -*- coding: utf-8 -*-
"""
qt_compat.py — Compatibilité des enums Qt/QGIS entre les vieux bindings
PyQt5 (ex: QGIS 3.0.0, où les enums s'utilisent "à plat", comme Qt.Checked)
et les bindings récents PyQt5/PyQt6 (où la forme "scopée" est requise,
comme Qt.CheckState.Checked).

Utilisation :
    from .qt_compat import qenum
    qenum(Qt, "CheckState", "Checked")        # -> Qt.CheckState.Checked ou Qt.Checked
    qenum(QDialogButtonBox, "StandardButton", "Ok")
    qenum(QgsMapLayer, "LayerType", "VectorLayer")
"""


def qenum(owner, scoped_name, flat_name):
    """Retourne la valeur d'un enum Qt/QGIS, quelle que soit la version.

    Essaie d'abord `owner.scoped_name.flat_name` (style PyQt6 / PyQt5 récent),
    puis retombe sur `owner.flat_name` (style PyQt5 ancien) si besoin.
    """
    scoped_owner = getattr(owner, scoped_name, None)
    value = getattr(scoped_owner, flat_name, None) if scoped_owner is not None else None
    if value is None:
        value = getattr(owner, flat_name)
    return value

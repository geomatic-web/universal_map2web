# -*- coding: utf-8 -*-
def qenum(owner, scoped_name, flat_name):
    """Retourne la valeur d'un enum Qt/QGIS, quelle que soit la version."""
    scoped_owner = getattr(owner, scoped_name, None)
    value = getattr(scoped_owner, flat_name, None) if scoped_owner is not None else None
    if value is None:
        value = getattr(owner, flat_name)
    return value

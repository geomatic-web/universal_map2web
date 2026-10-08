# -*- coding: utf-8 -*-
"""
ogc_live_source.py — Support du chargement EN DIRECT (live) depuis des
services OGC WFS (vecteur) et WMS (raster), en complément de l'export
GeoJSON statique et du mode dynamique PostgreSQL.
"""

from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

from qgis.core import QgsDataSourceUri, QgsMapLayer

from .qt_compat import qenum


def est_couche_wfs(layer):
    """Retourne True si la couche QGIS est une couche vecteur connectée à un service WFS."""
    try:
        return (
            layer.type() == qenum(QgsMapLayer, "LayerType", "VectorLayer")
            and layer.providerType().upper() == "WFS"
        )
    except Exception:
        return False


def extraire_config_wfs(layer):
    """Extrait les paramètres de connexion d'une couche WFS QGIS (QgsDataSourceUri)."""
    uri = QgsDataSourceUri(layer.source())
    return {
        "url": uri.param("url") or uri.param("URL") or "",
        "typename": uri.param("typename") or uri.param("TYPENAME") or layer.name(),
        "srsname": uri.param("srsname") or uri.param("SRSNAME") or "EPSG:4326",
        "version": uri.param("version") or uri.param("VERSION") or "2.0.0",
    }


def construire_url_wfs_live(config):

    base_url = (config.get("url") or "").strip()
    if not base_url:
        return ""

    parties = urlsplit(base_url)
    base_sans_requete = urlunsplit(
        (parties.scheme, parties.netloc, parties.path, "", "")
    )

    version = (config.get("version") or "").strip()
    if not version or version.lower() == "auto":
        version = "2.0.0"

    params = {
        "service": "WFS",
        "version": version,
        "request": "GetFeature",
        "typeName": config.get("typename") or "",
        "outputFormat": "application/json",
        "srsName": config.get("srsname") or "EPSG:4326",
    }
    return base_sans_requete + "?" + urlencode(params)


FORMATS_IMAGE_OK = ("image/png", "image/png8", "image/jpeg", "image/gif", "image/webp")


def _format_image_valide(fmt):
    """Ne garde qu'un vrai format d'image (ex. rejette application/openlayers,
    format de la page d'aperçu GeoServer qui renvoie du HTML)."""
    fmt = (fmt or "").strip().lower()
    return fmt if fmt in FORMATS_IMAGE_OK else "image/png"


def est_couche_wms(layer):
    """Retourne True si la couche QGIS est une couche raster connectée à un vrai
    service WMS (distingué d'un flux de tuiles XYZ, qui partage le même
    providerType "wms" dans QGIS mais n'a pas de paramètre "layers")."""
    try:
        if (
            layer.type() != qenum(QgsMapLayer, "LayerType", "RasterLayer")
            or layer.providerType() != "wms"
        ):
            return False
        params = parse_qs(layer.source())
        return "layers" in params
    except Exception:
        return False


def extraire_config_wms(layer):
    """Extrait les paramètres d'une couche WMS QGIS (source au format clé=valeur&...)."""
    params = parse_qs(layer.source())

    def _get(cle, defaut=""):
        return params.get(cle, [defaut])[0]

    transparent_brut = _get("transparent", "true").lower()
    format_image = _format_image_valide(_get("format", "image/png"))
    parties = urlsplit(_get("url"))
    url_propre = urlunsplit((parties.scheme, parties.netloc, parties.path, "", ""))
    return {
        "nom": layer.name(),
        "url": url_propre,
        "layers": _get("layers"),
        "format": format_image,
        "transparent": transparent_brut in ("1", "true", "yes")
        and format_image != "image/jpeg",
        "version": _get("version", "1.3.0"),
        "styles": _get("styles", ""),
        "crs": _get("crs") or _get("srs") or "EPSG:3857",
        "opacite_defaut": float(_get("opacity", "1") or 1),
    }

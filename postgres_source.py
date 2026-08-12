# -*- coding: utf-8 -*-
"""
postgres_source.py — Support du chargement dynamique des données depuis
PostgreSQL/PostGIS en complément de l'export GeoJSON statique.

Principe:
    - Seules les couches déjà connectées à PostGIS dans QGIS sont éligibles
      (aucune ressaisie d'identifiants dans le plugin : on relit ceux de la
      couche via QgsDataSourceUri).
    - La clé API est générée aléatoirement à chaque export (secrets.token_urlsafe).
    - Le nom de couche utilisé comme clé (identique à clean_filename(layer.name()))
      est une valeur interne fixée à l'export, jamais une entrée utilisateur au
      runtime : pas de risque d'injection SQL par ce biais côté get_data.php.
"""

import os
import secrets

from qgis.core import QgsDataSourceUri

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")


def est_couche_postgres(layer):
    """Retourne True si la couche QGIS est déjà connectée à une base PostgreSQL/PostGIS."""
    try:
        return layer.providerType() == "postgres"
    except Exception:
        return False


def extraire_config_postgres(layer):
    """Extrait les paramètres de connexion d'une couche PostGIS QGIS (QgsDataSourceUri)."""
    uri = QgsDataSourceUri(layer.source())
    return {
        "host": uri.host() or "localhost",
        "port": uri.port() or "5432",
        "dbname": uri.database(),
        "user": uri.username(),
        "pass": uri.password(),
        "schema": uri.schema() or "public",
        "table": uri.table(),
        "geom_col": uri.geometryColumn() or "geom",
    }


def generer_cle_api():
    """Génère une clé API aléatoire pour protéger get_data.php d'un accès non voulu."""
    return secrets.token_urlsafe(24)


def _php_str(valeur):
    """Échappe une valeur pour l'insérer dans une chaîne PHP entre apostrophes simples."""
    if valeur is None:
        valeur = ""
    valeur = str(valeur)
    return valeur.replace("\\", "\\\\").replace("'", "\\'")


def _construire_db_config_php(configs_par_couche, api_key):
    """Construit le contenu de db_config.php : clé API + dict PHP des connexions par couche."""
    lignes = [
        "<?php",
        "// db_config.php — généré par Universal Map2web",
        "// Protégé par .htaccess : ne jamais rendre ce fichier accessible directement",
        "",
    ]
    lignes.append(f"define('API_KEY', '{_php_str(api_key)}');")
    lignes.append("")
    lignes.append("$LAYERS_CONFIG = [")
    for nom_couche, cfg in configs_par_couche.items():
        lignes.append(f"    '{_php_str(nom_couche)}' => [")
        lignes.append(f"        'host'     => '{_php_str(cfg['host'])}',")
        lignes.append(f"        'port'     => '{_php_str(cfg['port'])}',")
        lignes.append(f"        'dbname'   => '{_php_str(cfg['dbname'])}',")
        lignes.append(f"        'user'     => '{_php_str(cfg['user'])}',")
        lignes.append(f"        'pass'     => '{_php_str(cfg['pass'])}',")
        lignes.append(f"        'schema'   => '{_php_str(cfg['schema'])}',")
        lignes.append(f"        'table'    => '{_php_str(cfg['table'])}',")
        lignes.append(f"        'geom_col' => '{_php_str(cfg['geom_col'])}',")
        lignes.append("    ],")
    lignes.append("];")
    lignes.append("")
    return "\n".join(lignes)


def generer_fichiers_postgres(output_dir, configs_par_couche, api_key):
    """Écrit db_config.php, .htaccess et get_data.php dans le dossier d'export.
    `configs_par_couche` est un dict {nom_fichier_couche: config_connexion}."""

    with open(os.path.join(output_dir, "db_config.php"), "w", encoding="utf-8") as f:
        f.write(_construire_db_config_php(configs_par_couche, api_key))

    with open(os.path.join(TEMPLATES_DIR, "get_data.php"), "r", encoding="utf-8") as f:
        get_data_php = f.read()
    with open(os.path.join(output_dir, "get_data.php"), "w", encoding="utf-8") as f:
        f.write(get_data_php)

    with open(
        os.path.join(TEMPLATES_DIR, "postgres.htaccess"), "r", encoding="utf-8"
    ) as f:
        htaccess = f.read()
    with open(os.path.join(output_dir, ".htaccess"), "w", encoding="utf-8") as f:
        f.write(htaccess)

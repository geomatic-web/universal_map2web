# -*- coding: utf-8 -*-

import os
import socket
import socketserver
import threading
import webbrowser
import http.server
import json
from datetime import datetime

from qgis.PyQt import QtCore
from qgis.PyQt.QtCore import Qt, QSettings, QCoreApplication
from qgis.PyQt.QtWidgets import QFileDialog, QMessageBox, QProgressDialog
from qgis.core import Qgis, QgsMapLayer, QgsProject, QgsWkbTypes

from . import html_generator
from .geojson import layer_to_geojson
from .labels import extraire_etiquettes
from .legend import extraire_icones_symbologie
from .postgres_source import (
    est_couche_postgres,
    extraire_config_postgres,
    generer_cle_api,
    generer_fichiers_postgres,
)
from .styles import construire_carte_styles_renderer
from .utils import clean_filename, get_geometry_type
from .qt_compat import qenum


class Exporter:
    def __init__(self, iface):
        self.iface = iface
        self.settings = QSettings()
        self.export_data = {}
        self.output_dir = None
        self.styles_dir = None

    def tr(self, text):
        """Traduit un texte"""
        return QCoreApplication.translate("UniversalMap2web", text)

    def exporter(self, dialog):
        self.export_data.clear()
        couches_a_exporter = []

        for i in range(dialog.listCouches.count()):
            item = dialog.listCouches.item(i)
            if item.checkState() == qenum(Qt, "CheckState", "Checked"):
                layer_id = item.data(qenum(Qt, "ItemDataRole", "UserRole"))
                layer = QgsProject.instance().mapLayer(layer_id)
                if layer and layer.type() == qenum(
                    QgsMapLayer, "LayerType", "VectorLayer"
                ):
                    couches_a_exporter.append(layer)

        if not couches_a_exporter:
            QMessageBox.warning(
                dialog,
                self.tr("No layer"),
                self.tr("Please select at least one layer."),
            )
            return

        last_dir = self.settings.value("UniversalMap2web/last_dir", "")
        output_dir = QFileDialog.getExistingDirectory(
            dialog, self.tr("Choose export folder"), last_dir
        )
        if not output_dir:
            return

        self.settings.setValue("UniversalMap2web/last_dir", output_dir)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_dir = os.path.join(output_dir, f"map2web_{timestamp}")
        self.styles_dir = os.path.join(self.output_dir, "styles_images")
        os.makedirs(self.output_dir, exist_ok=True)

        try:
            data_dir = os.path.join(self.output_dir, "data")
            os.makedirs(data_dir, exist_ok=True)

            progress = QProgressDialog(
                self.tr("Generating styles and geometries..."),
                self.tr("Cancel"),
                0,
                len(couches_a_exporter),
                dialog,
            )
            progress.setWindowModality(
                qenum(Qt, "WindowModality", "WindowModal")
            )

            postgres_dynamique = getattr(dialog, "chkPostgresDynamique", None)
            postgres_dynamique = (
                postgres_dynamique.isChecked() if postgres_dynamique else False
            )
            # nom_fichier -> config connexion, pour les couches en mode
            # dynamique
            configs_postgres = {}

            for i, layer in enumerate(couches_a_exporter):
                if progress.wasCanceled():
                    break
                progress.setValue(i)
                progress.setLabelText(
                    f"{self.tr('Extracting styles')} : {layer.name()}"
                )
                QtCore.QCoreApplication.processEvents()

                nom_fichier = clean_filename(layer.name())
                legend_icons = extraire_icones_symbologie(
                    layer, nom_fichier, self.styles_dir
                )
                popup_fields = dialog.popup_config.get(
                    layer.id(), [f.name() for f in layer.fields()]
                )
                etiquette = extraire_etiquettes(layer)

                renderer = layer.renderer()
                attr_classif = (
                    renderer.classAttribute()
                    if hasattr(renderer, "classAttribute")
                    else None
                )

                couche_en_pg_dynamique = (
                    postgres_dynamique and est_couche_postgres(layer)
                )

                if couche_en_pg_dynamique:
                    # Pas de dump GeoJSON : la page web ira chercher les données en
                    # direct via get_data.php. On calcule uniquement la petite table
                    # de correspondance valeur->style (issue du renderer QGIS) pour
                    # que le JS puisse reproduire le style par entité côté
                    # client.
                    carte_styles, style_defaut = (
                        construire_carte_styles_renderer(
                            renderer, layer.geometryType()
                        )
                    )
                    configs_postgres[nom_fichier] = extraire_config_postgres(
                        layer
                    )
                    # La clé API n'est connue qu'après la boucle (générée une seule
                    # fois pour tout l'export) : on la substitue ensuite.
                    reference_fichier = (
                        f"get_data.php?layer={nom_fichier}&key=__API_KEY__"
                    )
                else:
                    geojson_data = layer_to_geojson(layer, popup_fields)
                    chemin_geojson = os.path.join(
                        data_dir, f"{nom_fichier}.geojson"
                    )
                    with open(chemin_geojson, "w", encoding="utf-8") as f:
                        json.dump(geojson_data, f, indent=2)
                    reference_fichier = f"data/{nom_fichier}.geojson"
                    carte_styles, style_defaut = None, None

                self.export_data[layer.name()] = {
                    "fichier": reference_fichier,
                    "source": (
                        "postgres" if couche_en_pg_dynamique else "geojson"
                    ),
                    "style_map": carte_styles,
                    "style_defaut": style_defaut,
                    "geom_type": get_geometry_type(layer),
                    "popup_fields": popup_fields,
                    "legend_style": legend_icons,
                    "is_polygon": (
                        layer.geometryType()
                        == qenum(
                            QgsWkbTypes, "GeometryType", "PolygonGeometry"
                        )
                    ),
                    "is_line": (
                        layer.geometryType()
                        == qenum(QgsWkbTypes, "GeometryType", "LineGeometry")
                    ),
                    "is_point": (
                        layer.geometryType()
                        == qenum(QgsWkbTypes, "GeometryType", "PointGeometry")
                    ),
                    "etiquette": etiquette,
                    "attr_classif": attr_classif,
                }

            progress.setValue(len(couches_a_exporter))

            if configs_postgres:
                api_key = generer_cle_api()
                generer_fichiers_postgres(
                    self.output_dir, configs_postgres, api_key
                )
                for info in self.export_data.values():
                    if info.get("source") == "postgres":
                        info["fichier"] = info["fichier"].replace(
                            "__API_KEY__", api_key
                        )

            html_generator.generer_export(
                dialog, self.export_data, self.output_dir
            )

            if configs_postgres:
                QMessageBox.information(
                    dialog,
                    self.tr("PostgreSQL mode"),
                    self.tr(
                        "This export includes layers loaded dynamically from "
                        "PostgreSQL. It requires a hosting environment with PHP "
                        "and Apache active (with .htaccess support). It will NOT "
                        "work when opened locally, on GitHub Pages, or any static "
                        "hosting. Please deploy the exported folder to a "
                        "PHP-capable server."
                    ),
                )

            if dialog.chkOuvrirNavigateur.isChecked() and not configs_postgres:
                # Le serveur local (http.server) ne sait pas exécuter PHP : on
                # n'ouvre pas automatiquement le navigateur en mode PostgreSQL.
                self.demarrer_serveur_local(self.output_dir)

            message = "{} : {}".format(
                self.tr("Web map exported successfully to"), self.output_dir
            )
            self.iface.messageBar().pushMessage(
                self.tr("Success"),
                message,
                level=qenum(Qgis, "MessageLevel", "Success"),
                duration=5,
            )

        except Exception as e:
            message = f"{self.tr('An error occurred')} :\n{str(e)}"
            QMessageBox.critical(dialog, self.tr("Error"), message)

    def demarrer_serveur_local(self, dossier, port=8000):
        """
        Lance un serveur HTTP local dans un thread démon, servant le dossier d'export.
        Compatible Python 3.6 (QGIS 3.0) et Python 3.7+ / 3.12+ (QGIS 3.34+ / 3.40+).
        """
        port_choisi = port
        for _tentative in range(20):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.2)
                if s.connect_ex(("localhost", port_choisi)) != 0:
                    break  # port libre
                port_choisi += 1
        else:
            html_path = os.path.join(dossier, "index.html")
            webbrowser.open(f"file://{html_path}")
            return

        class SafeHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                # Utilise 'directory' pour Python 3.7+ (QGIS 3.34 / 3.40)
                kwargs["directory"] = dossier
                try:
                    super().__init__(*args, **kwargs)
                except TypeError:
                    # Fallback pour Python 3.6 (QGIS 3.0) si 'directory' n'est pas supporté en kwarg
                    kwargs.pop("directory", None)
                    super().__init__(*args, **kwargs)

            def translate_path(self, path):
                # Redirection explicite vers le dossier d'exportation
                path_clean = path.split("?", 1)[0].split("#", 1)[0]
                relpath = path_clean.lstrip("/")
                if not relpath or relpath == "/":
                    relpath = "index.html"
                return os.path.join(dossier, relpath)

            def log_message(self, format, *args):
                pass  # Désactive les logs dans la console QGIS

        def lancer():
            socketserver.TCPServer.allow_reuse_address = True
            try:
                with socketserver.TCPServer(
                    ("localhost", port_choisi), SafeHTTPRequestHandler
                ) as httpd:
                    httpd.serve_forever()
            except Exception as e:
                print(f"Erreur Serveur HTTP: {e}")

        thread = threading.Thread(target=lancer, daemon=True)
        thread.start()

        webbrowser.open(f"http://localhost:{port_choisi}/index.html")
        pass

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
from .utils import clean_filename, get_geometry_type


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
            if item.checkState() == Qt.CheckState.Checked:
                layer_id = item.data(Qt.ItemDataRole.UserRole)
                layer = QgsProject.instance().mapLayer(layer_id)
                if layer and layer.type() == QgsMapLayer.VectorLayer:
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
            progress.setWindowModality(Qt.WindowModality.WindowModal)

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
                geojson_data = layer_to_geojson(layer, popup_fields)
                etiquette = extraire_etiquettes(layer)

                chemin_geojson = os.path.join(data_dir, f"{nom_fichier}.geojson")
                with open(chemin_geojson, "w", encoding="utf-8") as f:
                    json.dump(geojson_data, f, indent=2)

                renderer = layer.renderer()
                attr_classif = (
                    renderer.classAttribute()
                    if hasattr(renderer, "classAttribute")
                    else None
                )

                self.export_data[layer.name()] = {
                    "fichier": f"data/{nom_fichier}.geojson",
                    "geom_type": get_geometry_type(layer),
                    "popup_fields": popup_fields,
                    "legend_style": legend_icons,
                    "is_polygon": (layer.geometryType() == QgsWkbTypes.PolygonGeometry),
                    "is_line": (layer.geometryType() == QgsWkbTypes.LineGeometry),
                    "is_point": (layer.geometryType() == QgsWkbTypes.PointGeometry),
                    "etiquette": etiquette,
                    "attr_classif": attr_classif,
                }

            progress.setValue(len(couches_a_exporter))

            html_generator.generer_export(dialog, self.export_data, self.output_dir)

            if dialog.chkOuvrirNavigateur.isChecked():
                self.demarrer_serveur_local(self.output_dir)

            message = (
                f"{self.tr('Web map exported successfully to')} : {self.output_dir}"
            )
            self.iface.messageBar().pushMessage(
                self.tr("Success"),
                message,
                level=Qgis.Success,
                duration=5,
            )

        except Exception as e:
            message = f"{self.tr('An error occurred')} :\n{str(e)}"
            QMessageBox.critical(dialog, self.tr("Error"), message)

    def demarrer_serveur_local(self, dossier, port=8000):
        """
        Lance un serveur HTTP local (http.server) dans un thread démon, servant le
        dossier d'export, puis ouvre le navigateur sur localhost:PORT. Nécessaire
        car fetch() est bloqué par CORS en file:// dans la plupart des navigateurs.
        Si le port est occupé, on essaie les ports suivants jusqu'à en trouver un libre.
        """

        port_choisi = port
        for _tentative in range(20):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.2)
                if s.connect_ex(("localhost", port_choisi)) != 0:
                    break  # port libre
                port_choisi += 1
        else:
            # Aucun port libre trouvé — on retombe sur file:// en dernier
            # recours
            html_path = os.path.join(dossier, "index.html")
            webbrowser.open(f"file://{html_path}")
            return

        class Handler(http.server.SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=dossier, **kwargs)

            def log_message(self, format, *args):
                pass  # silence les logs dans la console QGIS

        def lancer():
            with socketserver.TCPServer(("localhost", port_choisi), Handler) as httpd:
                httpd.serve_forever()

        thread = threading.Thread(target=lancer, daemon=True)
        thread.start()

        webbrowser.open(f"http://localhost:{port_choisi}/index.html")
        pass

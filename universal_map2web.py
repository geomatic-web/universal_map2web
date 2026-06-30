# -*- coding: utf-8 -*-
"""
universal_map2web.py — Point d'entrée du plugin QGIS. Ne contient que la
mécanique d'intégration à l'interface QGIS (menu, barre d'outils, ouverture du
dialogue) ; toute la logique d'export vit dans exporter.py et les modules
géométrie/styles/légende/HTML dédiés.
"""

import os

from qgis.PyQt import QtGui
from qgis.PyQt.QtWidgets import QAction

from .exporter import Exporter
from .universal_map2web_dialog import UniversalMap2webDialog


class UniversalMap2web:
    """Classe principale de l'extension Universal Map2web — rendu fidèle à QGIS, 100 % générique"""

    def __init__(self, iface):
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.dialog = None
        self.action = None
        self.exporter = Exporter(iface)

    def initGui(self):
        icon_path = os.path.join(self.plugin_dir, "icon.png")
        self.action = QAction(
            (QtGui.QIcon(icon_path) if os.path.exists(icon_path) else QtGui.QIcon()),
            "Universal Map2web",
            self.iface.mainWindow(),
        )
        self.action.setWhatsThis(
            "Exporter les couches en carte HTML interactive")
        self.action.triggered.connect(self.run)
        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToMenu("&Universal Map2web", self.action)

    def unload(self):
        self.iface.removeToolBarIcon(self.action)
        self.iface.removePluginMenu("&Universal Map2web", self.action)

    def run(self):
        self.dialog = UniversalMap2webDialog(self.iface.mainWindow())

        if self.dialog.comboFondPlan.count() == 0:
            self.dialog.comboFondPlan.addItems(
                ["🌍 OpenStreetMap", "🛰️ Google Satellite", "🌐 Google Hybrid"]
            )

        self.dialog.chkFondPlanPersonnalise.toggled.connect(
            self.activer_fond_personnalise
        )

        if hasattr(self.dialog, "btnExporter"):
            self.dialog.btnExporter.clicked.connect(self.exporter_courant)
        elif hasattr(self.dialog, "buttonBox"):
            try:
                self.dialog.buttonBox.accepted.disconnect()
            except (TypeError, RuntimeError):
                pass  # rien n'était connecté — normal au premier lancement
            self.dialog.buttonBox.accepted.connect(self.exporter_courant)

        self.dialog.show()  # fenêtre persistante : on peut exporter plusieurs fois sans rouvrir

    def activer_fond_personnalise(self, checked):
        self.dialog.txtFondPlanURL.setEnabled(checked)

    def exporter_courant(self):
        self.exporter.exporter(self.dialog)

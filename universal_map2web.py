# -*- coding: utf-8 -*-

import os
from qgis.PyQt import QtGui
from qgis.PyQt.QtWidgets import QAction
from qgis.PyQt.QtCore import QCoreApplication, QTranslator, QSettings

from .exporter import Exporter
from .universal_map2web_dialog import UniversalMap2webDialog


class UniversalMap2web:
    """Classe principale de l'extension Universal Map2web"""

    def __init__(self, iface):
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.dialog = None
        self.action = None
        self.exporter = Exporter(iface)
        self.translator = None

        # Charger la traduction
        self.load_translation()

    def load_translation(self):
        """Charge la traduction selon la langue de QGIS"""
        settings = QSettings()
        locale = settings.value("locale/userLocale", "en_US")

        # Nettoyer le locale (enlever .UTF-8 etc.)
        if locale:
            locale = locale.split(".")[0]

        # Si la langue est française, on utilise fr_FR, sinon en_US
        if locale.startswith("fr"):
            locale = "fr_FR"
        else:
            locale = "en_US"

        print(f"Langue chargée: {locale}")

        i18n_path = os.path.join(self.plugin_dir, "i18n")
        translation_file = os.path.join(i18n_path, f"{locale}.qm")

        self.translator = QTranslator()

        if os.path.exists(translation_file):
            self.translator.load(translation_file)
            QCoreApplication.installTranslator(self.translator)
            print(f"Traduction chargée: {locale}")
            return True
        else:
            print(f"Fichier de traduction non trouvé: {translation_file}")
            # Fallback sur l'anglais
            translation_file = os.path.join(i18n_path, "en_US.qm")
            if os.path.exists(translation_file):
                self.translator.load(translation_file)
                QCoreApplication.installTranslator(self.translator)
                print("Fallback: en_US chargé")
                return True

        return False

    def tr(self, text):
        """Traduit un texte"""
        return QCoreApplication.translate("UniversalMap2web", text)

    def initGui(self):
        icon_path = os.path.join(self.plugin_dir, "icon.png")
        self.action = QAction(
            (QtGui.QIcon(icon_path) if os.path.exists(icon_path) else QtGui.QIcon()),
            self.tr("Create web map"),
            self.iface.mainWindow(),
        )
        self.action.setWhatsThis(self.tr("Export the layers in interactive HTML map"))
        self.action.triggered.connect(self.run)
        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToMenu(self.tr("&Universal Map2web"), self.action)

    def unload(self):
        if self.action:
            self.iface.removeToolBarIcon(self.action)
            self.iface.removePluginMenu(self.tr("&Universal Map2web"), self.action)

    def run(self):
        self.dialog = UniversalMap2webDialog(self.iface.mainWindow())

        if self.dialog.comboFondPlan.count() == 0:
            self.dialog.comboFondPlan.addItems(
                [
                    self.tr("OpenStreetMap"),
                    self.tr("Google Satellite"),
                    self.tr("Google Hybrid"),
                ]
            )
            for i in range(self.dialog.comboFondPlan.count()):
                item = self.dialog.comboFondPlan.itemText(i)
                if "OpenStreetMap" in item:
                    self.dialog.comboFondPlan.setItemText(i, f"🌍 {item}")
                elif "Google Satellite" in item:
                    self.dialog.comboFondPlan.setItemText(i, f"🛰️ {item}")
                elif "Google Hybrid" in item:
                    self.dialog.comboFondPlan.setItemText(i, f"🌐 {item}")

        self.dialog.chkFondPlanPersonnalise.toggled.connect(
            self.activer_fond_personnalise
        )

        if hasattr(self.dialog, "btnExporter"):
            self.dialog.btnExporter.clicked.connect(self.exporter_courant)
        elif hasattr(self.dialog, "buttonBox"):
            try:
                self.dialog.buttonBox.accepted.disconnect()
            except (TypeError, RuntimeError):
                pass
            self.dialog.buttonBox.accepted.connect(self.exporter_courant)

        self.dialog.show()

    def activer_fond_personnalise(self, checked):
        self.dialog.txtFondPlanURL.setEnabled(checked)

    def exporter_courant(self):
        self.exporter.exporter(self.dialog)

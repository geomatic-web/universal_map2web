# -*- coding: utf-8 -*-
import json
import os
from qgis.core import QgsMapLayer, QgsProject
from qgis.PyQt import QtGui, uic
from qgis.PyQt.QtCore import QCoreApplication, QSettings, Qt
from qgis.PyQt.QtWidgets import (
    QColorDialog,
    QDialog,
    QFileDialog,
    QListWidgetItem,
)

from .ogc_live_source import est_couche_wms
from .qt_compat import qenum
from .utils import journaliser

FORM_CLASS, _ = uic.loadUiType(
    os.path.join(os.path.dirname(__file__), "universal_map2web_dialog_base.ui")
)


class UniversalMap2webDialog(QDialog, FORM_CLASS):

    def __init__(self, parent=None):
        super(UniversalMap2webDialog, self).__init__(parent)
        self.setupUi(self)
        self.popup_config = {}
        self.derniere_couche_id = None

        # Appliquer les traductions de l'interface immédiatement
        self.apply_translations()

        self.btnChoisirLogo.clicked.connect(self.selectionner_logo)
        self.btnChoisirCouleur.clicked.connect(self.selectionner_couleur)
        self.btnSelectAll.clicked.connect(self.tout_selectionner)
        self.btnDeselectAll.clicked.connect(self.tout_deselectionner)
        self.btnInvertSelection.clicked.connect(self.inverser_selection)
        self.btnMoveUp.clicked.connect(self.monter_couche)
        self.btnMoveDown.clicked.connect(self.descendre_couche)
        self.listCouchesPopup.currentItemChanged.connect(self.changement_couche_popup)

        self.charger_couches_qgis()

        # Restoration de la configuration enregistrée dans le projet
        self.restaurer_configuration_projet()

    def tr(self, text):
        """Traduit un texte"""
        return QCoreApplication.translate("UniversalMap2web", text)

    def apply_translations(self):
        """Applique les traductions à tous les éléments de l'interface"""

        # Onglets
        if self.tabWidget.count() > 0:
            self.tabWidget.setTabText(0, self.tr("General"))
        if self.tabWidget.count() > 1:
            self.tabWidget.setTabText(1, self.tr("Customization"))
        if self.tabWidget.count() > 2:
            self.tabWidget.setTabText(2, self.tr("Layers"))
        if self.tabWidget.count() > 3:
            self.tabWidget.setTabText(3, self.tr("Advanced"))
        if self.tabWidget.count() > 4:
            self.tabWidget.setTabText(4, self.tr("Wiki"))

        # Onglet Général
        self.groupLibrairie.setTitle(self.tr("Web Library"))
        self.groupFondsPlan.setTitle(self.tr("Basemap"))
        self.groupOutils.setTitle(self.tr("Tools to integrate"))

        # CheckBox Outils
        self.chkRecherche.setText(self.tr("Address search"))
        self.chkGeoloc.setText(self.tr("GPS location"))
        self.chkMesure.setText(self.tr("Measure (distance/area)"))
        self.chkImprimer.setText(self.tr("Print button"))
        self.chkPleinEcran.setText(self.tr("Full screen mode"))
        self.chkMiniMap.setText(self.tr("Overview map (MiniMap)"))
        self.chkScale.setText(self.tr("Scale bar"))
        self.chkMousePosition.setText(self.tr("Cursor position"))
        self.chkAttribution.setText(self.tr("Attribution"))
        self.chkFiltreAvance.setText(self.tr("Advanced filter"))

        # Onglet Personnalisation
        self.groupTitre.setTitle(self.tr("Map title"))
        self.groupLogo.setTitle(self.tr("Logo"))
        self.groupCouleur.setTitle(self.tr("Header color"))
        self.groupThemeVisuel.setTitle(self.tr("Interface theme"))

        self.btnChoisirLogo.setText(self.tr("Choose a logo"))
        self.lblLogoPath.setText(self.tr("No logo"))
        self.chkAfficherLogo.setText(self.tr("Show logo"))
        self.btnChoisirCouleur.setText(self.tr("Choose a color"))

        # Thèmes
        self.comboTheme.setItemText(0, self.tr("Light"))
        self.comboTheme.setItemData(0, "Clair")
        self.comboTheme.setItemText(1, self.tr("Dark"))
        self.comboTheme.setItemData(1, "Sombre")
        self.comboTheme.setItemText(2, self.tr("Professional"))
        self.comboTheme.setItemData(2, "Professionnel")
        self.comboTheme.setItemText(3, self.tr("Colorful"))
        self.comboTheme.setItemData(3, "Coloré")

        # Onglet Couches
        self.groupSelectionCouches.setTitle(self.tr("Layer selection to export"))
        self.groupCouchesWMS.setTitle(
            self.tr("WMS layers (loaded live from the server)")
        )
        self.groupPopupsConfiguration.setTitle(self.tr("Popup configuration per layer"))
        self.btnMoveUp.setText(self.tr("Move Up"))
        self.btnMoveDown.setText(self.tr("Move Down"))
        self.btnSelectAll.setText(self.tr("Select all"))
        self.btnDeselectAll.setText(self.tr("Deselect all"))
        self.btnInvertSelection.setText(self.tr("Invert"))

        self.lblCouchesPopup.setText(self.tr("1. Select a layer:"))
        self.lblChampsPopup.setText(self.tr("2. Check fields to display:"))

        # Onglet Avancé
        self.groupOptimisation.setTitle(self.tr("Data optimization"))
        self.groupExport.setTitle(self.tr("Export options"))

        self.chkSimplifier.setText(self.tr("Simplify geometries"))
        self.chkCompresser.setText(self.tr("Compress JSON data"))
        self.chkPrecision.setText(self.tr("Round coordinates"))
        self.chkZip.setText(self.tr("Export as ZIP file"))
        self.chkOuvrirNavigateur.setText(self.tr("Open automatically in browser"))

        self.groupPostgres.setTitle(self.tr("PostgreSQL data source"))
        self.chkPostgresDynamique.setText(
            self.tr(
                "Dynamically load PostGIS layers from PostgreSQL "
                "(instead of a static export)"
            )
        )
        self.lblPostgresAvertissement.setText(
            self.tr(
                "Requires a hosting environment with PHP and Apache active. "
                "Not compatible with a local export or fully static hosting "
                "(GitHub Pages, etc.). Only applies to layers already "
                "connected to PostGIS in QGIS."
            )
        )

        # Fond de plan (combo)
        for i in range(self.comboFondPlan.count()):
            item = self.comboFondPlan.itemText(i)
            if "OpenStreetMap" in item or "OpenStreetMap" in self.tr("OpenStreetMap"):
                self.comboFondPlan.setItemText(i, f"{self.tr('OpenStreetMap')}")
            elif "Google Satellite" in item or "Google Satellite" in self.tr(
                "Google Satellite"
            ):
                self.comboFondPlan.setItemText(i, f"🛰️ {self.tr('Google Satellite')}")
            elif "Google Hybrid" in item or "Google Hybrid" in self.tr("Google Hybrid"):
                self.comboFondPlan.setItemText(i, f"🌐 {self.tr('Google Hybrid')}")

        self.chkFondPlanPersonnalise.setText(self.tr("Custom URL"))

        # Onglet Wiki
        self.load_wiki_content()

        # Boutons OK / Cancel
        from qgis.PyQt.QtWidgets import QDialogButtonBox

        ok_button = self.buttonBox.button(
            qenum(QDialogButtonBox, "StandardButton", "Ok")
        )
        if ok_button:
            ok_button.setText(self.tr("OK"))
        cancel_button = self.buttonBox.button(
            qenum(QDialogButtonBox, "StandardButton", "Cancel")
        )
        if cancel_button:
            cancel_button.setText(self.tr("Cancel"))

    def load_wiki_content(self):
        """Charge le contenu du Wiki selon la langue"""
        try:
            settings = QSettings()
            locale = settings.value("locale/userLocale", "en_US")

            if locale and locale.startswith("fr"):
                wiki_file = os.path.join(
                    os.path.dirname(__file__), "i18n", "wiki_fr.html"
                )
            else:
                wiki_file = os.path.join(
                    os.path.dirname(__file__), "i18n", "wiki_en.html"
                )

            if os.path.exists(wiki_file):
                with open(wiki_file, "r", encoding="utf-8") as f:
                    self.wikiTextEdit.setHtml(f.read())
            else:
                wiki_html = self.tr("WIKI_HTML")
                if wiki_html and wiki_html != "WIKI_HTML":
                    self.wikiTextEdit.setHtml(wiki_html)
                else:
                    self.wikiTextEdit.setHtml(
                        "<h1>Universal Map2web</h1><p>Wiki non disponible.</p>"
                    )
        except Exception as e:
            journaliser(f"Erreur chargement Wiki : {e}", "Warning")
            self.wikiTextEdit.setHtml(f"<h1>Erreur</h1><p>{str(e)}</p>")

    def charger_couches_qgis(self):
        if not hasattr(self, "listCouches") or not hasattr(self, "listCouchesPopup"):
            return
        self.listCouches.clear()
        self.listCouchesPopup.clear()
        self.listCouchesWMS.clear()

        layers = QgsProject.instance().mapLayers().values()
        for layer in layers:
            if layer.type() == qenum(QgsMapLayer, "LayerType", "VectorLayer"):
                item_export = QListWidgetItem(layer.name())
                item_export.setCheckState(qenum(Qt, "CheckState", "Checked"))
                item_export.setData(qenum(Qt, "ItemDataRole", "UserRole"), layer.id())
                self.listCouches.addItem(item_export)

                item_popup = QListWidgetItem(layer.name())
                item_popup.setData(qenum(Qt, "ItemDataRole", "UserRole"), layer.id())
                self.listCouchesPopup.addItem(item_popup)

                self.popup_config[layer.id()] = [
                    field.name() for field in layer.fields()
                ]
            elif hasattr(self, "listCouchesWMS") and est_couche_wms(layer):
                item_wms = QListWidgetItem(f"🛰️ {layer.name()}")
                item_wms.setCheckState(qenum(Qt, "CheckState", "Checked"))
                item_wms.setData(qenum(Qt, "ItemDataRole", "UserRole"), layer.id())
                self.listCouchesWMS.addItem(item_wms)

        if self.listCouchesPopup.count() > 0:
            self.listCouchesPopup.setCurrentRow(0)

    # Sauvegarde et Restauration des paramètres de configuration
    def sauvegarder_configuration_projet(self):
        """Sauvegarde toutes les options de la fenêtre dans le fichier de projet QGIS."""
        project = QgsProject.instance()
        sec = "UniversalMap2web"

        # Personnalisation
        project.writeEntry(sec, "txtTitreCarte", self.txtTitreCarte.text())
        project.writeEntry(sec, "logoPath", self.lblLogoPath.toolTip() or "")
        project.writeEntry(sec, "logoText", self.lblLogoPath.text())
        project.writeEntry(sec, "chkAfficherLogo", self.chkAfficherLogo.isChecked())
        project.writeEntry(sec, "txtCouleurEntete", self.txtCouleurEntete.text())
        project.writeEntry(sec, "comboTheme", self.comboTheme.currentIndex())

        # Fond de plan
        project.writeEntry(sec, "comboFondPlan", self.comboFondPlan.currentIndex())
        project.writeEntry(
            sec,
            "chkFondPlanPersonnalise",
            self.chkFondPlanPersonnalise.isChecked(),
        )
        project.writeEntry(sec, "txtFondPlanURL", self.txtFondPlanURL.text())

        # Outils
        chks = [
            "chkRecherche",
            "chkGeoloc",
            "chkMesure",
            "chkImprimer",
            "chkPleinEcran",
            "chkMiniMap",
            "chkScale",
            "chkMousePosition",
            "chkAttribution",
            "chkFiltreAvance",
        ]
        for chk in chks:
            if hasattr(self, chk):
                project.writeEntry(sec, chk, getattr(self, chk).isChecked())

        # Options avancées
        project.writeEntry(sec, "chkSimplifier", self.chkSimplifier.isChecked())
        project.writeEntry(sec, "spinTolerance", str(self.spinTolerance.value()))
        project.writeEntry(sec, "chkCompresser", self.chkCompresser.isChecked())
        project.writeEntry(sec, "chkPrecision", self.chkPrecision.isChecked())
        project.writeEntry(sec, "spinPrecision", self.spinPrecision.value())
        project.writeEntry(
            sec, "chkPostgresDynamique", self.chkPostgresDynamique.isChecked()
        )
        project.writeEntry(sec, "chkZip", self.chkZip.isChecked())
        project.writeEntry(
            sec, "chkOuvrirNavigateur", self.chkOuvrirNavigateur.isChecked()
        )

        # Sauvegarde de la configuration des popups (JSON)
        project.writeEntry(sec, "popup_config", json.dumps(self.popup_config))

    def restaurer_configuration_projet(self):
        """Restaure les options précédemment sauvegardées dans le projet QGIS."""
        project = QgsProject.instance()
        sec = "UniversalMap2web"

        # Vérification si une configuration existe pour ce projet
        valeur_test, ok = project.readEntry(sec, "txtTitreCarte", "")
        if not ok:
            return

        # Personnalisation
        val, _ = project.readEntry(sec, "txtTitreCarte", "")
        if val:
            self.txtTitreCarte.setText(val)

        path, _ = project.readEntry(sec, "logoPath", "")
        text, _ = project.readEntry(sec, "logoText", self.tr("No logo"))
        self.lblLogoPath.setText(text)
        if path:
            self.lblLogoPath.setToolTip(path)

        val, _ = project.readBoolEntry(sec, "chkAfficherLogo", True)
        self.chkAfficherLogo.setChecked(val)

        val, _ = project.readEntry(sec, "txtCouleurEntete", "#1a1a2e")
        self.txtCouleurEntete.setText(val)
        if hasattr(self, "btnChoisirCouleur") and val:
            self.btnChoisirCouleur.setStyleSheet(
                f"background-color: {val}; color: white;"
            )

        val, _ = project.readNumEntry(sec, "comboTheme", 0)
        if 0 <= val < self.comboTheme.count():
            self.comboTheme.setCurrentIndex(val)

        # Fond de plan
        val, _ = project.readNumEntry(sec, "comboFondPlan", 0)
        if 0 <= val < self.comboFondPlan.count():
            self.comboFondPlan.setCurrentIndex(val)

        val, _ = project.readBoolEntry(sec, "chkFondPlanPersonnalise", False)
        self.chkFondPlanPersonnalise.setChecked(val)

        val, _ = project.readEntry(sec, "txtFondPlanURL", "")
        self.txtFondPlanURL.setText(val)

        # Outils
        chks = [
            "chkRecherche",
            "chkGeoloc",
            "chkMesure",
            "chkImprimer",
            "chkPleinEcran",
            "chkMiniMap",
            "chkScale",
            "chkMousePosition",
            "chkAttribution",
            "chkFiltreAvance",
        ]
        for chk in chks:
            if hasattr(self, chk):
                val, _ = project.readBoolEntry(sec, chk, getattr(self, chk).isChecked())
                getattr(self, chk).setChecked(val)

        # Options avancées
        val, _ = project.readBoolEntry(sec, "chkSimplifier", False)
        self.chkSimplifier.setChecked(val)

        val, _ = project.readDoubleEntry(sec, "spinTolerance", 0.0)
        self.spinTolerance.setValue(val)

        val, _ = project.readBoolEntry(sec, "chkCompresser", False)
        self.chkCompresser.setChecked(val)

        val, _ = project.readBoolEntry(sec, "chkPrecision", False)
        self.chkPrecision.setChecked(val)

        val, _ = project.readNumEntry(sec, "spinPrecision", 6)
        self.spinPrecision.setValue(val)

        val, _ = project.readBoolEntry(sec, "chkPostgresDynamique", False)
        self.chkPostgresDynamique.setChecked(val)

        val, _ = project.readBoolEntry(sec, "chkZip", False)
        self.chkZip.setChecked(val)

        val, _ = project.readBoolEntry(sec, "chkOuvrirNavigateur", True)
        self.chkOuvrirNavigateur.setChecked(val)

        # Restauration de la configuration des Popups
        popup_json, ok = project.readEntry(sec, "popup_config", "")
        if ok and popup_json:
            try:
                self.popup_config = json.loads(popup_json)
                # Recharger les cases à cocher si une couche est actuellement sélectionnée
                current_item = self.listCouchesPopup.currentItem()
                if current_item:
                    self.changement_couche_popup(current_item, None)
            except Exception as e:
                journaliser(f"Erreur chargement popups : {e}", "Warning")

    # Onglet Personnalisation
    def selectionner_logo(self):
        fichier, _ = QFileDialog.getOpenFileName(
            self,
            self.tr("Choose a logo"),
            "",
            "Images (*.png *.jpg *.jpeg *.svg)",
        )
        if fichier and hasattr(self, "lblLogoPath"):
            self.lblLogoPath.setText(os.path.basename(fichier))
            self.lblLogoPath.setToolTip(fichier)

    def selectionner_couleur(self):
        if not hasattr(self, "txtCouleurEntete"):
            return
        couleur_actuelle = self.txtCouleurEntete.text() or "#1a1a2e"
        couleur = QColorDialog.getColor(QtGui.QColor(couleur_actuelle), self)
        if couleur.isValid():
            self.txtCouleurEntete.setText(couleur.name())
            self.btnChoisirCouleur.setStyleSheet(
                f"background-color: {couleur.name()}; color: white;"
            )

    # Onglet Couches
    def tout_selectionner(self):
        if not hasattr(self, "listCouches"):
            return
        for i in range(self.listCouches.count()):
            self.listCouches.item(i).setCheckState(qenum(Qt, "CheckState", "Checked"))

    def tout_deselectionner(self):
        if not hasattr(self, "listCouches"):
            return
        for i in range(self.listCouches.count()):
            self.listCouches.item(i).setCheckState(qenum(Qt, "CheckState", "Unchecked"))

    def inverser_selection(self):
        if not hasattr(self, "listCouches"):
            return
        for i in range(self.listCouches.count()):
            item = self.listCouches.item(i)
            new_state = (
                qenum(Qt, "CheckState", "Unchecked")
                if item.checkState() == qenum(Qt, "CheckState", "Checked")
                else qenum(Qt, "CheckState", "Checked")
            )
            item.setCheckState(new_state)

    def monter_couche(self):
        """Déplace la couche sélectionnée d'une position vers le haut."""
        if not hasattr(self, "listCouches"):
            return
        row = self.listCouches.currentRow()
        if row <= 0:
            return
        item = self.listCouches.takeItem(row)
        self.listCouches.insertItem(row - 1, item)
        self.listCouches.setCurrentRow(row - 1)

    def descendre_couche(self):
        """Déplace la couche sélectionnée d'une position vers le bas."""
        if not hasattr(self, "listCouches"):
            return
        row = self.listCouches.currentRow()
        if row < 0 or row >= self.listCouches.count() - 1:
            return
        item = self.listCouches.takeItem(row)
        self.listCouches.insertItem(row + 1, item)
        self.listCouches.setCurrentRow(row + 1)

    # Mémorisation des popups
    def sauvegarder_champs_couche_actuelle(self):
        if not hasattr(self, "listChampsPopup"):
            return
        if self.derniere_couche_id and self.derniere_couche_id in self.popup_config:
            champs_coches = []
            for i in range(self.listChampsPopup.count()):
                item = self.listChampsPopup.item(i)
                if item.checkState() == qenum(Qt, "CheckState", "Checked"):
                    champs_coches.append(item.text())
            self.popup_config[self.derniere_couche_id] = champs_coches

    def changement_couche_popup(self, current_item, previous_item):
        if not hasattr(self, "listChampsPopup"):
            return
        if previous_item:
            previous_id = previous_item.data(qenum(Qt, "ItemDataRole", "UserRole"))
            self.derniere_couche_id = previous_id
            self.sauvegarder_champs_couche_actuelle()

        self.listChampsPopup.clear()
        if not current_item:
            return

        layer_id = current_item.data(qenum(Qt, "ItemDataRole", "UserRole"))
        self.derniere_couche_id = layer_id
        layer = QgsProject.instance().mapLayer(layer_id)
        if layer:
            champs_sauvegardes = self.popup_config.get(
                layer_id, [f.name() for f in layer.fields()]
            )
            for field in layer.fields():
                field_name = field.name()
                item_champ = QListWidgetItem(field_name)
                item_champ.setCheckState(
                    qenum(Qt, "CheckState", "Checked")
                    if field_name in champs_sauvegardes
                    else qenum(Qt, "CheckState", "Unchecked")
                )
                self.listChampsPopup.addItem(item_champ)

    def accept(self):
        self.sauvegarder_champs_couche_actuelle()
        self.sauvegarder_configuration_projet()
        super(UniversalMap2webDialog, self).accept()

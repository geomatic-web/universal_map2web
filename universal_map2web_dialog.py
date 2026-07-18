# -*- coding: utf-8 -*-
import os
from qgis.PyQt import QtGui
from qgis.PyQt.QtCore import Qt, QCoreApplication, QSettings
from qgis.PyQt.QtWidgets import QDialog, QColorDialog, QFileDialog, QListWidgetItem
from qgis.core import QgsProject, QgsMapLayer
from qgis.PyQt import uic

FORM_CLASS, _ = uic.loadUiType(
    os.path.join(os.path.dirname(__file__), "universal_map2web_dialog_base.ui")
)


class UniversalMap2webDialog(QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        super(UniversalMap2webDialog, self).__init__(parent)
        self.setupUi(self)
        self.popup_config = {}
        self.derniere_couche_id = None

        # ✅ Appliquer les traductions immédiatement
        self.apply_translations()

        if hasattr(self, "btnChoisirLogo"):
            self.btnChoisirLogo.clicked.connect(self.selectionner_logo)
        if hasattr(self, "btnChoisirCouleur"):
            self.btnChoisirCouleur.clicked.connect(self.selectionner_couleur)
        if hasattr(self, "btnSelectAll"):
            self.btnSelectAll.clicked.connect(self.tout_selectionner)
        if hasattr(self, "btnDeselectAll"):
            self.btnDeselectAll.clicked.connect(self.tout_deselectionner)
        if hasattr(self, "btnInvertSelection"):
            self.btnInvertSelection.clicked.connect(self.inverser_selection)
        if hasattr(self, "listCouchesPopup"):
            self.listCouchesPopup.currentItemChanged.connect(
                self.changement_couche_popup
            )

        self.charger_couches_qgis()

    def tr(self, text):
        """Traduit un texte"""
        return QCoreApplication.translate("UniversalMap2web", text)

    def apply_translations(self):
        """Applique les traductions à tous les éléments de l'interface"""
        print("🌐 Application des traductions...")

        # --- Onglets ---
        if hasattr(self, "tabWidget"):
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

        # --- Onglet Général ---
        if hasattr(self, "groupLibrairie"):
            self.groupLibrairie.setTitle(self.tr("Web Library"))
        if hasattr(self, "groupFondsPlan"):
            self.groupFondsPlan.setTitle(self.tr("Basemap"))
        if hasattr(self, "groupOutils"):
            self.groupOutils.setTitle(self.tr("Tools to integrate"))

        # --- CheckBox Outils ---
        if hasattr(self, "chkRecherche"):
            self.chkRecherche.setText(self.tr("Address search"))
        if hasattr(self, "chkGeoloc"):
            self.chkGeoloc.setText(self.tr("GPS location"))
        if hasattr(self, "chkMesure"):
            self.chkMesure.setText(self.tr("Measure (distance/area)"))
        if hasattr(self, "chkImprimer"):
            self.chkImprimer.setText(self.tr("Print button"))
        if hasattr(self, "chkPleinEcran"):
            self.chkPleinEcran.setText(self.tr("Full screen mode"))
        if hasattr(self, "chkMiniMap"):
            self.chkMiniMap.setText(self.tr("Overview map (MiniMap)"))
        if hasattr(self, "chkScale"):
            self.chkScale.setText(self.tr("Scale bar"))
        if hasattr(self, "chkMousePosition"):
            self.chkMousePosition.setText(self.tr("Cursor position"))
        if hasattr(self, "chkAttribution"):
            self.chkAttribution.setText(self.tr("Attribution"))
        if hasattr(self, "chkFiltreAvance"):
            self.chkFiltreAvance.setText(self.tr("Advanced filter"))

        # --- Onglet Personnalisation ---
        if hasattr(self, "groupTitre"):
            self.groupTitre.setTitle(self.tr("Map title"))
        if hasattr(self, "groupLogo"):
            self.groupLogo.setTitle(self.tr("Logo"))
        if hasattr(self, "groupCouleur"):
            self.groupCouleur.setTitle(self.tr("Header color"))
        if hasattr(self, "groupThemeVisuel"):
            self.groupThemeVisuel.setTitle(self.tr("Interface theme"))

        if hasattr(self, "btnChoisirLogo"):
            self.btnChoisirLogo.setText(self.tr("Choose a logo"))
        if hasattr(self, "lblLogoPath"):
            self.lblLogoPath.setText(self.tr("No logo"))
        if hasattr(self, "chkAfficherLogo"):
            self.chkAfficherLogo.setText(self.tr("Show logo"))
        if hasattr(self, "btnChoisirCouleur"):
            self.btnChoisirCouleur.setText(self.tr("Choose a color"))

        # --- Thèmes ---
        # On traduit le TEXTE affiché mais on fige la VALEUR réelle (clé de THEMES)
        # dans les données de l'item, pour que html_generator.py puisse la relire
        # sans dépendre de la langue de l'interface.
        if hasattr(self, "comboTheme"):
            self.comboTheme.setItemText(0, self.tr("Light"))
            self.comboTheme.setItemData(0, "Clair")
            self.comboTheme.setItemText(1, self.tr("Dark"))
            self.comboTheme.setItemData(1, "Sombre")
            self.comboTheme.setItemText(2, self.tr("Professional"))
            self.comboTheme.setItemData(2, "Professionnel")
            self.comboTheme.setItemText(3, self.tr("Colorful"))
            self.comboTheme.setItemData(3, "Coloré")

        # --- Onglet Couches ---
        if hasattr(self, "groupSelectionCouches"):
            self.groupSelectionCouches.setTitle(self.tr("Layer selection to export"))
        if hasattr(self, "groupPopupsConfiguration"):
            self.groupPopupsConfiguration.setTitle(
                self.tr("Popup configuration per layer")
            )

        if hasattr(self, "btnSelectAll"):
            self.btnSelectAll.setText(self.tr("Select all"))
        if hasattr(self, "btnDeselectAll"):
            self.btnDeselectAll.setText(self.tr("Deselect all"))
        if hasattr(self, "btnInvertSelection"):
            self.btnInvertSelection.setText(self.tr("Invert"))

        if hasattr(self, "lblCouchesPopup"):
            self.lblCouchesPopup.setText(self.tr("1. Select a layer:"))
        if hasattr(self, "lblChampsPopup"):
            self.lblChampsPopup.setText(self.tr("2. Check fields to display:"))

        # --- Onglet Avancé ---
        if hasattr(self, "groupOptimisation"):
            self.groupOptimisation.setTitle(self.tr("Data optimization"))
        if hasattr(self, "groupExport"):
            self.groupExport.setTitle(self.tr("Export options"))

        if hasattr(self, "chkSimplifier"):
            self.chkSimplifier.setText(self.tr("Simplify geometries"))
        if hasattr(self, "chkCompresser"):
            self.chkCompresser.setText(self.tr("Compress JSON data"))
        if hasattr(self, "chkPrecision"):
            self.chkPrecision.setText(self.tr("Round coordinates"))
        if hasattr(self, "chkZip"):
            self.chkZip.setText(self.tr("Export as ZIP file"))
        if hasattr(self, "chkOuvrirNavigateur"):
            self.chkOuvrirNavigateur.setText(self.tr("Open automatically in browser"))

        # --- Fond de plan (combo) ---
        if hasattr(self, "comboFondPlan"):
            for i in range(self.comboFondPlan.count()):
                item = self.comboFondPlan.itemText(i)
                if "OpenStreetMap" in item or "OpenStreetMap" in self.tr(
                    "OpenStreetMap"
                ):
                    self.comboFondPlan.setItemText(i, f"🌍 {self.tr('OpenStreetMap')}")
                elif "Google Satellite" in item or "Google Satellite" in self.tr(
                    "Google Satellite"
                ):
                    self.comboFondPlan.setItemText(
                        i, f"🛰️ {self.tr('Google Satellite')}"
                    )
                elif "Google Hybrid" in item or "Google Hybrid" in self.tr(
                    "Google Hybrid"
                ):
                    self.comboFondPlan.setItemText(i, f"🌐 {self.tr('Google Hybrid')}")

        if hasattr(self, "chkFondPlanPersonnalise"):
            self.chkFondPlanPersonnalise.setText(self.tr("Custom URL"))

        # --- Onglet Wiki ---
        if hasattr(self, "wikiTextEdit"):
            self.load_wiki_content()

        # --- Boutons OK / Cancel (CORRIGÉ) ---
        if hasattr(self, "buttonBox"):
            from qgis.PyQt.QtWidgets import QDialogButtonBox

            ok_button = self.buttonBox.button(QDialogButtonBox.StandardButton.Ok)
            if ok_button:
                ok_button.setText(self.tr("OK"))
            cancel_button = self.buttonBox.button(
                QDialogButtonBox.StandardButton.Cancel
            )
            if cancel_button:
                cancel_button.setText(self.tr("Cancel"))

        print("✅ Traductions appliquées")

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
                print(f"✅ Wiki chargé depuis {wiki_file}")
            else:
                # Fallback : utiliser la traduction
                wiki_html = self.tr("WIKI_HTML")
                if wiki_html and wiki_html != "WIKI_HTML":
                    self.wikiTextEdit.setHtml(wiki_html)
                else:
                    self.wikiTextEdit.setHtml(
                        "<h1>Universal Map2web</h1><p>Wiki non disponible.</p>"
                    )
        except Exception as e:
            print(f"❌ Erreur chargement Wiki: {e}")
            self.wikiTextEdit.setHtml(f"<h1>Erreur</h1><p>{str(e)}</p>")

    def charger_couches_qgis(self):
        if not hasattr(self, "listCouches") or not hasattr(self, "listCouchesPopup"):
            return
        self.listCouches.clear()
        self.listCouchesPopup.clear()

        layers = QgsProject.instance().mapLayers().values()
        for layer in layers:
            if layer.type() == QgsMapLayer.LayerType.VectorLayer:
                item_export = QListWidgetItem(layer.name())
                item_export.setCheckState(Qt.CheckState.Checked)
                item_export.setData(Qt.ItemDataRole.UserRole, layer.id())
                self.listCouches.addItem(item_export)

                item_popup = QListWidgetItem(layer.name())
                item_popup.setData(Qt.ItemDataRole.UserRole, layer.id())
                self.listCouchesPopup.addItem(item_popup)

                self.popup_config[layer.id()] = [
                    field.name() for field in layer.fields()
                ]

        if self.listCouchesPopup.count() > 0:
            self.listCouchesPopup.setCurrentRow(0)

    # ── Onglet Personnalisation ──────────────────────────────
    def selectionner_logo(self):
        fichier, _ = QFileDialog.getOpenFileName(
            self, self.tr("Choose a logo"), "", "Images (*.png *.jpg *.jpeg *.svg)"
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
            if hasattr(self, "btnChoisirCouleur"):
                self.btnChoisirCouleur.setStyleSheet(
                    f"background-color: {couleur.name()}; color: white;"
                )

    # ── Onglet Couches ───────────────────────────────────────
    def tout_selectionner(self):
        if not hasattr(self, "listCouches"):
            return
        for i in range(self.listCouches.count()):
            self.listCouches.item(i).setCheckState(Qt.CheckState.Checked)

    def tout_deselectionner(self):
        if not hasattr(self, "listCouches"):
            return
        for i in range(self.listCouches.count()):
            self.listCouches.item(i).setCheckState(Qt.CheckState.Unchecked)

    def inverser_selection(self):
        if not hasattr(self, "listCouches"):
            return
        for i in range(self.listCouches.count()):
            item = self.listCouches.item(i)
            new_state = (
                Qt.CheckState.Unchecked
                if item.checkState() == Qt.CheckState.Checked
                else Qt.CheckState.Checked
            )
            item.setCheckState(new_state)

    # ── Mémorisation des popups ──────────────────────────────
    def sauvegarder_champs_couche_actuelle(self):
        if not hasattr(self, "listChampsPopup"):
            return
        if self.derniere_couche_id and self.derniere_couche_id in self.popup_config:
            champs_coches = []
            for i in range(self.listChampsPopup.count()):
                item = self.listChampsPopup.item(i)
                if item.checkState() == Qt.CheckState.Checked:
                    champs_coches.append(item.text())
            self.popup_config[self.derniere_couche_id] = champs_coches

    def changement_couche_popup(self, current_item, previous_item):
        if not hasattr(self, "listChampsPopup"):
            return
        if previous_item:
            previous_id = previous_item.data(Qt.ItemDataRole.UserRole)
            self.derniere_couche_id = previous_id
            self.sauvegarder_champs_couche_actuelle()

        self.listChampsPopup.clear()
        if not current_item:
            return

        layer_id = current_item.data(Qt.ItemDataRole.UserRole)
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
                    Qt.CheckState.Checked
                    if field_name in champs_sauvegardes
                    else Qt.CheckState.Unchecked
                )
                self.listChampsPopup.addItem(item_champ)

    def accept(self):
        self.sauvegarder_champs_couche_actuelle()
        super(UniversalMap2webDialog, self).accept()

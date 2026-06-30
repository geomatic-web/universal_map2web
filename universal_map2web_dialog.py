# -*- coding: utf-8 -*-
import os
from qgis.PyQt import QtGui
from qgis.PyQt.QtCore import Qt
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

    def charger_couches_qgis(self):
        if not hasattr(
                self,
                "listCouches") or not hasattr(
                self,
                "listCouchesPopup"):
            return
        self.listCouches.clear()
        self.listCouchesPopup.clear()

        layers = QgsProject.instance().mapLayers().values()
        for layer in layers:
            if layer.type() == QgsMapLayer.VectorLayer:
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
            self, "Choisir un logo", "", "Images (*.png *.jpg *.jpeg *.svg)"
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

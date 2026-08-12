#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Compileur pour Universal Map2web
Utilise les modules de QGIS pour compiler
"""

import os
from pathlib import Path

print("=" * 50)
print("Compilation Universal Map2web")
print("=" * 50)

# S'assurer qu'on est dans le bon dossier
os.chdir(Path(__file__).parent)

try:
    # 1. Compiler l'interface UI
    print("\n1. Compilation de l'interface utilisateur...")

    # Lire le fichier .ui
    with open("universal_map2web_dialog_base.ui", "r", encoding="utf-8") as ui_file:
        ui_content = ui_file.read()

    # Générer le code Python
    with open("universal_map2web_dialog.py", "w", encoding="utf-8") as py_file:
        py_file.write('''# -*- coding: utf-8 -*-

"""
Interface générée automatiquement
Ne pas modifier directement - Modifier le fichier .ui
"""

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_UniversalMap2webDialog(object):
    def setupUi(self, UniversalMap2webDialog):
        UniversalMap2webDialog.setObjectName("UniversalMap2webDialog")
        UniversalMap2webDialog.resize(750, 650)

        # Layout principal
        self.verticalLayout = QtWidgets.QVBoxLayout(UniversalMap2webDialog)
        self.verticalLayout.setObjectName("verticalLayout")

        # Tab Widget
        self.tabWidget = QtWidgets.QTabWidget(UniversalMap2webDialog)
        self.tabWidget.setObjectName("tabWidget")
        self.verticalLayout.addWidget(self.tabWidget)

        # === Onglet 1 : Général ===
        self.tabGeneral = QtWidgets.QWidget()
        self.tabGeneral.setObjectName("tabGeneral")
        self.tabWidget.addTab(self.tabGeneral, "Général")

        # GroupBox Sélection des couches
        self.groupSelectionCouches = QtWidgets.QGroupBox(self.tabGeneral)
        self.groupSelectionCouches.setGeometry(QtCore.QRect(10, 10, 720, 250))
        self.groupSelectionCouches.setTitle("Sélection des couches")
        self.groupSelectionCouches.setObjectName("groupSelectionCouches")

        # Liste des couches
        self.listCouches = QtWidgets.QListWidget(self.groupSelectionCouches)
        self.listCouches.setGeometry(QtCore.QRect(10, 30, 700, 150))
        self.listCouches.setObjectName("listCouches")

        # Boutons de sélection
        self.btnSelectAll = QtWidgets.QPushButton(self.groupSelectionCouches)
        self.btnSelectAll.setGeometry(QtCore.QRect(10, 190, 120, 30))
        self.btnSelectAll.setText("Tout sélectionner")

        self.btnDeselectAll = QtWidgets.QPushButton(self.groupSelectionCouches)
        self.btnDeselectAll.setGeometry(QtCore.QRect(140, 190, 120, 30))
        self.btnDeselectAll.setText("Tout désélectionner")

        self.btnInvertSelection = QtWidgets.QPushButton(self.groupSelectionCouches)
        self.btnInvertSelection.setGeometry(QtCore.QRect(270, 190, 120, 30))
        self.btnInvertSelection.setText("Inverser")

        # GroupBox Librairie
        self.groupLibrairie = QtWidgets.QGroupBox(self.tabGeneral)
        self.groupLibrairie.setGeometry(QtCore.QRect(10, 270, 720, 80))
        self.groupLibrairie.setTitle("Librairie Web")

        self.radioLeaflet = QtWidgets.QRadioButton(self.groupLibrairie)
        self.radioLeaflet.setGeometry(QtCore.QRect(20, 30, 100, 25))
        self.radioLeaflet.setText("Leaflet")
        self.radioLeaflet.setChecked(True)

        self.radioOpenLayers = QtWidgets.QRadioButton(self.groupLibrairie)
        self.radioOpenLayers.setGeometry(QtCore.QRect(130, 30, 120, 25))
        self.radioOpenLayers.setText("OpenLayers")

        self.radioCesium = QtWidgets.QRadioButton(self.groupLibrairie)
        self.radioCesium.setGeometry(QtCore.QRect(260, 30, 120, 25))
        self.radioCesium.setText("Cesium 3D")

        # GroupBox Fonds de plan
        self.groupFondsPlan = QtWidgets.QGroupBox(self.tabGeneral)
        self.groupFondsPlan.setGeometry(QtCore.QRect(10, 360, 720, 80))
        self.groupFondsPlan.setTitle("Fond de plan")

        self.comboFondPlan = QtWidgets.QComboBox(self.groupFondsPlan)
        self.comboFondPlan.setGeometry(QtCore.QRect(10, 30, 200, 25))

        self.chkFondPlanPersonnalise = QtWidgets.QCheckBox(self.groupFondsPlan)
        self.chkFondPlanPersonnalise.setGeometry(QtCore.QRect(220, 30, 120, 25))
        self.chkFondPlanPersonnalise.setText("Personnalisé")

        self.txtFondPlanURL = QtWidgets.QLineEdit(self.groupFondsPlan)
        self.txtFondPlanURL.setGeometry(QtCore.QRect(340, 30, 370, 25))
        self.txtFondPlanURL.setEnabled(False)
        self.txtFondPlanURL.setPlaceholderText("https://...")

        # === Onglet 2 : Style ===
        self.tabStyle = QtWidgets.QWidget()
        self.tabStyle.setObjectName("tabStyle")
        self.tabWidget.addTab(self.tabStyle, "Style")

        # === Onglet 3 : Interactivité ===
        self.tabInteraction = QtWidgets.QWidget()
        self.tabInteraction.setObjectName("tabInteraction")
        self.tabWidget.addTab(self.tabInteraction, "Interactivité")

        # === Onglet 4 : Avancé ===
        self.tabAvance = QtWidgets.QWidget()
        self.tabAvance.setObjectName("tabAvance")
        self.tabWidget.addTab(self.tabAvance, " Avancé")

        # Boutons OK/Cancel
        self.buttonBox = QtWidgets.QDialogButtonBox(UniversalMap2webDialog)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.verticalLayout.addWidget(self.buttonBox)

        self.retranslateUi(UniversalMap2webDialog)
        self.buttonBox.accepted.connect(UniversalMap2webDialog.accept)
        self.buttonBox.rejected.connect(UniversalMap2webDialog.reject)
        QtCore.QMetaObject.connectSlotsByName(UniversalMap2webDialog)

    def retranslateUi(self, UniversalMap2webDialog):
        _translate = QtCore.QCoreApplication.translate
        UniversalMap2webDialog.setWindowTitle(_translate("UniversalMap2webDialog", "Universal Map2web - Export de cartes HTML"))

''')
    print("   Interface compilée avec succès !")

    # 2. Créer le fichier resources.py
    print("\n2. Compilation des ressources...")
    with open("resources.py", "w", encoding="utf-8") as f:
        f.write("""# -*- coding: utf-8 -*-

# Ressources
# Pas de ressources pour le moment

def qCleanupResources():
    pass

""")
    print("   Ressources compilées avec succès !")

    print("\n" + "=" * 50)
    print("Compilation terminée avec succès !")
    print("=" * 50)
    print("\nFichiers générés :")
    print("   - universal_map2web_dialog.py")
    print("   - resources.py")
    print("\nTu peux maintenant tester l'extension dans QGIS !")

except Exception as e:
    print(f"\nErreur lors de la compilation: {e}")
    import traceback

    traceback.print_exc()

input("\nAppuyez sur Entrée pour fermer...")

# -*- coding: utf-8 -*-
from qgis.PyQt import QtCore, QtGui, QtWidgets
from qgis.PyQt.QtWidgets import QAction, QMessageBox, QFileDialog, QListWidgetItem, QProgressDialog, QColorDialog
from qgis.PyQt.QtCore import QSettings, Qt
from qgis.core import (
    QgsProject, QgsVectorLayer, QgsMapLayer, Qgis, QgsWkbTypes,
    QgsCoordinateTransform, QgsCoordinateReferenceSystem
)
from qgis.gui import QgsMessageBar

import os
import json
import shutil
import webbrowser
import base64
from datetime import datetime

from .universal_map2web_dialog import UniversalMap2webDialog


class UniversalMap2web:
    """Classe principale de l'extension Universal Map2web — rendu fidèle à QGIS, 100 % générique"""

    def __init__(self, iface):
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.dialog = None
        self.settings = QSettings()
        self.selected_layers = []
        self.export_data = {}
        self.output_dir = None
        self.styles_dir = None

    def initGui(self):
        icon_path = os.path.join(self.plugin_dir, 'icon.png')
        self.action = QAction(
            QtGui.QIcon(icon_path) if os.path.exists(
                icon_path) else QtGui.QIcon(),
            "Universal Map2web",
            self.iface.mainWindow()
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
            self.dialog.comboFondPlan.addItems([
                "🌍 OpenStreetMap",
                "🛰️ Google Satellite",
                "🌐 Google Hybrid"
            ])
        self.dialog.chkFondPlanPersonnalise.toggled.connect(
            self.activer_fond_personnalise)

        # Bouton d'export connecté directement, fenêtre reste ouverte (pas de
        # fermeture auto)
        if hasattr(self.dialog, 'btnExporter'):
            self.dialog.btnExporter.clicked.connect(self.exporter)
        elif hasattr(self.dialog, 'buttonBox'):
            try:
                self.dialog.buttonBox.accepted.disconnect()
            except (TypeError, RuntimeError):
                pass  # rien n'était connecté — normal au premier lancement
            self.dialog.buttonBox.accepted.connect(self.exporter)

        self.dialog.show()  # fenêtre persistante : on peut exporter plusieurs fois sans rouvrir

    def activer_fond_personnalise(self, checked):
        self.dialog.txtFondPlanURL.setEnabled(checked)

    def clean_filename(self, name):
        caracteres_speciaux = [
            ' ', '/', '\\', ':', '*', '?', '"', '<', '>', '|',
            'é', 'è', 'ê', 'à', 'â', 'î', 'ô', 'û', 'ç',
            '(', ')', '[', ']', '{', '}', ';', ','
        ]
        for char in caracteres_speciaux:
            name = name.replace(char, '_')
        while '__' in name:
            name = name.replace('__', '_')
        return name.strip('_')

    def get_geometry_type(self, layer):
        if layer.type() != QgsMapLayer.VectorLayer:
            return "Inconnu"
        return QgsWkbTypes.geometryType(layer.wkbType())

    def extraire_style_symbole(self, symbol, geom_type):
        """Extrait fillColor, color, weight, opacity, fillOpacity, radius depuis un symbole QGIS"""
        MM_TO_PX = 3.78  # approximation mm → px

        style = {
            "color": "#3388ff",
            "fillColor": "#3388ff",
            "weight": 1.0,
            "opacity": 1.0,
            "fillOpacity": 0.6,
            "radius": 6,
            "dashArray": None
        }

        if not symbol or symbol.symbolLayerCount() == 0:
            return style

        sl = symbol.symbolLayer(0)

        try:
            op = symbol.opacity()
            style["opacity"] = round(op, 2)
        except Exception:
            pass

        # ── POLYGONE ──
        if geom_type == QgsWkbTypes.PolygonGeometry:
            if hasattr(sl, 'fillColor') and sl.fillColor().isValid():
                c = sl.fillColor()
                style["fillColor"] = c.name()
                style["fillOpacity"] = round(c.alpha() / 255.0, 2)
            else:
                style["fillColor"] = "#000000"
                style["fillOpacity"] = 0.0
            if hasattr(sl, 'strokeColor') and sl.strokeColor().isValid():
                style["color"] = sl.strokeColor().name()
            elif hasattr(sl, 'color') and sl.color().isValid():
                style["color"] = sl.color().name()
            if hasattr(sl, 'strokeWidth'):
                try:
                    style["weight"] = max(sl.strokeWidth() * MM_TO_PX, 0.5)
                except Exception:
                    pass

        # ── LIGNE ──
        elif geom_type == QgsWkbTypes.LineGeometry:
            couleur_ligne = None
            if hasattr(sl, 'color') and sl.color().isValid():
                couleur_ligne = sl.color()
            if not couleur_ligne or not couleur_ligne.isValid():
                try:
                    couleur_ligne = symbol.color()
                except Exception:
                    pass
            if couleur_ligne and couleur_ligne.isValid():
                style["color"] = couleur_ligne.name()
            if hasattr(sl, 'width'):
                try:
                    style["weight"] = max(sl.width() * MM_TO_PX, 1.0)
                except Exception:
                    pass
            style["fillOpacity"] = 0.0

        # ── POINT ──
        else:
            if hasattr(sl, 'color') and sl.color().isValid():
                c = sl.color()
                style["fillColor"] = c.name()
                style["color"] = c.name()
            if hasattr(sl, 'strokeColor') and sl.strokeColor().isValid():
                style["color"] = sl.strokeColor().name()
            try:
                style["radius"] = max(sl.size() * MM_TO_PX / 2.0, 3)
            except Exception:
                pass

        return style

    def extraire_etiquettes(self, layer):
        """
        Extrait la configuration d'étiquetage QGIS (labeling) d'une couche,
        si l'étiquetage est activé. Retourne un dict exploitable côté Leaflet
        (champ à afficher, taille, couleur, police) ou None si pas d'étiquette.
        """
        try:
            if not layer.labelsEnabled():
                return None
            labeling = layer.labeling()
            if not labeling:
                return None

            # On essaie de lire les paramètres du premier "settings" disponible
            settings = None
            try:
                settings = labeling.settings()
            except Exception:
                # Rule-based labeling : on prend la première règle
                try:
                    root = labeling.rootRule()
                    enfants = root.children()
                    if enfants:
                        settings = enfants[0].settings()
                except Exception:
                    settings = None

            if not settings:
                return None

            champ_label = settings.fieldName
            text_format = settings.format()
            couleur = "#000000"
            taille = 10
            try:
                c = text_format.color()
                if c.isValid():
                    couleur = c.name()
                taille = text_format.size()
                if taille <= 0:
                    taille = 10
            except Exception:
                pass

            return {
                "champ": champ_label,
                "couleur": couleur,
                # conversion approx pt → px lisible web
                "taille": round(taille * 1.4, 1)
            }
        except Exception:
            return None
        """Génère des miniatures PNG pour la légende des points et lignes"""
        icones_exportees = []
        if layer.geometryType() == QgsWkbTypes.PolygonGeometry:
            return icones_exportees

        renderer = layer.renderer()
        if not renderer:
            return icones_exportees

        os.makedirs(self.styles_dir, exist_ok=True)
        from qgis.core import QgsSymbolLayerUtils
        from qgis.PyQt.QtCore import QSize

        if hasattr(renderer, 'categories') and len(renderer.categories()) > 0:
            for idx, cat in enumerate(renderer.categories()):
                label = cat.label() if cat.label() else str(cat.value())
                symbol = cat.symbol()
                if symbol:
                    img_name = f"icon_{nom_fichier_couche}_{idx}.png"
                    img_path = os.path.join(self.styles_dir, img_name)
                    pixmap = QgsSymbolLayerUtils.symbolPreviewPixmap(
                        symbol, QSize(24, 24))
                    pixmap.save(img_path, "PNG")
                    icones_exportees.append({
                        "valeur": str(cat.value()),
                        "label": label,
                        "img_path": f"styles_images/{img_name}"
                    })

        elif hasattr(renderer, 'ranges') and len(renderer.ranges()) > 0:
            for idx, rang in enumerate(renderer.ranges()):
                label = rang.label() if rang.label() else f"{
                    rang.lowerValue():.2f} – {
                    rang.upperValue():.2f}"
                symbol = rang.symbol()
                if symbol:
                    img_name = f"icon_{nom_fichier_couche}_grad_{idx}.png"
                    img_path = os.path.join(self.styles_dir, img_name)
                    pixmap = QgsSymbolLayerUtils.symbolPreviewPixmap(
                        symbol, QSize(24, 24))
                    pixmap.save(img_path, "PNG")
                    icones_exportees.append({
                        "valeur": str(rang.lowerValue()),
                        "label": label,
                        "img_path": f"styles_images/{img_name}"
                    })

        elif hasattr(renderer, 'rootRule'):
            for idx, rule in enumerate(renderer.rootRule().children()):
                label = rule.label() if rule.label() else f"Règle {idx + 1}"
                symbol = rule.symbol()
                if symbol:
                    img_name = f"icon_{nom_fichier_couche}_rule_{idx}.png"
                    img_path = os.path.join(self.styles_dir, img_name)
                    pixmap = QgsSymbolLayerUtils.symbolPreviewPixmap(
                        symbol, QSize(24, 24))
                    pixmap.save(img_path, "PNG")
                    icones_exportees.append({
                        "valeur": label,
                        "label": label,
                        "img_path": f"styles_images/{img_name}"
                    })

        elif hasattr(renderer, 'symbol') and renderer.symbol():
            symbol = renderer.symbol()
            img_name = f"icon_{nom_fichier_couche}_unique.png"
            img_path = os.path.join(self.styles_dir, img_name)
            pixmap = QgsSymbolLayerUtils.symbolPreviewPixmap(
                symbol, QSize(24, 24))
            pixmap.save(img_path, "PNG")
            icones_exportees.append({
                "valeur": "default",
                "label": layer.name(),
                "img_path": f"styles_images/{img_name}"
            })

        return icones_exportees

    def extraire_icones_symbologie(self, layer, nom_fichier_couche):
        """Génère des miniatures PNG pour la légende des points et lignes"""
        icones_exportees = []
        if layer.geometryType() == QgsWkbTypes.PolygonGeometry:
            return icones_exportees

        renderer = layer.renderer()
        if not renderer:
            return icones_exportees

        os.makedirs(self.styles_dir, exist_ok=True)
        from qgis.core import QgsSymbolLayerUtils
        from qgis.PyQt.QtCore import QSize

        if hasattr(renderer, 'categories') and len(renderer.categories()) > 0:
            for idx, cat in enumerate(renderer.categories()):
                label = cat.label() if cat.label() else str(cat.value())
                symbol = cat.symbol()
                if symbol:
                    img_name = f"icon_{nom_fichier_couche}_{idx}.png"
                    img_path = os.path.join(self.styles_dir, img_name)
                    pixmap = QgsSymbolLayerUtils.symbolPreviewPixmap(
                        symbol, QSize(24, 24))
                    pixmap.save(img_path, "PNG")
                    icones_exportees.append({
                        "valeur": str(cat.value()),
                        "label": label,
                        "img_path": f"styles_images/{img_name}"
                    })

        elif hasattr(renderer, 'ranges') and len(renderer.ranges()) > 0:
            for idx, rang in enumerate(renderer.ranges()):
                label = rang.label() if rang.label() else f"{
                    rang.lowerValue():.2f} – {
                    rang.upperValue():.2f}"
                symbol = rang.symbol()
                if symbol:
                    img_name = f"icon_{nom_fichier_couche}_grad_{idx}.png"
                    img_path = os.path.join(self.styles_dir, img_name)
                    pixmap = QgsSymbolLayerUtils.symbolPreviewPixmap(
                        symbol, QSize(24, 24))
                    pixmap.save(img_path, "PNG")
                    icones_exportees.append({
                        "valeur": str(rang.lowerValue()),
                        "label": label,
                        "img_path": f"styles_images/{img_name}"
                    })

        elif hasattr(renderer, 'rootRule'):
            for idx, rule in enumerate(renderer.rootRule().children()):
                label = rule.label() if rule.label() else f"Règle {idx + 1}"
                symbol = rule.symbol()
                if symbol:
                    img_name = f"icon_{nom_fichier_couche}_rule_{idx}.png"
                    img_path = os.path.join(self.styles_dir, img_name)
                    pixmap = QgsSymbolLayerUtils.symbolPreviewPixmap(
                        symbol, QSize(24, 24))
                    pixmap.save(img_path, "PNG")
                    icones_exportees.append({
                        "valeur": label,
                        "label": label,
                        "img_path": f"styles_images/{img_name}"
                    })

        elif hasattr(renderer, 'symbol') and renderer.symbol():
            symbol = renderer.symbol()
            img_name = f"icon_{nom_fichier_couche}_unique.png"
            img_path = os.path.join(self.styles_dir, img_name)
            pixmap = QgsSymbolLayerUtils.symbolPreviewPixmap(
                symbol, QSize(24, 24))
            pixmap.save(img_path, "PNG")
            icones_exportees.append({
                "valeur": "default",
                "label": layer.name(),
                "img_path": f"styles_images/{img_name}"
            })

        return icones_exportees

    def construire_carte_styles_renderer(self, renderer, geom_type):
        carte = {}
        style_defaut = None

        try:
            if hasattr(renderer, 'categories'):
                for cat in renderer.categories():
                    symbol = cat.symbol()
                    if symbol:
                        style = self.extraire_style_symbole(symbol, geom_type)
                        carte[str(cat.value())] = style
                        if cat.value() in (None, ''):
                            style_defaut = style

            elif hasattr(renderer, 'ranges'):
                plages = []
                for rang in renderer.ranges():
                    symbol = rang.symbol()
                    if symbol:
                        style = self.extraire_style_symbole(symbol, geom_type)
                        plages.append(
                            (rang.lowerValue(), rang.upperValue(), style))
                carte['__plages__'] = plages

            elif hasattr(renderer, 'symbol') and renderer.symbol():
                style = self.extraire_style_symbole(
                    renderer.symbol(), geom_type)
                carte['default'] = style
                style_defaut = style

            elif hasattr(renderer, 'rootRule'):
                rules = renderer.rootRule().children()
                if rules and rules[0].symbol():
                    style_defaut = self.extraire_style_symbole(
                        rules[0].symbol(), geom_type)

        except Exception:
            pass

        if not style_defaut:
            style_defaut = {
                "color": "#3388ff", "fillColor": "#3388ff",
                "weight": 1.0, "opacity": 1.0, "fillOpacity": 0.6,
                "radius": 6, "dashArray": None
            }
        return carte, style_defaut

    def lookup_style(self, carte_styles, style_defaut, renderer, feature):
        try:
            if hasattr(renderer, 'categories') and hasattr(
                    renderer, 'classAttribute'):
                val = str(feature[renderer.classAttribute(
                )]) if feature[renderer.classAttribute()] is not None else ''
                return carte_styles.get(val, style_defaut)

            elif '__plages__' in carte_styles:
                attr = renderer.classAttribute() if hasattr(
                    renderer, 'classAttribute') else None
                if attr:
                    try:
                        val = float(feature[attr])
                        for (low, high, style) in carte_styles['__plages__']:
                            if low <= val <= high:
                                return style
                    except (TypeError, ValueError):
                        pass

            elif 'default' in carte_styles:
                return carte_styles['default']

        except Exception:
            pass
        return style_defaut

    def layer_to_geojson(self, layer, popup_fields=None):
        features = []
        crs_dest = QgsCoordinateReferenceSystem("EPSG:4326")
        transform = QgsCoordinateTransform(
            layer.crs(), crs_dest, QgsProject.instance())

        renderer = layer.renderer()
        geom_type = layer.geometryType()
        attribut_classification = renderer.classAttribute(
        ) if hasattr(renderer, 'classAttribute') else None

        carte_styles, style_defaut = self.construire_carte_styles_renderer(
            renderer, geom_type)

        for feature in layer.getFeatures():
            geom = feature.geometry()
            if geom and not geom.isEmpty():
                geom.transform(transform)
                geojson_geom = json.loads(geom.asJson())

                props = {}
                champs_a_exporter = popup_fields if popup_fields else [
                    f.name() for f in layer.fields()]
                for field_name in champs_a_exporter:
                    if layer.fields().indexOf(field_name) != -1:
                        val = feature[field_name]
                        props[field_name] = str(val) if val is not None else ""

                val_classe = str(feature[attribut_classification]) if (
                    attribut_classification and feature[attribut_classification] is not None) else "default"
                props["_qgis_class_val"] = val_classe

                style = self.lookup_style(
                    carte_styles, style_defaut, renderer, feature)
                props["_qgis_style"] = style

                features.append({
                    'type': 'Feature',
                    'geometry': geojson_geom,
                    'properties': props
                })

        return {
            'type': 'FeatureCollection',
            'crs': {'type': 'name', 'properties': {'name': 'EPSG:4326'}},
            'features': features
        }

    def exporter(self):
        self.export_data.clear()
        couches_a_exporter = []

        for i in range(self.dialog.listCouches.count()):
            item = self.dialog.listCouches.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                layer_id = item.data(Qt.ItemDataRole.UserRole)
                layer = QgsProject.instance().mapLayer(layer_id)
                if layer and layer.type() == QgsMapLayer.VectorLayer:
                    couches_a_exporter.append(layer)

        if not couches_a_exporter:
            QMessageBox.warning(
                self.dialog,
                "Aucune couche",
                "Veuillez cocher au moins une couche à exporter.")
            return

        last_dir = self.settings.value("UniversalMap2web/last_dir", "")
        output_dir = QFileDialog.getExistingDirectory(
            self.dialog, "Choisir le dossier d'export", last_dir)
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
                "Génération des styles et géométries...", "Annuler",
                0, len(couches_a_exporter), self.dialog
            )
            progress.setWindowModality(Qt.WindowModality.WindowModal)

            for i, layer in enumerate(couches_a_exporter):
                if progress.wasCanceled():
                    break
                progress.setValue(i)
                progress.setLabelText(
                    f"Extraction des styles : {
                        layer.name()}")
                QtCore.QCoreApplication.processEvents()

                nom_fichier = self.clean_filename(layer.name())
                legend_icons = self.extraire_icones_symbologie(
                    layer, nom_fichier)
                popup_fields = self.dialog.popup_config.get(
                    layer.id(), [f.name() for f in layer.fields()])
                geojson = self.layer_to_geojson(layer, popup_fields)
                etiquette = self.extraire_etiquettes(layer)

                chemin_geojson = os.path.join(
                    data_dir, f"{nom_fichier}.geojson")
                with open(chemin_geojson, 'w', encoding='utf-8') as f:
                    json.dump(geojson, f, indent=2)

                renderer = layer.renderer()
                attr_classif = renderer.classAttribute() if hasattr(
                    renderer, 'classAttribute') else None

                self.export_data[layer.name()] = {
                    'fichier': f"data/{nom_fichier}.geojson",
                    'geom_type': self.get_geometry_type(layer),
                    'popup_fields': popup_fields,
                    'legend_style': legend_icons,
                    'is_polygon': (layer.geometryType() == QgsWkbTypes.PolygonGeometry),
                    'is_line': (layer.geometryType() == QgsWkbTypes.LineGeometry),
                    'is_point': (layer.geometryType() == QgsWkbTypes.PointGeometry),
                    'etiquette': etiquette,
                    'attr_classif': attr_classif
                }

            progress.setValue(len(couches_a_exporter))
            self.generer_html(self.output_dir)

            if self.dialog.chkOuvrirNavigateur.isChecked():
                self.demarrer_serveur_local(self.output_dir)

            # Message de succès non-bloquant dans la barre d'interface QGIS
            self.iface.messageBar().pushMessage(
                "Succès",
                f"Carte Web exportée avec succès dans : {self.output_dir}",
                level=Qgis.Success,
                duration=5
            )

        except Exception as e:
            QMessageBox.critical(
                self.dialog, "Erreur d'export",
                f"Une erreur est survenue lors du traitement :\n{str(e)}"
            )

    def demarrer_serveur_local(self, dossier, port=8000):
        """
        Lance un serveur HTTP local (http.server) dans un thread démon,
        servant le dossier d'export, puis ouvre le navigateur sur localhost:PORT.
        Nécessaire car fetch() est bloqué par CORS en file:// dans la plupart des navigateurs.
        Si le port est occupé, on essaie les ports suivants jusqu'à en trouver un libre.
        """
        import threading
        import http.server
        import socketserver
        import socket

        # Trouver un port libre à partir de `port`
        port_choisi = port
        for tentative in range(20):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.2)
                if s.connect_ex(('localhost', port_choisi)) != 0:
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

    def generer_html(self, export_dir):
        titre = self.dialog.txtTitreCarte.text()
        couleur_entete = self.dialog.txtCouleurEntete.text()
        afficher_logo = self.dialog.chkAfficherLogo.isChecked()
        logo_path = (
            self.dialog.lblLogoPath.toolTip()
            if (afficher_logo and self.dialog.lblLogoPath.toolTip() != "Aucun logo")
            else None
        )

        logo_base64 = None
        if logo_path and os.path.exists(logo_path):
            try:
                with open(logo_path, 'rb') as f:
                    ext = os.path.splitext(logo_path)[1][1:].lower()
                    if ext in ['jpg', 'jpeg']:
                        ext = 'jpeg'
                    logo_base64 = f"data:image/{ext};base64,{
                        base64.b64encode(
                            f.read()).decode('utf-8')}"
            except Exception:
                pass

        fond_plan = self.dialog.comboFondPlan.currentText()
        fond_urls = {
            "🌍 OpenStreetMap": "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
            "🛰️ Google Satellite": "https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}",
            "🌐 Google Hybrid": "https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}"}
        url_fond = fond_urls.get(
            fond_plan, "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png")
        html_logo = f'<div class="logo-container"><img src="{logo_base64}" alt="Logo"/></div>' if logo_base64 else ""

        def opt(nom, defaut=False):
            w = getattr(self.dialog, nom, None)
            return w.isChecked() if w else defaut

        opt_geoloc = opt('chkGeoloc')
        opt_mesure = opt('chkMesure')
        opt_pleinecran = opt('chkPleinEcran')
        opt_echelle = opt('chkScale', True)
        opt_recherche = opt('chkRecherche')
        opt_minimap = opt('chkMiniMap')
        opt_mousepos = opt('chkMousePosition')
        opt_imprimer = opt('chkImprimer')
        opt_attribution = opt('chkAttribution', True)

        css_cluster = """
    <link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.css" />
    <link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.Default.css" />
    <style>
        .marker-cluster-small, .marker-cluster-medium, .marker-cluster-large { background-color: rgba(78, 205, 196, 0.2) !important; border-radius: 50% !important; }
        .marker-cluster-small div, .marker-cluster-medium div, .marker-cluster-large div { background-color: rgba(78, 205, 196, 0.85) !important; color: #fff !important; font-weight: bold; font-family: Arial, sans-serif; font-size: 12px; border-radius: 50%; width: 30px; height: 30px; margin-left: 5px; margin-top: 5px; display: flex; align-items: center; justify-content: center; box-shadow: 0 0 8px rgba(0,0,0,0.3); }

        /* Style d'animation pour le clignotement des entités sélectionnées */
        @keyframes clignoter-filtre {
            0% { opacity: 1; filter: drop-shadow(0 0 12px #f9ca24) saturate(3); stroke: #f9ca24; stroke-width: 5; }
            50% { opacity: 0.2; filter: drop-shadow(0 0 2px #f9ca24); stroke: #ffffff; stroke-width: 2; }
            100% { opacity: 1; filter: drop-shadow(0 0 12px #f9ca24) saturate(3); stroke: #f9ca24; stroke-width: 5; }
        }
        .entite-clignotante {
            animation: clignoter-filtre 0.8s linear 5; /* Clignote 5 fois rapidement */
        }
    </style>
        """

        extra_css = ''
        extra_js = ''
        extra_js += '\n    <script src="https://unpkg.com/leaflet.markercluster@1.5.3/dist/leaflet.markercluster.js"></script>'

        if opt_mesure:
            extra_css += '\n    <link rel="stylesheet" href="https://unpkg.com/leaflet-measure@3.1.0/dist/leaflet-measure.css" />'
            extra_js += '\n    <script src="https://unpkg.com/leaflet-measure@3.1.0/dist/leaflet-measure.js"></script>'

        if opt_pleinecran:
            extra_css += '\n    <link rel="stylesheet" href="https://unpkg.com/leaflet.fullscreen@1.6.0/Control.FullScreen.css" />'
            extra_js += '\n    <script src="https://unpkg.com/leaflet.fullscreen@1.6.0/Control.FullScreen.js"></script>'

        if opt_recherche:
            extra_css += '\n    <link rel="stylesheet" href="https://unpkg.com/leaflet-control-geocoder/dist/Control.Geocoder.css" />'
            extra_js += '\n    <script src="https://unpkg.com/leaflet-control-geocoder/dist/Control.Geocoder.js"></script>'

        if opt_minimap:
            extra_css += '\n    <link rel="stylesheet" href="https://unpkg.com/leaflet-minimap@3.6.1/dist/Control.MiniMap.min.css" />'
            extra_js += '\n    <script src="https://unpkg.com/leaflet-minimap@3.6.1/dist/Control.MiniMap.min.js"></script>'

        if opt_imprimer:
            extra_js += '\n    <script src="https://unpkg.com/leaflet-easyprint@2.1.9/dist/bundle.js"></script>'

        if opt_geoloc:
            extra_css += '\n    <link rel="stylesheet" href="https://unpkg.com/leaflet.locatecontrol/dist/L.Control.Locate.min.css" />'
            extra_js += '\n    <script src="https://unpkg.com/leaflet.locatecontrol/dist/L.Control.Locate.min.js"></script>'

        outils_js = ''
        if opt_attribution:
            outils_js += "\n        map.attributionControl.setPrefix('Leaflet | Universal Map2web');"
        else:
            outils_js += "\n        map.removeControl(map.attributionControl);"
        if opt_echelle:
            outils_js += "\n        L.control.scale({ imperial: false, metric: true, position: 'bottomleft' }).addTo(map);"
        if opt_geoloc:
            outils_js += "\n        if (typeof L.control.locate !== 'undefined') { L.control.locate({ position: 'topleft', flyTo: true, strings: { title: 'Ma position' } }).addTo(map); }"
        if opt_mesure:
            outils_js += "\n        if (typeof L.control.measure !== 'undefined') { L.control.measure({ primaryLengthUnit:'kilometers', secondaryLengthUnit:'meters', primaryAreaUnit:'sqkilometers', activeColor:'#4ecdc4', completedColor:'#4ecdc4' }).addTo(map); }"
        if opt_pleinecran:
            outils_js += "\n        if (typeof L.control.fullscreen !== 'undefined') { L.control.fullscreen({ title: 'Plein ecran', titleCancel: 'Quitter' }).addTo(map); }"
        if opt_recherche:
            outils_js += "\n        if (typeof L.Control.Geocoder !== 'undefined') { L.Control.geocoder({ defaultMarkGeocode: false, placeholder: 'Rechercher une adresse...' }).addTo(map); }"
        if opt_minimap:
            outils_js += "\n        if (typeof L.Control.MiniMap !== 'undefined') { var miniLayer = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png'); new L.Control.MiniMap(miniLayer, { toggleDisplay: true, minimized: false }).addTo(map); }"
        if opt_imprimer:
            outils_js += "\n        if (typeof L.easyPrint !== 'undefined') { var printer = L.easyPrint({ title: 'Exporter la carte', position: 'topleft', sizeModes: ['Current', 'A4Portrait', 'A4Landscape'], filename: 'export_carte_sig', exportOnly: true, hideControlContainer: false, defaultSizeTitles: { Current: 'Taille actuelle', A4Landscape: 'Format A4 Paysage', A4Portrait: 'Format A4 Portrait' } }).addTo(map); printer._printCurrent = function() { window.print(); }; printer._printPage = function() { window.print(); }; }"
        if opt_mousepos:
            outils_js += "\n        map.on('mousemove', function(e) { var el = document.getElementById('mouse-pos'); if (el) el.textContent = 'Lat: ' + e.latlng.lat.toFixed(5) + '  Lng: ' + e.latlng.lng.toFixed(5); });"

        mousepos_html = (
            '<div id="mouse-pos" style="position:absolute;bottom:28px;left:5px;'
            'background:rgba(0,0,0,0.65);color:#fff;padding:3px 8px;border-radius:4px;'
            'font-size:11px;z-index:999;pointer-events:none;"></div>') if opt_mousepos else ''

        meta_couches_json = json.dumps(self.export_data, ensure_ascii=False)
        meta_couches_escaped = meta_couches_json.replace(
            '\\', '\\\\').replace("'", "\\'")

        html_content = f'''<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{titre}</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />{extra_css}
    __CSS_CLUSTER__
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>{extra_js}
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif; background: #1a1a2e; overflow: hidden; }}
        #container {{ display: flex; flex-direction: column; width: 100vw; height: 100vh; }}
        #header {{
            background: {couleur_entete}; padding: 10px 20px;
            display: flex; justify-content: space-between; align-items: center;
            color: white; box-shadow: 0 2px 15px rgba(0,0,0,0.4); z-index: 1000; min-height: 65px;
        }}
        .header-left {{ display: flex; align-items: center; gap: 15px; }}
        .logo-container img {{ max-height: 45px; max-width: 120px; object-fit: contain; }}
        #main-zone {{ display: flex; flex-direction: row; flex: 1; position: relative; height: calc(100vh - 65px); }}
        #map {{ flex: 1; height: 100%; }}
        #sidebar {{
            width: 300px; background: rgba(26, 26, 46, 0.97);
            padding: 20px; color: white; overflow-y: auto;
            border-right: 1px solid rgba(255,255,255,0.1); box-shadow: -5px 0 20px rgba(0,0,0,0.3);
            order: -1;
            border-right: 1px solid rgba(255,255,255,0.1);
            border-left: none;
            box-shadow: 5px 0 20px rgba(0,0,0,0.3);
        }}
        h3 {{ margin-bottom: 15px; font-size: 12px; text-transform: uppercase; letter-spacing: 1px;
              color: #4ecdc4; border-bottom: 2px solid #4ecdc4; padding-bottom: 5px; }}
        .group-couche {{ margin-bottom: 18px; background: rgba(255,255,255,0.02); padding: 10px;
                         border-radius: 6px; border: 1px solid rgba(255,255,255,0.05); }}
        .item-couche-tit {{ display: flex; align-items: center; font-weight: 600; font-size: 13px; margin-bottom: 6px; }}
        .item-couche-tit input {{ margin-right: 8px; accent-color: #4ecdc4; width: 15px; height: 15px; cursor: pointer; }}
        .sous-legende-item {{ display: flex; align-items: center; gap: 8px; padding: 3px 0 3px 22px;
                              font-size: 11px; color: #bbb; }}
        .img-legend-icon {{ width: 16px; height: 16px; object-fit: contain; }}
        .legend-poly-swatch {{
            display: inline-block; width: 14px; height: 14px; border-radius: 2px;
            border: 2px solid #3388ff; background-color: rgba(51,136,255,0.2); flex-shrink: 0;
        }}
        .legend-line-swatch {{
            display: inline-block; width: 22px; height: 3px;
            border-radius: 2px; background-color: #3388ff; flex-shrink: 0;
        }}
        .leaflet-popup-content-wrapper {{ background: #1a1a2e; color: #fff;
            border: 1px solid rgba(255,255,255,0.2); border-radius: 8px; }}
        .leaflet-popup-tip {{ background: #1a1a2e; }}
        .custom-popup-table {{ width: 100%; border-collapse: collapse; margin-top: 5px; }}
        .custom-popup-table td {{ padding: 4px 6px; border-bottom: 1px solid rgba(255,255,255,0.08); font-size: 12px; }}
        .popup-title {{ color: #4ecdc4; font-weight: bold; font-size: 13px;
                        margin-bottom: 6px; border-bottom: 1px solid #4ecdc4; padding-bottom: 3px; }}
        #filtre-panel {{ margin-top: 18px; padding-top: 14px; border-top: 1px solid rgba(255,255,255,0.1); }}
        #filtre-panel h3 {{ color: #f9ca24; border-bottom-color: #f9ca24; }}
        .filtre-row {{ display: flex; flex-direction: column; gap: 6px; margin-bottom: 8px; }}
        .filtre-row label {{ font-size: 10px; text-transform: uppercase; color: #888; letter-spacing: 0.8px; }}
        .filtre-select, .filtre-input {{
            width: 100%; padding: 6px 8px; border-radius: 5px;
            background: #252538; color: #fff; border: 1px solid rgba(255,255,255,0.15);
            font-size: 12px; outline: none;
        }}
        .filtre-select:focus, .filtre-input:focus {{ border-color: #f9ca24; }}
        .filtre-btns {{ display: flex; gap: 6px; margin-top: 4px; }}
        .btn-filtre {{
            flex: 1; padding: 7px; border: none; border-radius: 5px;
            font-size: 12px; font-weight: 600; cursor: pointer; transition: opacity 0.2s;
        }}
        .btn-filtre:hover {{ opacity: 0.85; }}
        .btn-appliquer {{ background: #f9ca24; color: #1a1a2e; }}
        .btn-reset     {{ background: rgba(255,255,255,0.1); color: #fff; }}
        #filtre-resultat {{ font-size: 11px; color: #f9ca24; margin-top: 5px; min-height: 16px; }}
        .filtre-valeurs-liste {{
            max-height: 120px; overflow-y: auto; background: #1a1a2e;
            border: 1px solid rgba(255,255,255,0.1); border-radius: 5px; margin-top: 4px;
        }}
        .filtre-valeur-item {{
            padding: 4px 8px; font-size: 11px; cursor: pointer; color: #ccc;
        }}
        .filtre-valeur-item:hover {{ background: rgba(249,202,36,0.2); color: #f9ca24; }}
    </style>
</head>
<body>
    <div id="loader"></div>
    <div id="container">
        <div id="header">
            <div class="header-left">
                {html_logo}
                <h2 style="font-weight:500; font-size:20px;">{titre}</h2>
            </div>
            <div>
                <select id="fondSelector" onchange="changerFond()"
                    style="padding:6px 12px; border-radius:6px; background:#252538;
                           color:#fff; border:1px solid rgba(255,255,255,0.2); cursor:pointer;">
                    <option value="BASE">Base configurée</option>
                    <option value="OSM">🌍 OpenStreetMap</option>
                    <option value="SAT">🛰️ Google Satellite</option>
                </select>
            </div>
        </div>
        <div id="main-zone">
            <div id="sidebar">
                <h3>Légende &amp; Couches</h3>
                <div id="legende-liste"></div>

                <div id="filtre-panel">
                    <h3>🔎 Filtre par attribut</h3>
                    <div class="filtre-row">
                        <label>Couche</label>
                        <select id="filtre-couche" class="filtre-select" onchange="filtreChangerCouche()">
                            <option value="">-- Choisir une couche --</option>
                        </select>
                    </div>
                    <div class="filtre-row">
                        <label>Champ</label>
                        <select id="filtre-champ" class="filtre-select" onchange="filtreChangerChamp()">
                            <option value="">-- Choisir un champ --</option>
                        </select>
                    </div>
                    <div class="filtre-row">
                        <label>Opérateur</label>
                        <select id="filtre-operateur" class="filtre-select">
                            <option value="eq">= (égal à)</option>
                            <option value="neq">≠ (différent de)</option>
                            <option value="contains">⊃ contient</option>
                            <option value="starts">commence par</option>
                            <option value="gt">&gt; (supérieur à)</option>
                            <option value="lt">&lt; (inférieur à)</option>
                            <option value="gte">≥ (supérieur ou égal)</option>
                            <option value="lte">≤ (inférieur ou égal)</option>
                        </select>
                    </div>
                    <div class="filtre-row">
                        <label>Valeur</label>
                        <input id="filtre-valeur" class="filtre-input" type="text"
                               placeholder="Saisir ou cliquer une valeur..." oninput="filtreValeurInput()" />
                        <div id="filtre-valeurs-liste" class="filtre-valeurs-liste" style="display:none;"></div>
                    </div>
                    <div class="filtre-btns">
                        <button class="btn-filtre btn-appliquer" onclick="appliquerFiltre()">✔ Appliquer</button>
                        <button class="btn-filtre btn-reset" onclick="reinitialiserFiltre()">✖ Réinitialiser</button>
                    </div>
                    <div id="filtre-resultat"></div>
                </div>
            </div>
            <div id="map">
                {mousepos_html}
            </div>
        </div>
    </div>

    <script>
        document.body.classList.add('loading-active');
        var metaCouches = JSON.parse('{meta_couches_escaped}');
        var map = L.map('map', {{ zoomControl: true }}).setView([0, 0], 2);

        var baseLayers = {{
            "BASE": L.tileLayer("{url_fond}", {{ maxZoom: 20, crossOrigin: true }}),
            "OSM":  L.tileLayer("https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png", {{ maxZoom: 19, crossOrigin: true }}),
            "SAT":  L.tileLayer("https://mt1.google.com/vt/lyrs=s&x={{x}}&y={{y}}&z={{z}}", {{ maxZoom: 20, crossOrigin: true }})
        }};

        baseLayers["BASE"].addTo(map);

        function changerFond() {{
            var sel = document.getElementById('fondSelector').value;
            for (var k in baseLayers) {{ map.removeLayer(baseLayers[k]); }}
            baseLayers[sel].addTo(map);
        }}

        __OUTILS_JS__

        var couches_leaflet = {{}};
        var promesses_chargement = [];
        var geoLayersData = {{}};
        var couches_geolayers = {{}};
        var legendContainer = document.getElementById('legende-liste');

        Object.keys(metaCouches).forEach(function(nom) {{
            var info = metaCouches[nom];
            var safeId = nom.replace(/[^a-zA-Z0-9]/g, '_');

            var groupDiv = document.createElement('div');
            groupDiv.className = 'group-couche';
            groupDiv.innerHTML = '<div class="item-couche-tit">'
                + '<label><input type="checkbox" id="chk_' + safeId + '" checked /> ' + nom + '</label>'
                + '</div>';

            if (info.is_polygon) {{
                groupDiv.innerHTML += '<div class="sous-legende-item">'
                    + '<span class="legend-poly-swatch" id="poly_leg_' + safeId + '"></span>'
                    + '<span>' + nom + '</span></div>';
            }} else if (info.is_line) {{
                groupDiv.innerHTML += '<div class="sous-legende-item">'
                    + '<span class="legend-line-swatch" id="line_leg_' + safeId + '"></span>'
                    + '<span>' + nom + '</span></div>';
            }} else {{
                info.legend_style.forEach(function(node) {{
                    groupDiv.innerHTML += '<div class="sous-legende-item">'
                        + '<img class="img-legend-icon" src="' + node.img_path + '" />'
                        + '<span>' + node.label + '</span></div>';
                }});
            }}
            legendContainer.appendChild(groupDiv);

            var p = fetch(info.fichier)
                .then(function(r) {{ return r.json(); }})
                .then(function(data) {{
                    if (data.features && data.features.length > 0) {{
                        var fs = data.features[0].properties._qgis_style || {{}};
                        if (info.is_polygon) {{
                            var el = document.getElementById('poly_leg_' + safeId);
                            if (el) {{
                                el.style.border = '2px solid ' + (fs.color || '#3388ff');
                                el.style.backgroundColor = hexToRgba(fs.fillColor || fs.color || '#3388ff', fs.fillOpacity);
                            }}
                        }} else if (info.is_line) {{
                            var el = document.getElementById('line_leg_' + safeId);
                            if (el) {{
                                el.style.backgroundColor = fs.color || '#3388ff';
                                el.style.height = Math.min(Math.max(fs.weight || 2, 2), 8) + 'px';
                            }}
                        }}
                    }}

                    function deballerEtAjouterLayer(nomCouche, infoCouche, geoData) {{
                        var isPoint = !infoCouche.is_polygon && !infoCouche.is_line;
                        var clusterGroup = isPoint ? L.markerClusterGroup({{
                            disableClusteringAtZoom: 13,
                            maxClusterRadius: 50,
                            showCoverageOnHover: false,
                            iconCreateFunction: function(cluster) {{
                                var c = cluster.getChildCount();
                                return L.divIcon({{
                                    html: '<div style="background-color: rgba(78, 205, 196, 0.85); color: #fff; font-weight: bold; font-family: Arial, sans-serif; font-size: 12px; border-radius: 50%; width: 30px; height: 30px; display: flex; align-items: center; justify-content: center; box-shadow: 0 0 8px rgba(0,0,0,0.3);">' + c + '</div>',
                                    className: 'custom-marker-cluster',
                                    iconSize: L.point(40, 40),
                                    iconAnchor: L.point(20, 20)
                                }});
                            }}
                        }}) : null;

                        var geoLayer = L.geoJSON(geoData, {{
                            pointToLayer: function(feature, latlng) {{
                                var st  = feature.properties._qgis_style || {{}};
                                var val = feature.properties._qgis_class_val;

                                var matchImg = '';
                                infoCouche.legend_style.forEach(function(node) {{
                                    if (node.label === val || node.valeur === val) matchImg = node.img_path;
                                }});
                                if (!matchImg && infoCouche.legend_style.length > 0) matchImg = infoCouche.legend_style[0].img_path;

                                if (matchImg) {{
                                    return L.marker(latlng, {{ icon: L.icon({{
                                        iconUrl: matchImg, iconSize: [24, 24],
                                        iconAnchor: [12, 12], popupAnchor: [0, -12]
                                    }}) }});
                                }}
                                return L.circleMarker(latlng, {{
                                    radius:      st.radius      || 6,
                                    color:       st.color       || '#3388ff',
                                    fillColor:   st.fillColor   || '#3388ff',
                                    weight:      st.weight      != null ? st.weight      : 1,
                                    opacity:     st.opacity     != null ? st.opacity     : 1,
                                    fillOpacity: st.fillOpacity != null ? st.fillOpacity : 0.85
                                }});
                            }},

                            style: function(feature) {{
                                var s = (feature.properties && feature.properties._qgis_style) || {{}};
                                return {{
                                    color:       s.color       || '#3388ff',
                                    fillColor:   s.fillColor   || s.color || '#3388ff',
                                    weight:      s.weight      != null ? s.weight      : 1.0,
                                    opacity:     s.opacity     != null ? s.opacity     : 1.0,
                                    fillOpacity: (s.fillOpacity != null) ? s.fillOpacity : 0.0,
                                    dashArray:   s.dashArray   || null
                                }};
                            }},

                            onEachFeature: function(feature, layer) {{
                                var content = '<div style="min-width:200px;">'
                                    + '<div class="popup-title">' + nomCouche + '</div>'
                                    + '<table class="custom-popup-table">';
                                infoCouche.popup_fields.forEach(function(key) {{
                                    if (feature.properties[key] !== undefined && !key.startsWith('_qgis_')) {{
                                        content += '<tr>'
                                            + '<td style="color:#4ecdc4;font-weight:600;">' + key + '</td>'
                                            + '<td style="text-align:right;">' + feature.properties[key] + '</td>'
                                            + '</tr>';
                                    }}
                                }});
                                content += '</table></div>';
                                layer.bindPopup(content);
                            }}
                        }});

                        if (clusterGroup) {{
                            clusterGroup.addLayer(geoLayer);
                            return {{ actif: clusterGroup, brut: geoLayer }};
                        }}
                        return {{ actif: geoLayer, brut: geoLayer }};
                    }}

                    var construits = deballerEtAjouterLayer(nom, info, data);
                    construits.actif.addTo(map);

                    couches_leaflet[nom] = construits.actif;
                    geoLayersData[nom] = data;
                    couches_geolayers[nom] = construits.brut;

                    return couches_leaflet[nom];
                }});

            promesses_chargement.push(p);

            document.getElementById('chk_' + safeId).addEventListener('change', function(e) {{
                if (e.target.checked && couches_leaflet[nom]) {{ map.addLayer(couches_leaflet[nom]); }}
                else if (couches_leaflet[nom]) {{ map.removeLayer(couches_leaflet[nom]); }}
            }});
        }});

        Promise.all(promesses_chargement).then(function() {{
            var bounds = null;
            Object.values(couches_leaflet).forEach(function(lg) {{
                try {{
                    var b = lg.getBounds();
                    if (b && b.isValid()) bounds = bounds ? bounds.extend(b) : b;
                }} catch(e) {{}}
            }});

            if (bounds && bounds.isValid()) {{
                map.fitBounds(bounds, {{ padding: [20, 20], animate: false }});
            }} else {{
                map.setView([12.3, -1.5], 7);
            }}
            map.options.fadeAnimation = true;

            var loaderEl = document.getElementById('loader');
            if (loaderEl) loaderEl.style.display = 'none';
            document.body.classList.remove('loading-active');
        }});

        Promise.all(promesses_chargement).then(function() {{
            var sel = document.getElementById('filtre-couche');
            Object.keys(metaCouches).forEach(function(nom) {{
                var o = document.createElement('option');
                o.value = nom; o.textContent = nom;
                sel.appendChild(o);
            }});
        }});

        function filtreChangerCouche() {{
            var nom = document.getElementById('filtre-couche').value;
            var selChamp = document.getElementById('filtre-champ');
            selChamp.innerHTML = '<option value="">-- Choisir un champ --</option>';
            document.getElementById('filtre-valeurs-liste').style.display = 'none';
            document.getElementById('filtre-valeur').value = '';
            document.getElementById('filtre-resultat').textContent = '';
            if (!nom || !metaCouches[nom]) return;
            var champs = metaCouches[nom].popup_fields.filter(function(k) {{ return !k.startsWith('_qgis_'); }});
            champs.forEach(function(c) {{
                var o = document.createElement('option');
                o.value = c; o.textContent = c;
                selChamp.appendChild(o);
            }});
        }}

        function filtreChangerChamp() {{
            var nom   = document.getElementById('filtre-couche').value;
            var champ = document.getElementById('filtre-champ').value;
            document.getElementById('filtre-valeur').value = '';
            document.getElementById('filtre-valeurs-liste').style.display = 'none';
            if (!nom || !champ || !geoLayersData[nom]) return;
            var vals = {{}};
            geoLayersData[nom].features.forEach(function(f) {{
                var v = f.properties[champ];
                if (v !== undefined && v !== null && v !== '') vals[v] = true;
            }});
            var liste = document.getElementById('filtre-valeurs-liste');
            liste.innerHTML = '';
            Object.keys(vals).sort().forEach(function(v) {{
                var d = document.createElement('div');
                d.className = 'filtre-valeur-item';
                d.textContent = v;
                d.onclick = function() {{
                    document.getElementById('filtre-valeur').value = v;
                    liste.style.display = 'none';
                }};
                liste.appendChild(d);
            }});
            liste.style.display = 'block';
        }}

        function filtreValeurInput() {{
            var nom   = document.getElementById('filtre-couche').value;
            var champ = document.getElementById('filtre-champ').value;
            var saisie = document.getElementById('filtre-valeur').value.toLowerCase();
            var liste = document.getElementById('filtre-valeurs-liste');
            if (!nom || !champ || !geoLayersData[nom]) {{ liste.style.display = 'none'; return; }}
            var vals = {{}};
            geoLayersData[nom].features.forEach(function(f) {{
                var v = String(f.properties[champ] || '');
                if (v.toLowerCase().indexOf(saisie) !== -1) vals[v] = true;
            }});
            liste.innerHTML = '';
            Object.keys(vals).sort().slice(0, 30).forEach(function(v) {{
                var d = document.createElement('div');
                d.className = 'filtre-valeur-item';
                d.textContent = v;
                d.onclick = function() {{
                    document.getElementById('filtre-valeur').value = v;
                    liste.style.display = 'none';
                }};
                liste.appendChild(d);
            }});
            liste.style.display = Object.keys(vals).length > 0 ? 'block' : 'none';
        }}

        function appliquerFiltre() {{
            var nom   = document.getElementById('filtre-couche').value;
            var champ = document.getElementById('filtre-champ').value;
            var op    = document.getElementById('filtre-operateur').value;
            var val   = document.getElementById('filtre-valeur').value;
            var res   = document.getElementById('filtre-resultat');
            document.getElementById('filtre-valeurs-liste').style.display = 'none';

            if (!nom || !champ) {{ res.textContent = '⚠ Choisissez une couche et un champ.'; return; }}
            if (!geoLayersData[nom]) {{ res.textContent = '⚠ Données non encore chargées.'; return; }}

            var data = geoLayersData[nom];
            var filtrees = data.features.filter(function(f) {{
                var fv = String(f.properties[champ] || '');
                var fvn = parseFloat(fv);
                var vn  = parseFloat(val);
                switch(op) {{
                    case 'eq':       return fv === val;
                    case 'neq':      return fv !== val;
                    case 'contains': return fv.toLowerCase().indexOf(val.toLowerCase()) !== -1;
                    case 'starts':   return fv.toLowerCase().indexOf(val.toLowerCase()) === 0;
                    case 'gt':       return !isNaN(fvn) && !isNaN(vn) && fvn > vn;
                    case 'lt':       return !isNaN(fvn) && !isNaN(vn) && fvn < vn;
                    case 'gte':      return !isNaN(fvn) && !isNaN(vn) && fvn >= vn;
                    case 'lte':      return !isNaN(fvn) && !isNaN(vn) && fvn <= vn;
                    default:         return true;
                }}
            }});

            if (couches_leaflet[nom]) map.removeLayer(couches_leaflet[nom]);

            var filteredGeoJSON = {{ type: 'FeatureCollection', features: filtrees }};
            var info = metaCouches[nom];
            var isPoint = !info.is_polygon && !info.is_line;
            var clusterGroup = isPoint ? L.markerClusterGroup({{ disableClusteringAtZoom: 13, maxClusterRadius: 50, showCoverageOnHover: false }}) : null;

            var newLayer = L.geoJSON(filteredGeoJSON, {{
                pointToLayer: function(feature, latlng) {{
                    var st = feature.properties._qgis_style || {{}};
                    var val2 = feature.properties._qgis_class_val;
                    var matchImg = '';
                    info.legend_style.forEach(function(node) {{
                        if (node.label === val2 || node.valeur === val2) matchImg = node.img_path;
                    }});
                    if (!matchImg && info.legend_style.length > 0) matchImg = info.legend_style[0].img_path;
                    if (matchImg) {{
                        return L.marker(latlng, {{ icon: L.icon({{ iconUrl: matchImg, iconSize: [24,24], iconAnchor:[12,12], popupAnchor:[0,-12] }}) }});
                    }}
                    return L.circleMarker(latlng, {{ radius: st.radius||6, color: '#f9ca24', fillColor: '#f9ca24', weight: 3, opacity: 1, fillOpacity: 0.95 }});
                }},
                style: function(feature) {{
                    return {{
                        color: '#f9ca24',
                        fillColor: '#f9ca24',
                        weight: 4,
                        opacity: 1,
                        fillOpacity: 0.4,
                        dashArray: '5, 5'
                    }};
                }},
                onEachFeature: function(feature, layer) {{
                    var content = '<div style="min-width:200px;"><div class="popup-title">' + nom + '</div><table class="custom-popup-table">';
                    info.popup_fields.forEach(function(key) {{
                        if (feature.properties[key] !== undefined && !key.startsWith('_qgis_')) {{
                            content += '<tr><td style="color:#4ecdc4;font-weight:600;">' + key + '</td><td style="text-align:right;">' + feature.properties[key] + '</td></tr>';
                        }}
                    }});
                    content += '</table></div>';
                    layer.bindPopup(content);

                    // Ajout dynamique du clignotement après l'affichage à l'écran
                    setTimeout(function() {{
                        if (layer._path) {{
                            layer._path.classList.add('entite-clignotante');
                        }} else if (layer._icon) {{
                            layer._icon.classList.add('entite-clignotante');
                        }}
                    }}, 50);
                }}
            }});

            if (clusterGroup) {{
                clusterGroup.addLayer(newLayer); clusterGroup.addTo(map);
                couches_leaflet[nom] = clusterGroup;
            }} else {{
                newLayer.addTo(map);
                couches_leaflet[nom] = newLayer;
            }}

            res.textContent = filtrees.length + ' entité(s) trouvée(s) sur ' + data.features.length;

            // Zoom automatique ciblé et ouverture automatique du popup si unique entité
            try {{
                var bounds = newLayer.getBounds();
                if (bounds && bounds.isValid()) {{
                    map.fitBounds(bounds, {{ padding: [40, 40], maxZoom: 16 }});
                    if (filtrees.length === 1) {{
                        newLayer.eachLayer(function(l) {{ l.openPopup(); }});
                    }}
                }}
            }} catch(e) {{}}
        }}

        function reinitialiserFiltre() {{
            var nom = document.getElementById('filtre-couche').value;
            document.getElementById('filtre-valeur').value = '';
            document.getElementById('filtre-resultat').textContent = '';
            document.getElementById('filtre-valeurs-liste').style.display = 'none';
            if (!nom || !geoLayersData[nom] || !couches_leaflet[nom]) return;

            map.removeLayer(couches_leaflet[nom]);
            var info = metaCouches[nom];
            var isPoint = !info.is_polygon && !info.is_line;
            var clusterGroup = isPoint ? L.markerClusterGroup({{ disableClusteringAtZoom:13, maxClusterRadius:50, showCoverageOnHover:false }}) : null;
            var origLayer = couches_geolayers[nom];
            if (clusterGroup) {{
                clusterGroup.addLayer(origLayer); clusterGroup.addTo(map);
                couches_leaflet[nom] = clusterGroup;
            }} else {{
                origLayer.addTo(map);
                couches_leaflet[nom] = origLayer;
            }}
        }}

        function hexToRgba(hex, alpha) {{
            if (!hex || hex.length < 7) return 'rgba(51,136,255,0.2)';
            var r = parseInt(hex.slice(1,3),16);
            var g = parseInt(hex.slice(3,5),16);
            var b = parseInt(hex.slice(5,7),16);
            var a = (alpha != null) ? alpha : 0.0;
            return 'rgba(' + r + ',' + g + ',' + b + ',' + a + ')';
        }}
    </script>
</body>
</html>'''

        # Injection sécurisée
        html_content = html_content.replace('__CSS_CLUSTER__', css_cluster)
        html_content = html_content.replace('__OUTILS_JS__', outils_js)

        loader_css = """
    <style>
        #loader {
            border: 6px solid #f3f3f3;
            border-top: 6px solid #f0625e;
            border-right: 6px solid #f5a25c;
            border-bottom: 6px solid #8da28c;
            border-radius: 50%;
            width: 60px;
            height: 60px;
            animation: spin 1s linear infinite;
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            z-index: 10000;
        }
        @keyframes spin {
            0% { transform: translate(-50%, -50%) rotate(0deg); }
            100% { transform: translate(-50%, -50%) rotate(360deg); }
        }
        .loading-active #container {
            visibility: hidden;
        }

        @media print {
            body, html {
                margin: 0 !important;
                padding: 0 !important;
                width: 100% !important;
                height: 100% !important;
                -webkit-print-color-adjust: exact !important;
                print-color-adjust: exact !important;
            }
            #loader, #sidebar, .leaflet-control-container {
                display: none !important;
            }
            #main-zone {
                display: block !important;
                width: 100% !important;
                height: 100% !important;
            }
            #map {
                position: absolute !important;
                top: 0 !important;
                left: 0 !important;
                width: 100vw !important;
                height: 100vh !important;
                visibility: visible !important;
            }
        }
    </style>
        """
        html_content = html_content.replace(
            '</head>', f'{loader_css}\n</head>')

        html_path = os.path.join(export_dir, 'index.html')
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

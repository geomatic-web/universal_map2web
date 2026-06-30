# Universal Map2web

**Exportez vos couches QGIS en cartes web interactives avec Leaflet !**

[![QGIS Plugin](https://img.shields.io/badge/QGIS-Plugin-brightgreen)](https://github.com/geomatic-web/universal-map2web)
[![Version](https://img.shields.io/badge/version-1.0.0-blue)](https://github.com/geomatic-web/universal_map2web)
[![License](https://img.shields.io/badge/license-GPLv2-orange)](https://github.com/geomatic-web/universal_map2web)

## À propos

Universal Map2web est une extension QGIS qui exporte vos couches vectorielles en cartes web interactives avec **Leaflet**, en préservant **fidèlement la symbologie et les styles de votre projet QGIS**.

## Fonctionnalités

- 1 **Préservation de la symbologie QGIS** (couleurs, épaisseurs, opacités, styles de ligne)
- 2 **Support de tous les renderers** : Simple, Catégorisé, Gradué, Règle
- 3 **Étiquetage QGIS** (labeling) automatique
- 4 **Popups personnalisables** par couche
- 5 **Filtre avancé par attribut**
- 6 **Cluster de points** colorés
- 7 **Outils intégrés** : Mesure, Recherche, Géolocalisation, Plein écran, Échelle, MiniMap, Impression
- 8 **Thèmes d'interface** : Clair, Sombre, Professionnel, Coloré
- 9 **Logo et couleur d'en-tête personnalisables**
- 10 **Serveur local intégré** (évite les problèmes CORS)
- 11 **Export PNG, PDF et CSV**

## Captures d'écran

![alt text](image.png)

## Installation

### Depuis le dépôt officiel QGIS

1. Ouvrez QGIS
2. Allez dans `Extensions` → `Gérer et installer les extensions...`
3. Recherchez `Universal Map2web`
4. Cliquez sur `Installer`

### Depuis GitHub

1. Téléchargez le dossier `universal_map2web`
2. Copiez-le dans le dossier des plugins QGIS :
   - Windows : `C:\Users\VotreNom\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins\`
   - Linux : `~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/`
   - Mac : `~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/`
3. Activez l'extension dans QGIS

## Utilisation

1. Cliquez sur l'icône `Universal Map2web` dans la barre d'outils
2. Sélectionnez les couches à exporter
3. Personnalisez les options (titre, logo, thème, etc.)
4. Cliquez sur `OK`
5. La carte s'ouvre automatiquement dans votre navigateur

## Dépendances

- QGIS 3.16 ou supérieur
- Navigateur web moderne (Chrome, Firefox, Edge, Safari)

## Licence

Ce projet est sous licence GNU GPL v2. Voir le fichier [LICENSE](LICENSE) pour plus de détails.

## 👤 Auteur

**Jean-baptiste Bazikité KIBORA**

- Email : jeanbaptiste.kibora@tic.gov.bf
- GitHub : [@geomatic-web](https://github.com/geomatic-web)

## Remerciements

- [QGIS](https://qgis.org) - Le meilleur SIG open source
- [Leaflet](https://leafletjs.com) - La bibliothèque cartographique JavaScript
- [qgis2web](https://github.com/tomchadwin/qgis2web) - Source d'inspiration

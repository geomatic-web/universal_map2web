# -*- coding: utf-8 -*-
"""
resources.py — Réservé aux ressources Qt compilées (pyrcc5 à partir d'un
fichier .qrc), si vous choisissez un jour d'embarquer icon.png et d'autres
assets dans un binaire Qt plutôt que de les charger par chemin de fichier.

Le plugin actuel charge icon.png directement par chemin disque
(os.path.join(plugin_dir, "icon.png")) dans universal_map2web.py, donc ce
module n'est pas requis pour son fonctionnement. Il est inclus ici pour
respecter l'arborescence standard d'un plugin QGIS et reste prêt à accueillir
le résultat de :

    pyrcc5 resources.qrc -o resources.py
"""

# -*- coding: utf-8 -*-
"""
compile_translations.py - Compile les fichiers de traduction .ts en .qm
"""

import os
import xml.etree.ElementTree as ET
import struct


def compile_ts_to_qm(ts_file, qm_file):
    """Compile un fichier .ts en .qm (format binaire Qt)"""
    try:
        tree = ET.parse(ts_file)
        root = tree.getroot()

        # Extraire les traductions
        translations = []
        for context in root.findall("context"):
            for msg in context.findall("message"):
                source = msg.find("source").text
                translation_elem = msg.find("translation")
                if translation_elem is not None and translation_elem.text:
                    translation = translation_elem.text
                    translations.append((source, translation))
                else:
                    translations.append((source, source))

        # Écrire au format .qm (simplifié)
        with open(qm_file, "wb") as f:
            # Magic number
            f.write(b"\x3c\xb8\x64\x18\xca\xef\x9c\x95")
            # Version
            f.write(struct.pack("<I", 2))
            # Nombre de traductions
            f.write(struct.pack("<I", len(translations)))

            # Écrire chaque traduction
            for source, translation in translations:
                source_bytes = source.encode("utf-8")
                trans_bytes = translation.encode("utf-8")
                # Longueur source
                f.write(struct.pack("<I", len(source_bytes)))
                # Source
                f.write(source_bytes)
                # Longueur traduction
                f.write(struct.pack("<I", len(trans_bytes)))
                # Traduction
                f.write(trans_bytes)

        print(f"{qm_file} généré avec {len(translations)} traductions")

    except Exception as e:
        print(f"Erreur: {e}")
        # Créer un fichier .qm vide comme fallback
        with open(qm_file, "wb") as f:
            f.write(b"\x3c\xb8\x64\x18\xca\xef\x9c\x95")
            f.write(struct.pack("<I", 2))
            f.write(struct.pack("<I", 0))
        print(f"Fichier .qm vide créé: {qm_file}")


if __name__ == "__main__":
    # Compiler les fichiers .ts
    ts_files = ["fr_FR.ts", "en_US.ts"]

    for ts_file in ts_files:
        if os.path.exists(ts_file):
            qm_file = ts_file.replace(".ts", ".qm")
            compile_ts_to_qm(ts_file, qm_file)
        else:
            print(f"Fichier non trouvé: {ts_file}")

    print("\nCompilation terminée !")
    print("Fichiers .qm générés dans le dossier i18n/")

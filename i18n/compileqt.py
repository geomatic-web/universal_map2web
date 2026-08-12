import os
import subprocess


def compile_translations():
    """Compile tous les fichiers .ts en .qm"""
    current_dir = os.getcwd()

    # ✅ Spécifier le chemin complet vers lrelease
    # Adaptez ce chemin selon votre installation de Qt
    lrelease_paths = [
        r"C:\Qt\6.5.0\msvc2019_64\bin\lrelease.exe",  # Qt6
        r"C:\Qt\6.5.0\mingw_64\bin\lrelease.exe",
        r"C:\Qt\5.15.2\msvc2019_64\bin\lrelease.exe",  # Qt5
        r"C:\Qt\Qt5.14.2\5.14.2\mingw73_64\bin\lrelease.exe",
        r"C:\Program Files\QGIS 3.34\bin\lrelease.exe",  # QGIS intégré
        r"C:\Program Files\QGIS 3.28\bin\lrelease.exe",
        r"C:\Program Files\QGIS 3.22\bin\lrelease.exe",
        r"C:\Program Files\QGIS 3.16\bin\lrelease.exe",
        r"C:\Python312\Scripts\pyside6-lrelease.exe",  # PySide6
    ]

    # Trouver la première installation valide
    lrelease = None
    for path in lrelease_paths:
        if os.path.exists(path):
            lrelease = path
            break

    if not lrelease:
        print("❌ lrelease.exe introuvable !")
        print("   Veuillez installer Qt ou PySide6.")
        print("   Ou installez PySide6 avec : pip install pyside6")
        return

    print(f"✅ Utilisation de : {lrelease}")

    for file in os.listdir(current_dir):
        if file.endswith(".ts"):
            ts_path = os.path.join(current_dir, file)
            qm_path = ts_path.replace(".ts", ".qm")

            print(f"🔨 Compilation de {file}...")
            result = subprocess.run(
                [lrelease, ts_path, "-qm", qm_path],
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                print(f"✅ Compilé : {file} → {os.path.basename(qm_path)}")
            else:
                print(f"❌ Erreur lors de la compilation de {file}: {result.stderr}")


if __name__ == "__main__":
    compile_translations()

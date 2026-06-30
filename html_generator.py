# -*- coding: utf-8 -*-
"""
html_generator.py — Assemble la page web finale d'un export à partir des templates
statiques (templates/index.html, templates/style.css, templates/app.js) et des
réglages choisis dans le dialogue (titre, thème, fond de plan, logo, outils...).
"""

import base64
import os
import shutil

from .leaflet_generator import build_extra_libs, render_app_js

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")

FOND_URLS = {
    "🌍 OpenStreetMap": "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    "🛰️ Google Satellite": "https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}",
    "🌐 Google Hybrid": "https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}",
}

THEMES = {
    "Clair": {
        "bg_body": "#f4f5f7", "bg_sidebar": "rgba(255,255,255,0.97)",
        "bg_panel": "rgba(0,0,0,0.03)", "bg_select": "#ffffff",
        "text_main": "#1a1a2e", "text_muted": "#666666",
        "accent": "#1a8a7f", "border": "rgba(0,0,0,0.1)",
        "popup_bg": "#ffffff", "popup_text": "#1a1a2e",
    },
    "Sombre": {
        "bg_body": "#1a1a2e", "bg_sidebar": "rgba(26,26,46,0.97)",
        "bg_panel": "rgba(255,255,255,0.02)", "bg_select": "#252538",
        "text_main": "#ffffff", "text_muted": "#bbbbbb",
        "accent": "#4ecdc4", "border": "rgba(255,255,255,0.1)",
        "popup_bg": "#1a1a2e", "popup_text": "#ffffff",
    },
    "Professionnel": {
        "bg_body": "#eef1f5", "bg_sidebar": "rgba(255,255,255,0.98)",
        "bg_panel": "rgba(15,40,75,0.04)", "bg_select": "#ffffff",
        "text_main": "#0f284b", "text_muted": "#5a6b80",
        "accent": "#0f6e9e", "border": "rgba(15,40,75,0.15)",
        "popup_bg": "#ffffff", "popup_text": "#0f284b",
    },
    "Coloré": {
        "bg_body": "#2b1a3d", "bg_sidebar": "rgba(43,26,61,0.97)",
        "bg_panel": "rgba(255,255,255,0.04)", "bg_select": "#3d2455",
        "text_main": "#ffffff", "text_muted": "#d8c4ee",
        "accent": "#ff6b9d", "border": "rgba(255,255,255,0.15)",
        "popup_bg": "#3d2455", "popup_text": "#ffffff",
    },
}


def _opt(dialog, nom, defaut=False):
    w = getattr(dialog, nom, None)
    return w.isChecked() if w else defaut


def _lire_options(dialog):
    return {
        "geoloc": _opt(dialog, "chkGeoloc"),
        "mesure": _opt(dialog, "chkMesure"),
        "pleinecran": _opt(dialog, "chkPleinEcran"),
        "echelle": _opt(dialog, "chkScale", True),
        "recherche": _opt(dialog, "chkRecherche"),
        "minimap": _opt(dialog, "chkMiniMap"),
        "mousepos": _opt(dialog, "chkMousePosition"),
        "imprimer": _opt(dialog, "chkImprimer"),
        "attribution": _opt(dialog, "chkAttribution", True),
    }


def _lire_logo_base64(dialog):
    afficher_logo = dialog.chkAfficherLogo.isChecked()
    logo_path = (
        dialog.lblLogoPath.toolTip()
        if (afficher_logo and dialog.lblLogoPath.toolTip() != "Aucun logo")
        else None
    )
    if not logo_path or not os.path.exists(logo_path):
        return None
    try:
        with open(logo_path, "rb") as f:
            ext = os.path.splitext(logo_path)[1][1:].lower()
            if ext in ("jpg", "jpeg"):
                ext = "jpeg"
            return f"data:image/{ext};base64,{
                base64.b64encode(
                    f.read()).decode('utf-8')}"
    except Exception:
        return None


def generer_export(dialog, export_data, output_dir):
    """Génère index.html, style.css et app.js dans output_dir à partir des templates
    statiques et des réglages du dialogue. `export_data` est le dict couche -> métadonnées
    produit par l'export (fichier geojson, styles de légende, champs popup...)."""
    titre = dialog.txtTitreCarte.text()
    couleur_entete = dialog.txtCouleurEntete.text() or "#1a1a2e"

    logo_base64 = _lire_logo_base64(dialog)
    html_logo = f'<div class="logo-container"><img src="{logo_base64}" alt="Logo"/></div>' if logo_base64 else ""

    fond_plan = dialog.comboFondPlan.currentText()
    url_fond = FOND_URLS.get(fond_plan, FOND_URLS["🌍 OpenStreetMap"])

    theme_nom = dialog.comboTheme.currentText() if hasattr(
        dialog, "comboTheme") else "Sombre"
    th = THEMES.get(theme_nom, THEMES["Sombre"])

    options = _lire_options(dialog)
    extra_css, extra_js = build_extra_libs(options)

    mousepos_html = (
        '<div id="mouse-pos" style="position:absolute;bottom:28px;left:5px;'
        "background:rgba(0,0,0,0.65);color:#fff;padding:3px 8px;border-radius:4px;"
        'font-size:11px;z-index:999;pointer-events:none;"></div>'
        if options.get("mousepos")
        else ""
    )

    # ── index.html ──────────────────────────────────────────────
    with open(os.path.join(TEMPLATES_DIR, "index.html"), "r", encoding="utf-8") as f:
        index_html = f.read()

    remplacements = {
        "__TITRE__": titre,
        "__EXTRA_CSS__": extra_css,
        "__EXTRA_JS__": extra_js,
        "__HTML_LOGO__": html_logo,
        "__MOUSEPOS_HTML__": mousepos_html,
        "__HEADER_COLOR__": couleur_entete,
        "__BG_BODY__": th["bg_body"],
        "__BG_SIDEBAR__": th["bg_sidebar"],
        "__BG_PANEL__": th["bg_panel"],
        "__BG_SELECT__": th["bg_select"],
        "__TEXT_MAIN__": th["text_main"],
        "__TEXT_MUTED__": th["text_muted"],
        "__ACCENT__": th["accent"],
        "__BORDER__": th["border"],
        "__POPUP_BG__": th["popup_bg"],
        "__POPUP_TEXT__": th["popup_text"],
    }
    for marqueur, valeur in remplacements.items():
        index_html = index_html.replace(marqueur, valeur)

    with open(os.path.join(output_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(index_html)

    # ── style.css (statique, le thème passe par les variables CSS de index.html) ──
    shutil.copyfile(
        os.path.join(TEMPLATES_DIR, "style.css"),
        os.path.join(output_dir, "style.css"),
    )

    # ── app.js (métadonnées des couches + outils optionnels injectés) ──
    render_app_js(
        export_data,
        url_fond,
        options,
        os.path.join(
            output_dir,
            "app.js"))

var I18N = JSON.parse('__I18N_JSON__');
var metaCouches = JSON.parse('__META_COUCHES_JSON__');
// preferCanvas : rendu Canvas par défaut pour toutes les couches vectorielles
var map = L.map('map', {zoomControl: true, preferCanvas: true}).setView([0, 0], 2);

// Renderer SVG partagé pour les motifs de remplissage
var svgRendererPartage = L.svg({padding: 0.5});

// Cache des <pattern> SVG déjà créés
var motifsSvgEnregistres = {};

function idMotifValide(cheminImg) {
    return 'motif-' + cheminImg.replace(/[^a-zA-Z0-9_-]/g, '_');
}

function assurerMotifSVG(motif) {
    if (!motif || !motif.img) return null;
    var id = idMotifValide(motif.img);
    if (motifsSvgEnregistres[id]) return 'url(#' + id + ')';

    if (!svgRendererPartage._container) {
        svgRendererPartage.addTo(map);
    }
    var svgRoot = svgRendererPartage._container;
    if (!svgRoot) return null;

    var NS = 'http://www.w3.org/2000/svg';
    var defs = svgRoot.querySelector('defs');
    if (!defs) {
        defs = document.createElementNS(NS, 'defs');
        svgRoot.insertBefore(defs, svgRoot.firstChild);
    }

    var taille = motif.taille || 16;
    var pattern = document.createElementNS(NS, 'pattern');
    pattern.setAttribute('id', id);
    pattern.setAttribute('patternUnits', 'userSpaceOnUse');
    pattern.setAttribute('width', taille);
    pattern.setAttribute('height', taille);

    var image = document.createElementNS(NS, 'image');
    image.setAttributeNS('http://www.w3.org/1999/xlink', 'href', motif.img);
    image.setAttribute('href', motif.img);
    image.setAttribute('x', 0);
    image.setAttribute('y', 0);
    image.setAttribute('width', taille);
    image.setAttribute('height', taille);
    pattern.appendChild(image);

    defs.appendChild(pattern);
    motifsSvgEnregistres[id] = true;
    return 'url(#' + id + ')';
}

var baseLayers = {
    "BASE": L.tileLayer("__URL_FOND__", {maxZoom: 20, crossOrigin: true}),
    "OSM": L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {maxZoom: 19, crossOrigin: true}),
    "SAT": L.tileLayer("https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}", {maxZoom: 20})
};
baseLayers["BASE"].addTo(map);

function changerFond() {
    var sel = document.getElementById('fondSelector').value;
    for (var k in baseLayers) {map.removeLayer(baseLayers[k]); }
    baseLayers[sel].addTo(map);
}

__OUTILS_JS__

// ── Style dynamique pour les couches PostgreSQL ──────────────
function normaliserValeurClassification(v) {
    if (v === null || v === undefined) return '';
    if (typeof v === 'boolean') return v ? 'true' : 'false';
    if (typeof v === 'number') {
        if (Number.isInteger(v)) return String(v);
        var s = String(parseFloat(v.toPrecision(12)));
        return s;
    }
    return String(v).trim();
}

function resoudreStylePostgres(feature, info) {
    var attr = info.attr_classif;
    var carte = info.style_map || {};
    var styleDefaut = info.style_defaut || {
        color: '#3388ff', fillColor: '#3388ff', weight: 1,
        opacity: 1, fillOpacity: 0.6, radius: 8
    };

    var valBrute = null;
    if (attr) {
        if (Object.prototype.hasOwnProperty.call(feature.properties, attr)
                && feature.properties[attr] !== null) {
            valBrute = feature.properties[attr];
        } else {
            var attrLower = attr.toLowerCase();
            for (var k in feature.properties) {
                if (k.toLowerCase() === attrLower && feature.properties[k] !== null) {
                    valBrute = feature.properties[k];
                    break;
                }
            }
        }
    }
    var val = (valBrute !== null) ? normaliserValeurClassification(valBrute) : '';

    feature.properties._qgis_class_val = val || 'default';

    if (carte['__plages__']) {
        var num = parseFloat(valBrute);
        var style = styleDefaut;
        if (!isNaN(num)) {
            for (var i = 0; i < carte['__plages__'].length; i++) {
                var plage = carte['__plages__'][i];
                if (num >= plage[0] && num <= plage[1]) {
                    style = plage[2];
                    break;
                }
            }
        }
        feature.properties._qgis_style = style;
    } else if (Object.prototype.hasOwnProperty.call(carte, val)) {
        feature.properties._qgis_style = carte[val];
    } else {
        var valSouple = val.trim().toLowerCase();
        var cleTrouvee = null;
        Object.keys(carte).forEach(function(cle) {
            if (cleTrouvee || cle === '__plages__') return;
            if (cle.trim().toLowerCase() === valSouple) cleTrouvee = cle;
        });
        if (cleTrouvee !== null) {
            feature.properties._qgis_style = carte[cleTrouvee];
        } else if (carte['default']) {
            feature.properties._qgis_style = carte['default'];
        } else {
            feature.properties._qgis_style = styleDefaut;
        }
    }
}

function appliquerStyleFeat(feature, styleInfo) {
    if (!styleInfo) return {};

    let styleApplicable = styleInfo;
    if (styleInfo.style_map || styleInfo.__plages__) {
        styleApplicable = resoudreStylePostgres(feature, styleInfo) || styleInfo.default;
    }

    if (styleApplicable && styleApplicable.motifs) {
        assurerMotifSVG(styleApplicable.motifs);
        return {
            fillColor: 'url(#' + styleApplicable.motifs + ')',
            fillOpacity: styleApplicable.fillOpacity || 0.8,
            color: styleApplicable.color || '#333',
            weight: styleApplicable.weight || 1,
            renderer: svgRendererPartage
        };
    }

    return {
        fillColor: styleApplicable.fillColor || styleApplicable.color || '#3388ff',
        fillOpacity: styleApplicable.fillOpacity !== undefined ? styleApplicable.fillOpacity : 0.5,
        color: styleApplicable.color || '#3388ff',
        weight: styleApplicable.weight || 2,
        dashArray: styleApplicable.dashArray || null
    };
}

// ── Utilitaires couleur ──────────────────────────────────────
function hexToRgba(hex, alpha) {
    if (!hex || hex.length < 7) return 'rgba(51,136,255,0.2)';
    var r = parseInt(hex.slice(1,3),16);
    var g = parseInt(hex.slice(3,5),16);
    var b = parseInt(hex.slice(5,7),16);
    var a = (alpha != null) ? alpha : 0.0;
    return 'rgba(' + r + ',' + g + ',' + b + ',' + a + ')';
}

function texteContrastant(hex) {
    if (!hex || hex.length < 7) return '#fff';
    var r = parseInt(hex.slice(1,3),16), g = parseInt(hex.slice(3,5),16), b = parseInt(hex.slice(5,7),16);
    var luminance = (0.299*r + 0.587*g + 0.114*b) / 255;
    return luminance > 0.6 ? '#1a1a2e' : '#ffffff';
}

function appliquerStyleEtiquette(element, etiquetteInfo) {
    if (!element || !etiquetteInfo) return;
    
    if (etiquetteInfo.couleur) element.style.color = etiquetteInfo.couleur;
    if (etiquetteInfo.taille) {
        var tailleWeb = Math.min(Math.max(parseInt(etiquetteInfo.taille) * 0.85, 8), 11);
        element.style.fontSize = tailleWeb + 'pt';
    } else {
        element.style.fontSize = '8.5pt';
    }
    
    if (etiquetteInfo.tampon_actif) {
        var c = etiquetteInfo.tampon_couleur || '#ffffff';
        var t = Math.min(etiquetteInfo.tampon_taille || 1, 1.5);
        
        element.style.textShadow = 
            '-' + t + 'px -' + t + 'px 0 ' + c + ', ' +
             t + 'px -' + t + 'px 0 ' + c + ', ' +
            '-' + t + 'px  ' + t + 'px 0 ' + c + ', ' +
             t + 'px  ' + t + 'px 0 ' + c + ', ' +
            '0px -' + t + 'px 0 ' + c + ', ' +
            '0px  ' + t + 'px 0 ' + c + ', ' +
            '-' + t + 'px 0px 0 ' + c + ', ' +
             t + 'px 0px 0 ' + c;
    }
}

function fabriqueIconeCluster(couleurBase) {
    return function(cluster) {
        var n = cluster.getChildCount();
        var taille = n < 10 ? 32 : (n < 50 ? 40 : 48);
        return L.divIcon({
            html: '<div class="custom-marker-cluster" style="width:' + taille + 'px;height:' + taille + 'px;'
                + 'background-color:' + hexToRgba(couleurBase, 0.85) + ';color:' + texteContrastant(couleurBase) + ';'
                + 'font-size:' + (taille > 36 ? 13 : 11) + 'px;">' + n + '</div>',
            className: '',
            iconSize: L.point(taille, taille),
            iconAnchor: L.point(taille/2, taille/2)
        });
    };
}

var couches_leaflet   = {};
var couches_geolayers = {};
var couches_cluster_color = {};
var geoLayersData     = {};
var promesses_chargement = [];
var legendContainer = document.getElementById('legende-liste');

function construireLayer(nom, info, data, activerCluster) {
    var isPoint = !!info.is_point;
    var isPolygon = !!info.is_polygon;
    var clusterGroup = null;
    var overlaysMotifs = [];

    var couleurCluster = '#4ecdc4';
    if (data.features && data.features.length > 0) {
        var stf = data.features[0].properties._qgis_style || {};
        if (stf.fillColor) couleurCluster = stf.fillColor;
        else if (stf.color) couleurCluster = stf.color;
    }
    couches_cluster_color[nom] = couleurCluster;

    if (isPoint && activerCluster) {
        clusterGroup = L.markerClusterGroup({
            disableClusteringAtZoom: 13,
            maxClusterRadius: 50,
            showCoverageOnHover: false,
            iconCreateFunction: function(cluster) {
                var enfants = cluster.getAllChildMarkers();
                var compteur = {};
                enfants.forEach(function(m) {
                    var c = (m.options && m.options.__qgisColor) || couleurCluster;
                    compteur[c] = (compteur[c] || 0) + 1;
                });
                var meilleureCouleur = couleurCluster, maxN = 0;
                Object.keys(compteur).forEach(function(c) {
                    if (compteur[c] > maxN) { maxN = compteur[c]; meilleureCouleur = c; }
                });
                return fabriqueIconeCluster(meilleureCouleur)(cluster);
            }
        });
    }

    var optionsGeoJSON = {
        pointToLayer: function(feature, latlng) {
            var st  = feature.properties._qgis_style || {};
            var val = feature.properties._qgis_class_val;

            if ((!st.color && !st.fillColor && !st.icone && !st.icon_url && !st.img_path) && (info.style_map || info.__plages__)) {
                st = resoudreStylePostgres(feature, info) || st;
            }

            var matchImg = st.icone || st.icon_url || st.img_path || '';

            if (!matchImg && info.legend_style) {
                info.legend_style.forEach(function(node) {
                    if (node.label === val || node.valeur === val) {
                        matchImg = node.img_path || node.icon_url;
                    }
                });
            }

            var marker;
            if (matchImg) {
                // ───────────── RESOLUTION DYNAMIQUE TAILLE DE L'ICÔNE ─────────────
                var iconW = 32, iconH = 32;
                var anchorX = 16, anchorY = 32;

                if (st.iconeProps && st.iconeProps.size) {
                    iconW = st.iconeProps.size[0];
                    iconH = st.iconeProps.size[1];
                    if (st.iconeProps.anchor) {
                        anchorX = st.iconeProps.anchor[0];
                        anchorY = st.iconeProps.anchor[1];
                    } else {
                        anchorX = Math.round(iconW / 2);
                        anchorY = iconH;
                    }
                } else if (st.iconSize) {
                    iconW = st.iconSize[0]; iconH = st.iconSize[1];
                    anchorX = Math.round(iconW / 2); anchorY = iconH;
                } else if (st.size) {
                    var sz = typeof st.size === 'number' ? st.size : 32;
                    iconW = sz; iconH = sz;
                    anchorX = Math.round(iconW / 2); anchorY = iconH;
                }

                marker = L.marker(latlng, { 
                    icon: L.icon({
                        iconUrl: matchImg, 
                        iconSize: [iconW, iconH],
                        iconAnchor: [anchorX, anchorY], 
                        popupAnchor: [0, -anchorY]
                    }) 
                });
            } else {
                marker = L.circleMarker(latlng, {
                    radius:      st.radius      || 8,
                    color:       st.color       || '#3388ff',
                    fillColor:   st.fillColor   || st.color || '#3388ff',
                    weight:      st.weight      != null ? st.weight      : 1.5,
                    opacity:     st.opacity     != null ? st.opacity     : 1,
                    fillOpacity: st.fillOpacity != null ? st.fillOpacity : 0.85
                });
            }
            marker.options.__qgisColor = st.fillColor || st.color || couleurCluster;

            if (info.etiquette && info.etiquette.champ && feature.properties[info.etiquette.champ] !== undefined) {
                marker.bindTooltip(String(feature.properties[info.etiquette.champ]), {
                    permanent: true, 
                    direction: 'right', 
                    className: 'qgis-label',
                    offset: [10, 0]
                });
                marker.getTooltip().options.opacity = 1;

                marker.on('add', function() {
                    var tt = marker.getTooltip();
                    if (tt && tt.getElement()) {
                        appliquerStyleEtiquette(tt.getElement(), info.etiquette);
                    }
                });
            }
            return marker;
        },

        style: function(feature) {
            var s = (feature.properties && feature.properties._qgis_style) || {};

            if ((!s.color && !s.fillColor) && (info.style_map || info.__plages__)) {
                s = resoudreStylePostgres(feature, info) || s;
            }

            return {
                color:       s.color       || '#3388ff',
                fillColor:   s.fillColor   || s.color || '#3388ff',
                weight:      s.weight      != null ? s.weight      : 1.0,
                opacity:     s.opacity     != null ? s.opacity     : 1.0,
                fillOpacity: (s.fillOpacity != null) ? s.fillOpacity : 0.0,
                dashArray:   s.dashArray   || null
            };
        },

        onEachFeature: function(feature, layer) {
            var content = '<div style="min-width:200px;">'
                + '<div class="popup-title">' + nom + '</div>'
                + '<table class="custom-popup-table">';
            (info.popup_fields || []).forEach(function(key) {
                if (feature.properties[key] !== undefined && !key.startsWith('_qgis_')) {
                    content += '<tr>'
                        + '<td style="color:#4ecdc4;font-weight:600;">' + key + '</td>'
                        + '<td style="text-align:right;">' + feature.properties[key] + '</td>'
                        + '</tr>';
                }
            });
            content += '</table></div>';
            layer.bindPopup(content);

            if (info.etiquette && info.etiquette.champ && feature.properties[info.etiquette.champ] !== undefined && !isPoint) {
                layer.bindTooltip(String(feature.properties[info.etiquette.champ]), {
                    permanent: true, 
                    direction: 'center', 
                    className: 'qgis-label'
                });

                layer.on('add', function() {
                    var tt = layer.getTooltip();
                    if (tt && tt.getElement()) {
                        appliquerStyleEtiquette(tt.getElement(), info.etiquette);
                    }
                });
            }

            var stMotifs = (feature.properties && feature.properties._qgis_style) || {};
            if (isPolygon && stMotifs.motifs && stMotifs.motifs.length && layer.getLatLngs) {
                stMotifs.motifs.forEach(function(motif) {
                    var refMotif = assurerMotifSVG(motif);
                    if (!refMotif) return;
                    var overlay = L.polygon(layer.getLatLngs(), {
                        renderer: svgRendererPartage,
                        fillColor: refMotif,
                        fillOpacity: 1,
                        stroke: false,
                        interactive: false
                    });
                    overlaysMotifs.push(overlay);
                });
            }
        }
    };

    if (info.needs_svg) {
        optionsGeoJSON.renderer = svgRendererPartage;
    }

    var geoLayer = L.geoJSON(data, optionsGeoJSON);

    overlaysMotifs.forEach(function(overlay) {
        geoLayer.addLayer(overlay);
    });

    var resultat;
    if (clusterGroup) {
        clusterGroup.addLayer(geoLayer);
        resultat = clusterGroup;
    } else {
        resultat = geoLayer;
    }
    return { actif: resultat, brut: geoLayer };
}

// ── Rendu de la légende HTML ─────────────────────────────────
Object.keys(metaCouches).forEach(function(nom) {
    var info = metaCouches[nom];
    var safeId = nom.replace(/[^a-zA-Z0-9]/g, '_');

    var groupDiv = document.createElement('div');
    groupDiv.className = 'group-couche';
    groupDiv.innerHTML = '<div class="item-couche-tit">'
        + '<div class="item-couche-tit-gauche">'
        + '<input type="checkbox" id="chk_' + safeId + '" checked />'
        + '<label for="chk_' + safeId + '">' + nom + '</label>'
        + '</div>'
        + '<button class="btn-collapse" id="toggle_' + safeId + '" title="' + I18N.collapse_toggle_title + '">▾</button>'
        + '</div>'
        + '<div class="group-couche-corps" id="corps_' + safeId + '"></div>';

    var corps = groupDiv.querySelector('#corps_' + safeId);

    // Style d'image sécurisé pour la légende (ne se fait plus rogner)
    var imgStyleLegende = 'style="max-height:28px; max-width:28px; object-fit:contain; flex-shrink:0; vertical-align:middle; display:inline-block;"';

    if (info.is_polygon) {
        if (info.legend_style && info.legend_style.length > 0) {
            info.legend_style.forEach(function(node) {
                corps.innerHTML += '<div class="sous-legende-item">'
                    + '<img class="img-legend-icon" src="' + node.img_path + '" ' + imgStyleLegende + ' />'
                    + '<span>' + node.label + '</span></div>';
            });
        } else {
            corps.innerHTML += '<div class="sous-legende-item">'
                + '<span class="legend-poly-swatch" id="poly_leg_' + safeId + '"></span>'
                + '<span>' + nom + '</span></div>';
        }
    } else if (info.is_line) {
        if (info.legend_style && info.legend_style.length > 0) {
            info.legend_style.forEach(function(node, idx) {
                if (node.img_path) {
                    corps.innerHTML += '<div class="sous-legende-item">'
                        + '<img class="img-legend-icon" src="' + node.img_path + '" ' + imgStyleLegende + ' />'
                        + '<span>' + node.label + '</span></div>';
                } else {
                    corps.innerHTML += '<div class="sous-legende-item">'
                        + '<span class="legend-line-swatch" id="line_leg_' + safeId + '_' + idx + '" data-default="' + idx + '"></span>'
                        + '<span>' + node.label + '</span></div>';
                }
            });
        } else {
            corps.innerHTML += '<div class="sous-legende-item">'
                + '<span class="legend-line-swatch" id="line_leg_' + safeId + '_0"></span>'
                + '<span>' + nom + '</span></div>';
        }
    } else {
        (info.legend_style || []).forEach(function(node) {
            corps.innerHTML += '<div class="sous-legende-item">'
                + '<img class="img-legend-icon" src="' + node.img_path + '" ' + imgStyleLegende + ' />'
                + '<span>' + node.label + '</span></div>';
        });
        corps.innerHTML += '<div class="cluster-toggle-row">'
            + '<input type="checkbox" id="cluster_' + safeId + '" checked />'
            + '<label for="cluster_' + safeId + '">' + I18N.cluster_points_label + '</label></div>';
    }
    legendContainer.appendChild(groupDiv);

    var btnToggle = groupDiv.querySelector('#toggle_' + safeId);
    btnToggle.addEventListener('click', function() {
        corps.classList.toggle('is-collapsed');
        btnToggle.classList.toggle('is-collapsed');
    });

    var p = fetch(info.fichier)
        .then(function(r) { return r.json(); })
        .then(function(data) {
            if (info.source === 'postgres' && data.features) {
                data.features.forEach(function(f) {
                    resoudreStylePostgres(f, info);
                });
            }

            geoLayersData[nom] = data;

            if (data.features && data.features.length > 0) {
                if (info.is_polygon) {
                    var fs = data.features[0].properties._qgis_style || {};
                    var el = document.getElementById('poly_leg_' + safeId);
                    if (el) {
                        el.style.border = '2px solid ' + (fs.color || '#3388ff');
                        el.style.backgroundColor = hexToRgba(fs.fillColor || fs.color || '#3388ff', fs.fillOpacity);
                    }
                } else if (info.is_line) {
                    if (info.legend_style && info.legend_style.length > 0) {
                        info.legend_style.forEach(function(node, idx) {
                            var feat = data.features.find(function(f) {
                                var v = f.properties._qgis_class_val;
                                return v === node.label || v === node.valeur;
                            });
                            var stl = feat ? (feat.properties._qgis_style || {}) : {};
                            var elLine = document.getElementById('line_leg_' + safeId + '_' + idx);
                            if (elLine) {
                                elLine.style.backgroundColor = stl.color || '#3388ff';
                                elLine.style.height = Math.min(Math.max(stl.weight || 2, 2), 8) + 'px';
                            }
                        });
                    } else {
                        var fsL = data.features[0].properties._qgis_style || {};
                        var elL0 = document.getElementById('line_leg_' + safeId + '_0');
                        if (elL0) {
                            elL0.style.backgroundColor = fsL.color || '#3388ff';
                            elL0.style.height = Math.min(Math.max(fsL.weight || 2, 2), 8) + 'px';
                        }
                    }
                }
            }

            var clusterCheckbox = document.getElementById('cluster_' + safeId);
            var activerCluster = clusterCheckbox ? clusterCheckbox.checked : false;
            var construits = construireLayer(nom, info, data, activerCluster);

            couches_geolayers[nom] = construits.brut;
            couches_leaflet[nom]   = construits.actif;

            if (clusterCheckbox) {
                clusterCheckbox.addEventListener('change', function(e) {
                    var coche = document.getElementById('chk_' + safeId);
                    var visible = !coche || coche.checked;
                    if (couches_leaflet[nom] && map.hasLayer(couches_leaflet[nom])) {
                        map.removeLayer(couches_leaflet[nom]);
                    }
                    var reconstruits = construireLayer(nom, info, geoLayersData[nom], e.target.checked);
                    couches_geolayers[nom] = reconstruits.brut;
                    couches_leaflet[nom]   = reconstruits.actif;
                    if (visible) couches_leaflet[nom].addTo(map);
                });
            }

            return couches_leaflet[nom];
        });

    promesses_chargement.push(p);

    document.getElementById('chk_' + safeId).addEventListener('change', function(e) {
        if (e.target.checked && couches_leaflet[nom]) { map.addLayer(couches_leaflet[nom]); }
        else if (couches_leaflet[nom]) { map.removeLayer(couches_leaflet[nom]); }
    });
});

function ajusterVueSurDonnees(bounds) {
    map.invalidateSize(false);
    if (bounds && bounds.isValid()) {
        map.fitBounds(bounds, { padding: [30, 30], maxZoom: 19, animate: false });
    } else {
        map.setView([12.3, -1.5], 7);
    }
}

Promise.all(promesses_chargement).then(function() {
    Object.keys(metaCouches).forEach(function(nom) {
        var couche = couches_leaflet[nom];
        if (!couche) return;
        var safeId = nom.replace(/[^a-zA-Z0-9]/g, '_');
        var chk = document.getElementById('chk_' + safeId);
        var visible = !chk || chk.checked;
        if (visible) couche.addTo(map);
    });

    var bounds = null;
    Object.values(couches_leaflet).forEach(function(lg) {
        try {
            var b = lg.getBounds();
            if (b && b.isValid()) bounds = bounds ? bounds.extend(b) : b;
        } catch(e) {}
    });

    ajusterVueSurDonnees(bounds);
    requestAnimationFrame(function() { ajusterVueSurDonnees(bounds); });

    map.options.fadeAnimation = true;

    var loaderEl = document.getElementById('loader');
    if (loaderEl) loaderEl.style.display = 'none';
    document.body.classList.remove('loading-active');

    var selFiltre = document.getElementById('filtre-couche');
    Object.keys(metaCouches).forEach(function(nom) {
        var o = document.createElement('option');
        o.value = nom; o.textContent = nom;
        selFiltre.appendChild(o);
    });
});

// ═══════════════════════════════════════════════════════
// FILTRE AVANCÉ PAR ATTRIBUT
// ═══════════════════════════════════════════════════════
function toutDeplierLegende() {
    document.querySelectorAll('.group-couche-corps').forEach(function(el) {
        el.classList.remove('is-collapsed');
    });
    document.querySelectorAll('.btn-collapse').forEach(function(el) {
        el.classList.remove('is-collapsed');
    });
}

function toutReplierLegende() {
    document.querySelectorAll('.group-couche-corps').forEach(function(el) {
        el.classList.add('is-collapsed');
    });
    document.querySelectorAll('.btn-collapse').forEach(function(el) {
        el.classList.add('is-collapsed');
    });
}

function filtreChangerCouche() {
    var nom = document.getElementById('filtre-couche').value;
    var selChamp = document.getElementById('filtre-champ');
    selChamp.innerHTML = '<option value="">' + I18N.filter_choose_field + '</option>';
    document.getElementById('filtre-valeurs-liste').style.display = 'none';
    document.getElementById('filtre-valeur').value = '';
    document.getElementById('filtre-resultat').textContent = '';
    if (!nom || !metaCouches[nom]) return;
    var champs = (metaCouches[nom].popup_fields || []).filter(function(k) { return !k.startsWith('_qgis_'); });
    champs.forEach(function(c) {
        var o = document.createElement('option');
        o.value = c; o.textContent = c;
        selChamp.appendChild(o);
    });
}

function filtreChangerChamp() {
    var nom   = document.getElementById('filtre-couche').value;
    var champ = document.getElementById('filtre-champ').value;
    document.getElementById('filtre-valeur').value = '';
    document.getElementById('filtre-valeurs-liste').style.display = 'none';
    if (!nom || !champ || !geoLayersData[nom]) return;
    var vals = {};
    geoLayersData[nom].features.forEach(function(f) {
        var v = f.properties[champ];
        if (v !== undefined && v !== null && v !== '') vals[v] = true;
    });
    var liste = document.getElementById('filtre-valeurs-liste');
    liste.innerHTML = '';
    Object.keys(vals).sort().forEach(function(v) {
        var d = document.createElement('div');
        d.className = 'filtre-valeur-item';
        d.textContent = v;
        d.onclick = function() {
            document.getElementById('filtre-valeur').value = v;
            liste.style.display = 'none';
        };
        liste.appendChild(d);
    });
    liste.style.display = 'block';
}

function filtreValeurInput() {
    var nom   = document.getElementById('filtre-couche').value;
    var champ = document.getElementById('filtre-champ').value;
    var saisie = document.getElementById('filtre-valeur').value.toLowerCase();
    var liste = document.getElementById('filtre-valeurs-liste');
    if (!nom || !champ || !geoLayersData[nom]) { liste.style.display = 'none'; return; }
    var vals = {};
    geoLayersData[nom].features.forEach(function(f) {
        var v = String(f.properties[champ] || '');
        if (v.toLowerCase().indexOf(saisie) !== -1) vals[v] = true;
    });
    liste.innerHTML = '';
    Object.keys(vals).sort().slice(0, 30).forEach(function(v) {
        var d = document.createElement('div');
        d.className = 'filtre-valeur-item';
        d.textContent = v;
        d.onclick = function() {
            document.getElementById('filtre-valeur').value = v;
            liste.style.display = 'none';
        };
        liste.appendChild(d);
    });
    liste.style.display = Object.keys(vals).length > 0 ? 'block' : 'none';
}

function appliquerFiltre() {
    var nom   = document.getElementById('filtre-couche').value;
    var champ = document.getElementById('filtre-champ').value;
    var op    = document.getElementById('filtre-operateur').value;
    var val   = document.getElementById('filtre-valeur').value;
    var res   = document.getElementById('filtre-resultat');
    document.getElementById('filtre-valeurs-liste').style.display = 'none';

    if (!nom || !champ) { res.textContent = I18N.choose_layer_and_field; return; }
    if (!geoLayersData[nom]) { res.textContent = I18N.data_not_loaded; return; }

    var data = geoLayersData[nom];
    var info = metaCouches[nom];
    var filtrees = data.features.filter(function(f) {
        var fv = String(f.properties[champ] || '');
        var fvn = parseFloat(fv);
        var vn  = parseFloat(val);
        switch(op) {
            case 'eq':       return fv === val;
            case 'neq':      return fv !== val;
            case 'contains': return fv.toLowerCase().indexOf(val.toLowerCase()) !== -1;
            case 'starts':   return fv.toLowerCase().indexOf(val.toLowerCase()) === 0;
            case 'gt':       return !isNaN(fvn) && !isNaN(vn) && fvn > vn;
            case 'lt':       return !isNaN(fvn) && !isNaN(vn) && fvn < vn;
            case 'gte':      return !isNaN(fvn) && !isNaN(vn) && fvn >= vn;
            case 'lte':      return !isNaN(fvn) && !isNaN(vn) && fvn <= vn;
            default:         return true;
        }
    });

    if (couches_leaflet[nom]) map.removeLayer(couches_leaflet[nom]);

    if (filtrees.length === 0) {
        res.textContent = I18N.no_entity_found;
        var clusterCheckboxVide = document.getElementById('cluster_' + nom.replace(/[^a-zA-Z0-9]/g, '_'));
        var activerClusterVide = clusterCheckboxVide ? clusterCheckboxVide.checked : false;
        var construitsVide = construireLayer(nom, info, data, activerClusterVide);
        couches_leaflet[nom] = construitsVide.actif;
        construitsVide.actif.addTo(map);
        return;
    }

    var filteredGeoJSON = { type: 'FeatureCollection', features: filtrees };
    var construits = construireLayer(nom, info, filteredGeoJSON, false);
    couches_leaflet[nom] = construits.actif;
    construits.actif.addTo(map);

    surlignerEntitesFiltrees(construits.actif, filtrees.length);

    res.textContent = filtrees.length + ' ' + I18N.entities_found_prefix + ' ' + data.features.length
        + ' ' + I18N.entities_highlighted_suffix;
    try { map.invalidateSize(false); map.fitBounds(couches_leaflet[nom].getBounds(), { padding: [40,40], maxZoom: 19 }); } catch(e) {}
}

function surlignerEntitesFiltrees(layerGroup, nbEntites) {
    var premiereCouche = null;

    layerGroup.eachLayer(function(couche) {
        if (!premiereCouche) premiereCouche = couche;

        if (couche instanceof L.Marker) {
            var el = couche.getElement ? couche.getElement() : null;
            if (el) {
                L.DomUtil.addClass(el, 'entite-filtree-pulse');
            } else {
                couche.once('add', function() {
                    var e2 = couche.getElement ? couche.getElement() : null;
                    if (e2) L.DomUtil.addClass(e2, 'entite-filtree-pulse');
                });
            }
        } else if (couche.setStyle) {
            var elPath = couche.getElement ? couche.getElement() : null;
            if (elPath) {
                L.DomUtil.addClass(elPath, 'entite-filtree-pulse');
            }
            try {
                couche.setStyle({ color: '#f9ca24', weight: (couche.options.weight || 2) + 2 });
            } catch(e) {}
        }
    });

    if (premiereCouche) {
        if (nbEntites === 1) {
            premiereCouche.fire('click');
        }
        if (premiereCouche.openPopup) {
            setTimeout(function() { premiereCouche.openPopup(); }, 300);
        }
    }
}

function reinitialiserFiltre() {
    var nom = document.getElementById('filtre-couche').value;
    document.getElementById('filtre-valeur').value = '';
    document.getElementById('filtre-resultat').textContent = '';
    document.getElementById('filtre-valeurs-liste').style.display = 'none';
    if (!nom || !geoLayersData[nom]) return;

    if (couches_leaflet[nom]) map.removeLayer(couches_leaflet[nom]);
    var info = metaCouches[nom];
    var clusterCheckbox = document.getElementById('cluster_' + nom.replace(/[^a-zA-Z0-9]/g, '_'));
    var activerCluster = clusterCheckbox ? clusterCheckbox.checked : false;
    var construits = construireLayer(nom, info, geoLayersData[nom], activerCluster);
    couches_geolayers[nom] = construits.brut;
    couches_leaflet[nom]   = construits.actif;
    construits.actif.addTo(map);
}

// ═══════════════════════════════════════════════════════
// SIDEBAR REPLIABLE & RESPONSIVE (mobile / web)
// ═══════════════════════════════════════════════════════
function estMobile() {
    return window.matchMedia('(max-width: 768px)').matches;
}

function sidebarEstVisible(sb) {
    return estMobile() ? sb.classList.contains('sidebar-open') : !sb.classList.contains('sidebar-hidden');
}

function ouvrirSidebar() {
    var sb = document.getElementById('sidebar');
    if (!sb) return;
    if (estMobile()) {
        sb.classList.add('sidebar-open');
        document.getElementById('sidebar-overlay').classList.add('visible');
    } else {
        sb.classList.remove('sidebar-hidden');
    }
    setTimeout(function() { map.invalidateSize(false); }, 280);
}

function fermerSidebar() {
    var sb = document.getElementById('sidebar');
    if (!sb) return;
    if (estMobile()) {
        sb.classList.remove('sidebar-open');
        document.getElementById('sidebar-overlay').classList.remove('visible');
    } else {
        sb.classList.add('sidebar-hidden');
    }
    setTimeout(function() { map.invalidateSize(false); }, 280);
}

function basculerSidebar() {
    var sb = document.getElementById('sidebar');
    if (!sb) return;
    if (sidebarEstVisible(sb)) fermerSidebar(); else ouvrirSidebar();
}

var btnSidebarToggle = document.getElementById('btn-sidebar-toggle');
if (btnSidebarToggle) btnSidebarToggle.addEventListener('click', basculerSidebar);

var sidebarOverlay = document.getElementById('sidebar-overlay');
if (sidebarOverlay) sidebarOverlay.addEventListener('click', fermerSidebar);

if (estMobile()) {
    var sbInit = document.getElementById('sidebar');
    if (sbInit) sbInit.classList.remove('sidebar-open');
}

var redimensionnementTimer = null;
window.addEventListener('resize', function() {
    clearTimeout(redimensionnementTimer);
    redimensionnementTimer = setTimeout(function() { map.invalidateSize(false); }, 150);
});
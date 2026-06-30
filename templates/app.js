        var metaCouches = JSON.parse('__META_COUCHES_JSON__');
        var map = L.map('map', { zoomControl: true }).setView([0, 0], 2);

        var baseLayers = {
            "BASE": L.tileLayer("__URL_FOND__", { maxZoom: 20, crossOrigin: true }),
            "OSM":  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", { maxZoom: 19, crossOrigin: true }),
            "SAT":  L.tileLayer("https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}", { maxZoom: 20 })
        };
        baseLayers["BASE"].addTo(map);

        function changerFond() {
            var sel = document.getElementById('fondSelector').value;
            for (var k in baseLayers) { map.removeLayer(baseLayers[k]); }
            baseLayers[sel].addTo(map);
        }

        __OUTILS_JS__

        // ── Utilitaires couleur ──────────────────────────────────────
        function hexToRgba(hex, alpha) {
            if (!hex || hex.length < 7) return 'rgba(51,136,255,0.2)';
            var r = parseInt(hex.slice(1,3),16);
            var g = parseInt(hex.slice(3,5),16);
            var b = parseInt(hex.slice(5,7),16);
            var a = (alpha != null) ? alpha : 0.0;
            return 'rgba(' + r + ',' + g + ',' + b + ',' + a + ')';
        }

        // Détermine si une couleur hex est plutôt claire (pour choisir le texte du badge cluster)
        function texteContrastant(hex) {
            if (!hex || hex.length < 7) return '#fff';
            var r = parseInt(hex.slice(1,3),16), g = parseInt(hex.slice(3,5),16), b = parseInt(hex.slice(5,7),16);
            var luminance = (0.299*r + 0.587*g + 0.114*b) / 255;
            return luminance > 0.6 ? '#1a1a2e' : '#ffffff';
        }

        // ── Fabrique d'icône de cluster colorée selon la couleur dominante du groupe ──
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
        var couches_geolayers = {};   // layer GeoJSON brut (sans cluster), pour reset filtre
        var couches_cluster_color = {}; // couleur dominante utilisée pour chaque cluster de couche
        var geoLayersData     = {};
        var promesses_chargement = [];
        var legendContainer = document.getElementById('legende-liste');

        // Construit un layer Leaflet (cluster ou direct) à partir d'un GeoJSON déjà chargé
        function construireLayer(nom, info, data, activerCluster) {
            var isPoint = !!info.is_point;
            var clusterGroup = null;

            // Couleur dominante de la couche pour le cluster : 1ère entrée de légende sinon 1ère feature
            var couleurCluster = '#4ecdc4';
            if (info.legend_style && info.legend_style.length > 0) {
                // on tentera de la déduire dynamiquement depuis le style réel plus bas
                couleurCluster = couleurCluster;
            }
            if (data.features && data.features.length > 0) {
                var stf = data.features[0].properties._qgis_style || {};
                if (stf.fillColor) couleurCluster = stf.fillColor;
                else if (stf.color) couleurCluster = stf.color;
            }
            couches_cluster_color[nom] = couleurCluster;

            if (isPoint && activerCluster) {
                // Si la couche est catégorisée (plusieurs couleurs), chaque cluster regroupe des
                // points pouvant être de catégories différentes. On utilise un cluster "neutre"
                // par défaut, mais si toutes les features visibles dans un cluster partagent la
                // même classe, Leaflet.markercluster recalcule via iconCreateFunction qui peut
                // inspecter cluster.getAllChildMarkers() pour la couleur dominante du groupe.
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
                        // Couleur dominante du sous-groupe (catégorie majoritaire dans ce cluster)
                        var meilleureCouleur = couleurCluster, maxN = 0;
                        Object.keys(compteur).forEach(function(c) {
                            if (compteur[c] > maxN) { maxN = compteur[c]; meilleureCouleur = c; }
                        });
                        return fabriqueIconeCluster(meilleureCouleur)(cluster);
                    }
                });
            }

            var geoLayer = L.geoJSON(data, {
                pointToLayer: function(feature, latlng) {
                    var st  = feature.properties._qgis_style || {};
                    var val = feature.properties._qgis_class_val;

                    var matchImg = '';
                    if (info.legend_style) {
                        info.legend_style.forEach(function(node) {
                            if (node.label === val || node.valeur === val) matchImg = node.img_path;
                        });
                        if (!matchImg && info.legend_style.length > 0) matchImg = info.legend_style[0].img_path;
                    }

                    var marker;
                    if (matchImg) {
                        marker = L.marker(latlng, { icon: L.icon({
                            iconUrl: matchImg, iconSize: [20, 20],
                            iconAnchor: [10, 10], popupAnchor: [0, -12]
                        }) });
                    } else {
                        marker = L.circleMarker(latlng, {
                            radius:      st.radius      || 6,
                            color:       st.color       || '#3388ff',
                            fillColor:   st.fillColor   || '#3388ff',
                            weight:      st.weight      != null ? st.weight      : 1,
                            opacity:     st.opacity     != null ? st.opacity     : 1,
                            fillOpacity: st.fillOpacity != null ? st.fillOpacity : 0.85
                        });
                    }
                    // Couleur QGIS attachée au marker pour que le cluster puisse la lire (catégorisation)
                    marker.options.__qgisColor = st.fillColor || st.color || couleurCluster;

                    // Étiquette QGIS (point 6) : tooltip permanent si la couche a un labeling actif
                    if (info.etiquette && info.etiquette.champ && feature.properties[info.etiquette.champ] !== undefined) {
                        marker.bindTooltip(String(feature.properties[info.etiquette.champ]), {
                            permanent: true, direction: 'right', className: 'qgis-label',
                            offset: [10, 0]
                        });
                        marker.getTooltip().options.opacity = 1;
                    }
                    return marker;
                },

                style: function(feature) {
                    var s = (feature.properties && feature.properties._qgis_style) || {};
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

                    // Étiquette pour lignes/polygones : tooltip centré sur l'entité
                    if (info.etiquette && info.etiquette.champ && feature.properties[info.etiquette.champ] !== undefined
                        && !isPoint) {
                        layer.bindTooltip(String(feature.properties[info.etiquette.champ]), {
                            permanent: true, direction: 'center', className: 'qgis-label'
                        });
                    }
                }
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
                + '<button class="btn-collapse" id="toggle_' + safeId + '" title="Replier / déplier">▾</button>'
                + '</div>'
                + '<div class="group-couche-corps" id="corps_' + safeId + '"></div>';

            var corps = groupDiv.querySelector('#corps_' + safeId);

            if (info.is_polygon) {
                corps.innerHTML += '<div class="sous-legende-item">'
                    + '<span class="legend-poly-swatch" id="poly_leg_' + safeId + '"></span>'
                    + '<span>' + nom + '</span></div>';
            } else if (info.is_line) {
                // Légende lignes : une entrée par catégorie si dispo (point 5),
                // sinon une seule barre générique mise à jour avec la couleur réelle
                if (info.legend_style && info.legend_style.length > 0) {
                    info.legend_style.forEach(function(node, idx) {
                        corps.innerHTML += '<div class="sous-legende-item">'
                            + '<span class="legend-line-swatch" id="line_leg_' + safeId + '_' + idx + '" data-default="' + idx + '"></span>'
                            + '<span>' + node.label + '</span></div>';
                    });
                } else {
                    corps.innerHTML += '<div class="sous-legende-item">'
                        + '<span class="legend-line-swatch" id="line_leg_' + safeId + '_0"></span>'
                        + '<span>' + nom + '</span></div>';
                }
            } else {
                // Points : icônes PNG par catégorie
                (info.legend_style || []).forEach(function(node) {
                    corps.innerHTML += '<div class="sous-legende-item">'
                        + '<img class="img-legend-icon" src="' + node.img_path + '" />'
                        + '<span>' + node.label + '</span></div>';
                });
                // Case à cocher "Regrouper les points" — uniquement pour couches ponctuelles (point 3)
                corps.innerHTML += '<div class="cluster-toggle-row">'
                    + '<input type="checkbox" id="cluster_' + safeId + '" checked />'
                    + '<label for="cluster_' + safeId + '">Regrouper les points (cluster)</label></div>';
            }
            legendContainer.appendChild(groupDiv);

            // Bascule repli/dépli de ce groupe précisément
            var btnToggle = groupDiv.querySelector('#toggle_' + safeId);
            btnToggle.addEventListener('click', function() {
                corps.classList.toggle('is-collapsed');
                btnToggle.classList.toggle('is-collapsed');
            });

            var p = fetch(info.fichier)
                .then(function(r) { return r.json(); })
                .then(function(data) {
                    geoLayersData[nom] = data;

                    // Mise à jour légende polygone/ligne avec couleurs réelles
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
                                // Une couleur par catégorie : on cherche dans les features la 1ère
                                // entité de chaque catégorie pour en extraire le style réel
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
                    construits.actif.addTo(map);

                    // Bascule cluster ON/OFF en direct, sans recharger les données
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

        // Recalcule l'étendue et ajuste le zoom de la carte sur les données chargées.
        // Force systématiquement un invalidateSize() avant le fitBounds : tant que la mise
        // en page (flexbox, repli du loader, sidebar) n'est pas stabilisée, Leaflet peut
        // mesurer un conteneur dont la taille n'est pas encore définitive, ce qui produit
        // un zoom d'ajustement incorrect ne couvrant pas réellement 100% des données.
        function ajusterVueSurDonnees(bounds) {
            map.invalidateSize(false);
            if (bounds && bounds.isValid()) {
                map.fitBounds(bounds, { padding: [30, 30], maxZoom: 19, animate: false });
            } else {
                map.setView([12.3, -1.5], 7);
            }
        }

        Promise.all(promesses_chargement).then(function() {
            var bounds = null;
            Object.values(couches_leaflet).forEach(function(lg) {
                try {
                    var b = lg.getBounds();
                    if (b && b.isValid()) bounds = bounds ? bounds.extend(b) : b;
                } catch(e) {}
            });

            ajusterVueSurDonnees(bounds);
            // Second passage après le prochain repaint du navigateur : garantit un
            // ajustement exact même si la fenêtre (ou la barre d'adresse mobile) a
            // changé de taille juste après le premier calcul.
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
        // Déplie ou replie tous les groupes de la légende d'un coup
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
            selChamp.innerHTML = '<option value="">-- Choisir un champ --</option>';
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

            if (!nom || !champ) { res.textContent = '⚠ Choisissez une couche et un champ.'; return; }
            if (!geoLayersData[nom]) { res.textContent = '⚠ Données non encore chargées.'; return; }

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
                res.textContent = '⚠ Aucune entité trouvée.';
                // On réaffiche quand même la couche complète (vide visuellement de résultat)
                var clusterCheckboxVide = document.getElementById('cluster_' + nom.replace(/[^a-zA-Z0-9]/g, '_'));
                var activerClusterVide = clusterCheckboxVide ? clusterCheckboxVide.checked : false;
                var construitsVide = construireLayer(nom, info, data, activerClusterVide);
                couches_leaflet[nom] = construitsVide.actif;
                construitsVide.actif.addTo(map);
                return;
            }

            var filteredGeoJSON = { type: 'FeatureCollection', features: filtrees };

            // Le clustering masque visuellement les entités sélectionnées : on le désactive
            // temporairement pour le résultat du filtre, pour que chaque entité reste visible
            // et cliquable individuellement, avec sa surbrillance.
            var construits = construireLayer(nom, info, filteredGeoJSON, false);
            couches_leaflet[nom] = construits.actif;
            construits.actif.addTo(map);

            // Surlignage pulsé + sélection/clic automatique des entités trouvées
            surlignerEntitesFiltrees(construits.actif, filtrees.length);

            res.textContent = filtrees.length + ' entité(s) trouvée(s) sur ' + data.features.length
                + ' — sélectionnée(s) en surbrillance sur la carte.';
            try { map.invalidateSize(false); map.fitBounds(couches_leaflet[nom].getBounds(), { padding: [40,40], maxZoom: 19 }); } catch(e) {}
        }

        // Applique une surbrillance pulsée à toutes les entités d'un layer filtré,
        // et ouvre/clique automatiquement le popup de la première entité trouvée
        // (ou de l'unique entité si une seule correspond au filtre).
        function surlignerEntitesFiltrees(layerGroup, nbEntites) {
            var premiereCouche = null;

            layerGroup.eachLayer(function(couche) {
                if (!premiereCouche) premiereCouche = couche;

                if (couche instanceof L.Marker) {
                    // Marker avec icône image : on ajoute la classe CSS de pulsation sur l'icône DOM
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
                    // CircleMarker, Polyline, Polygon : on renforce le style visuellement
                    // (la classe CSS pulse s'applique aussi via le path SVG)
                    var elPath = couche.getElement ? couche.getElement() : null;
                    if (elPath) {
                        L.DomUtil.addClass(elPath, 'entite-filtree-pulse');
                    }
                    try {
                        couche.setStyle({ color: '#f9ca24', weight: (couche.options.weight || 2) + 2 });
                    } catch(e) {}
                }
            });

            // Sélection/clic automatique : ouvre le popup de la première entité.
            // Si une seule entité correspond, on simule un clic réel dessus (fire 'click').
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

        // Sur mobile, la sidebar démarre fermée pour laisser toute la place à la carte.
        if (estMobile()) {
            var sbInit = document.getElementById('sidebar');
            if (sbInit) sbInit.classList.remove('sidebar-open');
        }

        // Recalcule la taille de la carte à chaque redimensionnement (rotation mobile,
        // redimensionnement de fenêtre desktop, etc.) pour garder un rendu correct.
        var redimensionnementTimer = null;
        window.addEventListener('resize', function() {
            clearTimeout(redimensionnementTimer);
            redimensionnementTimer = setTimeout(function() { map.invalidateSize(false); }, 150);
        });

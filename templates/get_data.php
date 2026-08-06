<?php
/**
 * get_data.php — généré par Universal Map2web
 * Endpoint unique servant les données PostgreSQL/PostGIS en GeoJSON,
 * pour toutes les couches déclarées dans db_config.php ($LAYERS_CONFIG).
 *
 * Appel attendu : get_data.php?layer=<nom_couche>&key=<API_KEY>
 */

header('Content-Type: application/json; charset=utf-8');

require_once __DIR__ . '/db_config.php';

// --- Vérification de la clé API ---
$provided_key = $_GET['key'] ?? '';
if (!hash_equals(API_KEY, $provided_key)) {
    http_response_code(403);
    echo json_encode(["error" => "Acces non autorise."]);
    exit;
}

// --- Sélection de la couche demandée ---
$layer = $_GET['layer'] ?? '';
if (!isset($LAYERS_CONFIG[$layer])) {
    http_response_code(404);
    echo json_encode(["error" => "Couche inconnue."]);
    exit;
}
$cfg = $LAYERS_CONFIG[$layer];

// --- Filtrage spatial optionnel (bbox envoyée par le client : minx,miny,maxx,maxy) ---
$bbox = $_GET['bbox'] ?? null;
$bbox_filter = '';
$params = [];

if ($bbox && preg_match('/^-?\d+\.?\d*,-?\d+\.?\d*,-?\d+\.?\d*,-?\d+\.?\d*$/', $bbox)) {
    [$minx, $miny, $maxx, $maxy] = explode(',', $bbox);
    $bbox_filter = "WHERE ST_Intersects(
        \"{$cfg['geom_col']}\",
        ST_Transform(ST_MakeEnvelope(:minx, :miny, :maxx, :maxy, 4326), ST_SRID(\"{$cfg['geom_col']}\"))
    )";
    $params = [':minx' => $minx, ':miny' => $miny, ':maxx' => $maxx, ':maxy' => $maxy];
}

try {
    $pdo = new PDO(
        "pgsql:host=" . $cfg['host'] . ";port=" . $cfg['port'] . ";dbname=" . $cfg['dbname'],
        $cfg['user'],
        $cfg['pass']
    );
    $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);

    // Schéma/table/colonne = valeurs fixées à l'export (pas de saisie utilisateur au runtime)
    $schema = $cfg['schema'];
    $table = $cfg['table'];
    $geom_col = $cfg['geom_col'];

    $sql = "
        SELECT jsonb_build_object(
            'type', 'FeatureCollection',
            'features', COALESCE(jsonb_agg(f.feature), '[]'::jsonb)
        )
        FROM (
            SELECT jsonb_build_object(
                'type', 'Feature',
                'geometry', ST_AsGeoJSON(ST_Transform(\"$geom_col\", 4326))::jsonb,
                'properties', to_jsonb(t) - '$geom_col'
            ) AS feature
            FROM \"$schema\".\"$table\" t
            $bbox_filter
        ) f;
    ";

    $stmt = $pdo->prepare($sql);
    $stmt->execute($params);
    $result = $stmt->fetchColumn();

    echo $result ?: '{"type":"FeatureCollection","features":[]}';

} catch (PDOException $e) {
    http_response_code(500);
    if (isset($_GET['debug']) && $_GET['debug'] === '1') {
        // Ne s'affiche que si la clé API valide a déjà été fournie (vérifiée plus haut) :
        // safe à garder en place, pas de fuite pour un visiteur non autorisé.
        echo json_encode(["error" => "Erreur PDO : " . $e->getMessage()]);
    } else {
        echo json_encode(["error" => "Erreur de connexion a la base de donnees."]);
    }
}

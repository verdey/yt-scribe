<?php

set_time_limit(300);

require_once __DIR__ . '/../includes/cli.php';

header('Content-Type: application/json');
header('Cache-Control: no-store');

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    echo json_encode(['error' => 'POST only']);
    exit;
}

$body = json_decode(file_get_contents('php://input'), true);
if (!$body) {
    http_response_code(400);
    echo json_encode(['error' => 'Invalid JSON body']);
    exit;
}

$videoIds = $body['video_ids'] ?? [];
$bundle   = trim($body['bundle'] ?? '');

if (empty($videoIds) || !is_array($videoIds)) {
    http_response_code(400);
    echo json_encode(['error' => 'video_ids must be a non-empty array']);
    exit;
}

if ($bundle === '') {
    http_response_code(400);
    echo json_encode(['error' => 'bundle is required']);
    exit;
}

// Sanitize bundle name: lowercase, alphanumeric + underscore + hyphen only
$bundle = strtolower(preg_replace('/[^a-zA-Z0-9_-]/', '_', $bundle));

$result = yt_scribe('batch', $videoIds, [
    '--bundle' => $bundle,
    '-o' => '/Users/verdey/code/verdey-projects/yt-scribe/transcripts',
    '--json' => true,
]);

if ($result['exitCode'] !== 0) {
    http_response_code(500);
    echo json_encode(['error' => trim($result['stderr']), 'code' => $result['exitCode']]);
    exit;
}

echo $result['stdout'];

<?php

require_once __DIR__ . '/../includes/cli.php';

header('Content-Type: application/json');
header('Cache-Control: no-store');

$url = trim($_GET['url'] ?? '');
if ($url === '') {
    http_response_code(400);
    echo json_encode(['error' => 'Missing required parameter: url']);
    exit;
}

$result = yt_scribe('playlist', [$url], ['--json' => true]);

if ($result['exitCode'] !== 0) {
    http_response_code(500);
    echo json_encode(['error' => trim($result['stderr']), 'code' => $result['exitCode']]);
    exit;
}

echo $result['stdout'];

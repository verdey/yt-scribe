<?php

require_once __DIR__ . '/../includes/cli.php';

header('Content-Type: application/json');
header('Cache-Control: no-store');

$q = trim($_GET['q'] ?? '');
if ($q === '') {
    http_response_code(400);
    echo json_encode(['error' => 'Missing required parameter: q']);
    exit;
}

$n = (int) ($_GET['n'] ?? 10);
$n = max(1, min(25, $n));

$result = yt_scribe('search', [$q], ['--json' => true, '-n' => $n]);

if ($result['exitCode'] !== 0) {
    http_response_code(500);
    echo json_encode(['error' => trim($result['stderr']), 'code' => $result['exitCode']]);
    exit;
}

echo $result['stdout'];

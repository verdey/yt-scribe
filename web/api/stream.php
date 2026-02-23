<?php

set_time_limit(300);

// Disable output buffering
while (ob_get_level()) {
    ob_end_flush();
}
ob_implicit_flush(true);

// SSE headers
header('Content-Type: text/event-stream');
header('Cache-Control: no-cache');
header('Connection: keep-alive');
header('X-Accel-Buffering: no');

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    echo "data: " . json_encode(['event' => 'error', 'message' => 'POST only']) . "\n\n";
    flush();
    exit;
}

$body = json_decode(file_get_contents('php://input'), true);
if (!$body) {
    http_response_code(400);
    echo "data: " . json_encode(['event' => 'error', 'message' => 'Invalid JSON body']) . "\n\n";
    flush();
    exit;
}

$videoIds = $body['video_ids'] ?? [];
$bundle   = trim($body['bundle'] ?? '');

if (empty($videoIds) || !is_array($videoIds)) {
    http_response_code(400);
    echo "data: " . json_encode(['event' => 'error', 'message' => 'video_ids must be a non-empty array']) . "\n\n";
    flush();
    exit;
}

if ($bundle === '') {
    http_response_code(400);
    echo "data: " . json_encode(['event' => 'error', 'message' => 'bundle is required']) . "\n\n";
    flush();
    exit;
}

// Sanitize bundle name
$bundle = strtolower(preg_replace('/[^a-zA-Z0-9_-]/', '_', $bundle));

// Build command
$bin = '/Users/verdey/code/verdey-projects/yt-scribe/.venv/bin/yt-scribe';
$transcriptsDir = '/Users/verdey/code/verdey-projects/yt-scribe/transcripts';

$cmd = escapeshellarg($bin) . ' batch'
    . ' --bundle ' . escapeshellarg($bundle)
    . ' -o ' . escapeshellarg($transcriptsDir)
    . ' --jsonl';

foreach ($videoIds as $id) {
    $cmd .= ' ' . escapeshellarg((string) $id);
}

$descriptors = [
    0 => ['pipe', 'r'],
    1 => ['pipe', 'w'],
    2 => ['pipe', 'w'],
];

$process = proc_open($cmd, $descriptors, $pipes);

if (!is_resource($process)) {
    echo "data: " . json_encode(['event' => 'error', 'message' => 'Failed to start yt-scribe process']) . "\n\n";
    flush();
    exit;
}

fclose($pipes[0]);

// Stream stdout line by line
while (($line = fgets($pipes[1])) !== false) {
    $line = trim($line);
    if ($line === '') {
        continue;
    }
    echo "data: " . $line . "\n\n";
    flush();
}

fclose($pipes[1]);

// Read stderr
$stderr = stream_get_contents($pipes[2]);
fclose($pipes[2]);

$exitCode = proc_close($process);

if ($exitCode !== 0 && $stderr) {
    echo "data: " . json_encode(['event' => 'error', 'message' => trim($stderr)]) . "\n\n";
    flush();
}

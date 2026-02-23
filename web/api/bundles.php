<?php

header('Content-Type: application/json');
header('Cache-Control: no-store');

$transcriptsDir = '/Users/verdey/code/verdey-projects/yt-scribe/transcripts';

/**
 * Parse flat YAML frontmatter from a markdown file.
 * Returns associative array of key-value pairs between --- markers.
 */
function parse_frontmatter(string $content): array
{
    $meta = [];
    if (strpos($content, '---') !== 0) {
        return $meta;
    }
    $end = strpos($content, '---', 3);
    if ($end === false) {
        return $meta;
    }
    $block = trim(substr($content, 3, $end - 3));
    foreach (explode("\n", $block) as $line) {
        $parts = explode(': ', $line, 2);
        if (count($parts) === 2) {
            $meta[trim($parts[0])] = trim(trim($parts[1]), '"\'');
        }
    }
    return $meta;
}

$name = $_GET['name'] ?? null;

if ($name !== null) {
    // Get specific bundle contents
    $name = basename($name); // prevent path traversal
    $bundleDir = $transcriptsDir . '/' . $name;

    if (!is_dir($bundleDir)) {
        http_response_code(404);
        echo json_encode(['error' => 'Bundle not found']);
        exit;
    }

    $indexPath = $bundleDir . '/_index.md';
    $indexContent = file_exists($indexPath) ? file_get_contents($indexPath) : '';

    $files = [];
    foreach (glob($bundleDir . '/*.md') as $filepath) {
        $filename = basename($filepath);
        if ($filename === '_index.md') continue;

        $content = file_get_contents($filepath);
        $meta = parse_frontmatter($content);

        $files[] = [
            'filename' => $filename,
            'title'    => $meta['title'] ?? pathinfo($filename, PATHINFO_FILENAME),
            'video_id' => $meta['video_id'] ?? null,
        ];
    }

    echo json_encode([
        'name'          => $name,
        'index_content' => $indexContent,
        'files'         => $files,
    ]);
    exit;
}

// List all bundles
$bundles = [];

if (!is_dir($transcriptsDir)) {
    echo json_encode($bundles);
    exit;
}

foreach (scandir($transcriptsDir) as $entry) {
    if ($entry === '.' || $entry === '..') continue;
    $dir = $transcriptsDir . '/' . $entry;
    if (!is_dir($dir)) continue;

    $indexPath = $dir . '/_index.md';
    $count = count(glob($dir . '/*.md')) - (file_exists($indexPath) ? 1 : 0);

    $meta = [];
    if (file_exists($indexPath)) {
        $meta = parse_frontmatter(file_get_contents($indexPath));
    }

    $bundles[] = [
        'name'       => $entry,
        'path'       => $dir,
        'count'      => max(0, $count),
        'created_at' => $meta['created'] ?? $meta['created_at'] ?? date('Y-m-d', filemtime($dir)),
    ];
}

echo json_encode($bundles);

<?php

/**
 * Run a yt-scribe CLI command and return its output.
 *
 * @param string $subcommand  The subcommand (e.g., "search", "playlist", "batch")
 * @param array  $args        Arguments array (gets shell-escaped and joined)
 * @param array  $flags       Associative array of flags (e.g., ["--json" => true, "-n" => "10"])
 * @return array{exitCode: int, stdout: string, stderr: string}
 */
function yt_scribe(string $subcommand, array $args = [], array $flags = []): array
{
    $bin = '/Users/verdey/code/verdey-projects/yt-scribe/.venv/bin/yt-scribe';

    $cmd = escapeshellarg($bin) . ' ' . escapeshellarg($subcommand);

    foreach ($flags as $flag => $value) {
        if ($value === true) {
            $cmd .= ' ' . $flag;
        } elseif ($value !== false && $value !== null) {
            $cmd .= ' ' . $flag . ' ' . escapeshellarg((string) $value);
        }
    }

    foreach ($args as $arg) {
        $cmd .= ' ' . escapeshellarg((string) $arg);
    }

    $descriptors = [
        0 => ['pipe', 'r'],
        1 => ['pipe', 'w'],
        2 => ['pipe', 'w'],
    ];

    $process = proc_open($cmd, $descriptors, $pipes);

    if (!is_resource($process)) {
        return [
            'exitCode' => 1,
            'stdout'   => '',
            'stderr'   => 'Failed to start yt-scribe process',
        ];
    }

    fclose($pipes[0]);
    $stdout = stream_get_contents($pipes[1]);
    fclose($pipes[1]);
    $stderr = stream_get_contents($pipes[2]);
    fclose($pipes[2]);
    $exitCode = proc_close($process);

    return [
        'exitCode' => $exitCode,
        'stdout'   => $stdout,
        'stderr'   => $stderr,
    ];
}

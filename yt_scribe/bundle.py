"""Bundle management: directories and index generation."""
from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path


def slugify(text: str) -> str:
    """Convert text to a filesystem-safe slug for bundle directory names.

    "Sales Automation Tools" -> "sales_automation_tools"
    Lowercase, replace non-alphanumeric with underscore, collapse multiples,
    truncate to 60 chars.
    """
    slug = text.lower()
    slug = re.sub(r"[^a-z0-9]+", "_", slug)
    slug = slug.strip("_")
    return slug[:60]


def _parse_frontmatter(text: str) -> dict[str, str]:
    """Parse flat YAML frontmatter from a markdown file's text content.

    Returns dict of key: value pairs with surrounding quotes stripped.
    """
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    fm = {}
    for line in parts[1].strip().splitlines():
        if ": " not in line:
            continue
        key, val = line.split(": ", 1)
        val = val.strip().strip('"').strip("'")
        fm[key.strip()] = val
    return fm


def read_bundle_entries(bundle_dir: Path) -> list[tuple[str, str, Path]]:
    """Read existing transcript entries from a bundle directory.

    Scans all .md files (except _index.md), parses YAML frontmatter
    for title and video_id.

    Returns list of (title, video_id, filepath) tuples, sorted by filename.
    """
    entries = []
    for md_file in sorted(bundle_dir.glob("*.md")):
        if md_file.name == "_index.md":
            continue
        text = md_file.read_text(encoding="utf-8")
        fm = _parse_frontmatter(text)
        title = fm.get("title", md_file.stem)
        video_id = fm.get("video_id", "")
        entries.append((title, video_id, md_file))
    return entries


def _read_index_metadata(bundle_dir: Path) -> dict | None:
    """Read metadata from existing _index.md frontmatter.

    Returns dict with keys: bundle, query, source_url, created_at.
    Returns None if _index.md doesn't exist.
    """
    index_path = bundle_dir / "_index.md"
    if not index_path.is_file():
        return None
    text = index_path.read_text(encoding="utf-8")
    fm = _parse_frontmatter(text)
    return {
        "bundle": fm.get("bundle", ""),
        "query": fm.get("query", ""),
        "source_url": fm.get("source_url"),
        "created_at": fm.get("created_at"),
    }


def create_bundle_dir(bundle_name: str, output_base: Path | None = None) -> Path:
    """Create and return a bundle directory path.

    Default: ./transcripts/{bundle_name}/
    With output_base: {output_base}/{bundle_name}/
    """
    base = output_base or Path("transcripts")
    bundle_dir = base / bundle_name
    bundle_dir.mkdir(parents=True, exist_ok=True)
    return bundle_dir


def generate_index(
    bundle_dir: Path,
    bundle_name: str,
    query: str,
    saved_files: list[tuple[str, str, Path]],
    source_url: str | None = None,
) -> Path:
    """Generate _index.md for a bundle.

    Args:
        bundle_dir: Path to the bundle directory.
        bundle_name: Human-readable bundle name (used as heading).
        query: Original search query (or playlist title).
        saved_files: List of (title, video_id, filepath) tuples.
        source_url: Optional playlist URL to link back to in the index.

    Returns the path to the created _index.md file.
    """
    # 1. Check if _index.md already exists — preserve original metadata
    existing_meta = _read_index_metadata(bundle_dir)

    if existing_meta:
        bundle_name = existing_meta.get("bundle") or bundle_name
        query = existing_meta.get("query") or query
        source_url = existing_meta.get("source_url") or source_url
        original_created_at = existing_meta.get("created_at")
    else:
        original_created_at = None

    # 2. Scan the directory for ALL .md files (not just saved_files)
    all_entries = read_bundle_entries(bundle_dir)

    # 3. Fall back to saved_files if scan found nothing
    if not all_entries:
        all_entries = saved_files

    count = len(all_entries)
    now = original_created_at or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    lines = [
        "---",
        f'bundle: "{bundle_name}"',
        f'query: "{query}"',
        f"count: {count}",
        f'created_at: "{now}"',
    ]

    if source_url:
        lines.append(f'source_url: "{source_url}"')

    lines.extend([
        "---",
        "",
        f"# {bundle_name}",
        "",
    ])

    if source_url:
        lines.append(f"> Source: [{query}]({source_url})")
    else:
        lines.append(f'> Search query: "{query}"')

    lines.append(f"> {count} transcripts")
    lines.extend([
        "",
        "## Contents",
        "",
        "| # | Title | Video |",
        "|---|-------|-------|",
    ])

    for i, (title, video_id, filepath) in enumerate(all_entries, 1):
        fname = filepath.name
        yt_url = f"https://youtube.com/watch?v={video_id}"
        lines.append(f"| {i} | [{title}](./{fname}) | [YouTube]({yt_url}) |")

    lines.append("")

    index_path = bundle_dir / "_index.md"
    index_path.write_text("\n".join(lines), encoding="utf-8")
    return index_path

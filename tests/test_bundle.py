"""Tests for yt_scribe.bundle — filesystem tests using tmp_path."""
from pathlib import Path

from yt_scribe.bundle import slugify, create_bundle_dir, generate_index, read_bundle_entries


class TestSlugify:
    """Test slugify() text normalization."""

    def test_basic(self):
        assert slugify("Hello World") == "hello_world"

    def test_special_chars(self):
        assert slugify("Test: Video! #1") == "test_video_1"

    def test_preserves_numbers(self):
        assert slugify("abc123") == "abc123"

    def test_collapses_multiple_underscores(self):
        assert slugify("a---b___c") == "a_b_c"

    def test_strips_leading_trailing_underscores(self):
        assert slugify("  Hello  ") == "hello"

    def test_truncates_to_60(self):
        long_text = "a" * 100
        assert len(slugify(long_text)) == 60

    def test_empty_string(self):
        assert slugify("") == ""

    def test_all_special_chars(self):
        assert slugify("!@#$%^&*()") == ""


class TestCreateBundleDir:
    """Test create_bundle_dir() with tmp directories."""

    def test_creates_directory(self, tmp_path):
        bundle_dir = create_bundle_dir("test_bundle", output_base=tmp_path)
        assert bundle_dir.exists()
        assert bundle_dir.is_dir()
        assert bundle_dir == tmp_path / "test_bundle"

    def test_creates_nested_parents(self, tmp_path):
        base = tmp_path / "deep" / "nested"
        bundle_dir = create_bundle_dir("mybundle", output_base=base)
        assert bundle_dir.exists()
        assert bundle_dir == base / "mybundle"

    def test_idempotent(self, tmp_path):
        create_bundle_dir("test_bundle", output_base=tmp_path)
        bundle_dir = create_bundle_dir("test_bundle", output_base=tmp_path)
        assert bundle_dir.exists()

    def test_default_base_is_transcripts(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        bundle_dir = create_bundle_dir("test_bundle")
        assert bundle_dir == Path("transcripts") / "test_bundle"
        assert bundle_dir.exists()


class TestGenerateIndex:
    """Test generate_index() output."""

    def test_creates_index_file(self, tmp_path):
        bundle_dir = tmp_path / "test_bundle"
        bundle_dir.mkdir()

        saved_files = [
            ("Video One", "vid11111111", bundle_dir / "video_one_vid11111111.md"),
            ("Video Two", "vid22222222", bundle_dir / "video_two_vid22222222.md"),
        ]
        # Create the files so read_bundle_entries can scan them
        for title, vid_id, path in saved_files:
            path.write_text(
                f'---\ntitle: "{title}"\nvideo_id: "{vid_id}"\n---\n# {title}\n',
                encoding="utf-8",
            )

        index_path = generate_index(bundle_dir, "test_bundle", "test query", saved_files)

        assert index_path.exists()
        assert index_path.name == "_index.md"

    def test_index_contains_frontmatter(self, tmp_path):
        bundle_dir = tmp_path / "test_bundle"
        bundle_dir.mkdir()

        saved_files = [("Video", "vid12345678", bundle_dir / "video.md")]
        saved_files[0][2].write_text(
            '---\ntitle: "Video"\nvideo_id: "vid12345678"\n---\n',
            encoding="utf-8",
        )

        index_path = generate_index(bundle_dir, "my_bundle", "search terms", saved_files)
        content = index_path.read_text(encoding="utf-8")

        assert content.startswith("---\n")
        assert 'bundle: "my_bundle"' in content
        assert 'query: "search terms"' in content
        assert "count: 1" in content

    def test_index_contains_table(self, tmp_path):
        bundle_dir = tmp_path / "test_bundle"
        bundle_dir.mkdir()

        saved_files = [
            ("First Video", "vid11111111", bundle_dir / "first_vid11111111.md"),
        ]
        saved_files[0][2].write_text(
            '---\ntitle: "First Video"\nvideo_id: "vid11111111"\n---\n',
            encoding="utf-8",
        )

        index_path = generate_index(bundle_dir, "bundle", "query", saved_files)
        content = index_path.read_text(encoding="utf-8")

        assert "## Contents" in content
        assert "| # | Title | Video |" in content
        assert "First Video" in content
        assert "vid11111111" in content

    def test_index_with_source_url(self, tmp_path):
        bundle_dir = tmp_path / "test_bundle"
        bundle_dir.mkdir()

        saved_files = [("Video", "vid12345678", bundle_dir / "video.md")]
        saved_files[0][2].write_text(
            '---\ntitle: "Video"\nvideo_id: "vid12345678"\n---\n',
            encoding="utf-8",
        )

        index_path = generate_index(
            bundle_dir, "bundle", "playlist title", saved_files,
            source_url="https://youtube.com/playlist?list=PL123",
        )
        content = index_path.read_text(encoding="utf-8")
        assert 'source_url: "https://youtube.com/playlist?list=PL123"' in content


class TestReadBundleEntries:
    """Test read_bundle_entries() file scanning."""

    def test_reads_markdown_files(self, tmp_path):
        (tmp_path / "video1.md").write_text(
            '---\ntitle: "Video One"\nvideo_id: "id111111111"\n---\n',
            encoding="utf-8",
        )
        (tmp_path / "video2.md").write_text(
            '---\ntitle: "Video Two"\nvideo_id: "id222222222"\n---\n',
            encoding="utf-8",
        )

        entries = read_bundle_entries(tmp_path)
        assert len(entries) == 2
        titles = [e[0] for e in entries]
        assert "Video One" in titles
        assert "Video Two" in titles

    def test_skips_index_file(self, tmp_path):
        (tmp_path / "_index.md").write_text("---\nbundle: test\n---\n", encoding="utf-8")
        (tmp_path / "video.md").write_text(
            '---\ntitle: "Video"\nvideo_id: "id123456789"\n---\n',
            encoding="utf-8",
        )

        entries = read_bundle_entries(tmp_path)
        assert len(entries) == 1

    def test_empty_dir(self, tmp_path):
        entries = read_bundle_entries(tmp_path)
        assert entries == []

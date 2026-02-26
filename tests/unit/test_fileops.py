"""Tests for FileTracker: pre-existence tracking, backup creation."""

from cc_rig.generators.fileops import FileTracker


class TestFileTracker:
    def test_write_new_file(self, tmp_path):
        tracker = FileTracker(tmp_path)
        tracker.write_text("hello.txt", "world")
        assert (tmp_path / "hello.txt").read_text() == "world"
        meta = tracker.metadata()
        assert meta["hello.txt"]["pre_existed"] is False
        assert meta["hello.txt"]["backed_up"] is False

    def test_write_creates_parents(self, tmp_path):
        tracker = FileTracker(tmp_path)
        tracker.write_text("a/b/c.txt", "deep")
        assert (tmp_path / "a" / "b" / "c.txt").read_text() == "deep"

    def test_overwrite_existing_backs_up(self, tmp_path):
        original = tmp_path / "existing.txt"
        original.write_text("original content")

        tracker = FileTracker(tmp_path)
        tracker.write_text("existing.txt", "new content")

        # New content written
        assert (tmp_path / "existing.txt").read_text() == "new content"

        # Backup created (with .bak extension to avoid Claude Code discovery)
        backup = tmp_path / ".cc-rig-backup" / "existing.txt.bak"
        assert backup.exists()
        assert backup.read_text() == "original content"

        # Metadata correct
        meta = tracker.metadata()
        assert meta["existing.txt"]["pre_existed"] is True
        assert meta["existing.txt"]["backed_up"] is True

    def test_overwrite_nested_backs_up(self, tmp_path):
        nested = tmp_path / "sub" / "file.md"
        nested.parent.mkdir(parents=True)
        nested.write_text("original nested")

        tracker = FileTracker(tmp_path)
        tracker.write_text("sub/file.md", "replaced")

        backup = tmp_path / ".cc-rig-backup" / "sub" / "file.md.bak"
        assert backup.read_text() == "original nested"

    def test_chmod(self, tmp_path):
        tracker = FileTracker(tmp_path)
        tracker.write_text("script.sh", "#!/bin/bash\necho hi")
        tracker.chmod("script.sh", 0o755)
        import os

        mode = os.stat(tmp_path / "script.sh").st_mode
        assert mode & 0o755 == 0o755

    def test_metadata_returns_copy(self, tmp_path):
        tracker = FileTracker(tmp_path)
        tracker.write_text("a.txt", "x")
        m1 = tracker.metadata()
        m1["a.txt"]["pre_existed"] = True  # mutate copy
        m2 = tracker.metadata()
        assert m2["a.txt"]["pre_existed"] is False  # original unchanged

    def test_multiple_files_tracked(self, tmp_path):
        tracker = FileTracker(tmp_path)
        tracker.write_text("a.txt", "1")
        tracker.write_text("b.txt", "2")
        tracker.write_text("c/d.txt", "3")
        meta = tracker.metadata()
        assert len(meta) == 3
        assert all(not v["pre_existed"] for v in meta.values())

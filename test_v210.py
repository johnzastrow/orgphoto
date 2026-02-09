#!/usr/bin/env python3
"""
test_v210.py - Tests for v2.1.0 features

Tests the persistent SQLite hash cache, fast EXIF extraction via exifread,
benchmark flag, and console progress output.
"""

import datetime
import hashlib
import logging
import shutil
import sqlite3
import tempfile
import time
import unittest
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import op


def _make_file(path: Path, content: bytes = b"default content") -> Path:
    """Helper: create a file with given content, creating parent dirs."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _get_test_logger() -> logging.Logger:
    """Return a logger that doesn't touch the filesystem."""
    logger = logging.getLogger(f"test.{id(object())}")
    logger.setLevel(logging.DEBUG)
    logger.addHandler(logging.NullHandler())
    return logger


# ---------------------------------------------------------------------------
# TargetHashCache — SQLite persistence
# ---------------------------------------------------------------------------


class TestHashCacheCreation(unittest.TestCase):
    """Test that TargetHashCache creates and populates the SQLite DB."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.target = self.tmp / "target"
        self.target.mkdir()
        self.logger = _get_test_logger()

    def test_db_file_created_in_target_dir(self):
        """First run creates .orgphoto_cache.db in the target directory."""
        _make_file(self.target / "a.txt", b"aaa")
        cache = op.TargetHashCache(self.target, self.logger)
        db_path = self.target / ".orgphoto_cache.db"
        self.assertTrue(db_path.exists())
        cache.close()

    def test_db_file_created_in_custom_cache_dir(self):
        """-C flag places DB in a custom directory."""
        cache_dir = self.tmp / "custom_cache"
        _make_file(self.target / "a.txt", b"aaa")
        cache = op.TargetHashCache(self.target, self.logger, cache_dir=cache_dir)
        db_path = cache_dir / ".orgphoto_cache.db"
        self.assertTrue(db_path.exists())
        # DB should NOT be in target dir
        self.assertFalse((self.target / ".orgphoto_cache.db").exists())
        cache.close()

    def test_files_indexed_on_first_run(self):
        """All files in target are hashed on first run."""
        _make_file(self.target / "a.txt", b"aaa")
        _make_file(self.target / "sub" / "b.txt", b"bbb")
        cache = op.TargetHashCache(self.target, self.logger)
        stats = cache.get_stats()
        self.assertEqual(stats["total_files"], 2)
        cache.close()

    def test_build_stats_first_run_all_hashed(self):
        """On first run, all files are freshly hashed (reused=0)."""
        _make_file(self.target / "a.txt", b"aaa")
        _make_file(self.target / "b.txt", b"bbb")
        cache = op.TargetHashCache(self.target, self.logger)
        build_stats = cache.get_build_stats()
        self.assertEqual(build_stats["hashed"], 2)
        self.assertEqual(build_stats["reused"], 0)
        cache.close()

    def test_close_sets_conn_to_none(self):
        """close() sets the connection to None."""
        cache = op.TargetHashCache(self.target, self.logger)
        cache.close()
        self.assertIsNone(cache.conn)


class TestHashCacheReuse(unittest.TestCase):
    """Test that cached hashes are reused on subsequent runs."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.target = self.tmp / "target"
        self.target.mkdir()
        self.logger = _get_test_logger()

    def test_unchanged_files_reused(self):
        """Second run reuses cached hashes for unchanged files."""
        _make_file(self.target / "a.txt", b"aaa")
        _make_file(self.target / "b.txt", b"bbb")

        # First run — hashes everything
        cache1 = op.TargetHashCache(self.target, self.logger)
        stats1 = cache1.get_build_stats()
        self.assertEqual(stats1["hashed"], 2)
        self.assertEqual(stats1["reused"], 0)
        cache1.close()

        # Second run — should reuse all
        cache2 = op.TargetHashCache(self.target, self.logger)
        stats2 = cache2.get_build_stats()
        self.assertEqual(stats2["hashed"], 0)
        self.assertEqual(stats2["reused"], 2)
        cache2.close()

    def test_modified_file_rehashed(self):
        """A file with changed content (mtime/size) is rehashed."""
        f = _make_file(self.target / "a.txt", b"original")

        cache1 = op.TargetHashCache(self.target, self.logger)
        cache1.close()

        # Modify the file — ensure mtime changes
        time.sleep(0.05)
        f.write_bytes(b"modified content that is different")

        cache2 = op.TargetHashCache(self.target, self.logger)
        stats2 = cache2.get_build_stats()
        self.assertEqual(stats2["hashed"], 1)

        # Verify the hash is for the new content
        expected_hash = _sha256(b"modified content that is different")
        duplicates = cache2.find_duplicates(f, expected_hash)
        self.assertTrue(len(duplicates) > 0)
        cache2.close()

    def test_deleted_file_stale_removed(self):
        """Deleted files are removed from the DB (stale entries)."""
        _make_file(self.target / "a.txt", b"aaa")
        _make_file(self.target / "b.txt", b"bbb")

        cache1 = op.TargetHashCache(self.target, self.logger)
        self.assertEqual(cache1.get_stats()["total_files"], 2)
        cache1.close()

        # Delete one file
        (self.target / "b.txt").unlink()

        cache2 = op.TargetHashCache(self.target, self.logger)
        stats2 = cache2.get_build_stats()
        self.assertEqual(stats2["stale_removed"], 1)
        self.assertEqual(cache2.get_stats()["total_files"], 1)
        cache2.close()

    def test_new_file_picked_up(self):
        """A new file added to target is hashed on next run."""
        _make_file(self.target / "a.txt", b"aaa")

        cache1 = op.TargetHashCache(self.target, self.logger)
        self.assertEqual(cache1.get_stats()["total_files"], 1)
        cache1.close()

        # Add a new file
        _make_file(self.target / "c.txt", b"ccc")

        cache2 = op.TargetHashCache(self.target, self.logger)
        stats2 = cache2.get_build_stats()
        self.assertEqual(stats2["reused"], 1)
        self.assertEqual(stats2["hashed"], 1)
        self.assertEqual(cache2.get_stats()["total_files"], 2)
        cache2.close()


class TestHashCacheDBOperations(unittest.TestCase):
    """Test add_file, invalidate_file, and DB persistence."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.target = self.tmp / "target"
        self.target.mkdir()
        self.logger = _get_test_logger()

    def test_add_file_persists_to_db(self):
        """add_file() inserts a record into the SQLite DB."""
        cache = op.TargetHashCache(self.target, self.logger)

        new_file = _make_file(self.target / "new.txt", b"new content")
        file_hash = _sha256(b"new content")
        cache.add_file(new_file, file_hash)

        # Verify in-memory
        self.assertEqual(cache.get_stats()["total_files"], 1)

        # Verify in DB
        rel_path = new_file.relative_to(self.target).as_posix()
        row = cache.conn.execute(
            "SELECT file_hash FROM file_hashes WHERE file_path=?", (rel_path,)
        ).fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row[0], file_hash)
        cache.close()

    def test_add_file_survives_restart(self):
        """A file added via add_file() is reused on next run."""
        cache1 = op.TargetHashCache(self.target, self.logger)
        new_file = _make_file(self.target / "new.txt", b"new content")
        cache1.add_file(new_file, _sha256(b"new content"))
        cache1.close()

        # Restart — should reuse the added file
        cache2 = op.TargetHashCache(self.target, self.logger)
        stats = cache2.get_build_stats()
        self.assertEqual(stats["reused"], 1)
        self.assertEqual(stats["hashed"], 0)
        cache2.close()

    def test_invalidate_file_removes_from_db(self):
        """invalidate_file() removes the entry from SQLite."""
        f = _make_file(self.target / "a.txt", b"aaa")
        cache = op.TargetHashCache(self.target, self.logger)
        self.assertEqual(cache.get_stats()["total_files"], 1)

        cache.invalidate_file(f)

        # Verify in-memory
        self.assertEqual(cache.get_stats()["total_files"], 0)

        # Verify in DB
        rel_path = f.relative_to(self.target).as_posix()
        row = cache.conn.execute(
            "SELECT file_hash FROM file_hashes WHERE file_path=?", (rel_path,)
        ).fetchone()
        self.assertIsNone(row)
        cache.close()

    def test_find_duplicates(self):
        """find_duplicates() returns files with matching hash."""
        content = b"duplicate content"
        _make_file(self.target / "a.txt", content)
        _make_file(self.target / "b.txt", content)

        cache = op.TargetHashCache(self.target, self.logger)
        source_file = _make_file(self.tmp / "source.txt", content)
        duplicates = cache.find_duplicates(source_file, _sha256(content))
        self.assertEqual(len(duplicates), 2)
        cache.close()

    def test_find_duplicates_no_match(self):
        """find_duplicates() returns empty list when no match."""
        _make_file(self.target / "a.txt", b"aaa")
        cache = op.TargetHashCache(self.target, self.logger)
        duplicates = cache.find_duplicates(
            self.target / "a.txt", _sha256(b"something else")
        )
        self.assertEqual(len(duplicates), 0)
        cache.close()


class TestHashCacheGracefulFallback(unittest.TestCase):
    """Test graceful degradation when DB is unavailable."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.target = self.tmp / "target"
        self.target.mkdir()
        self.logger = _get_test_logger()

    def test_corrupted_db_triggers_rebuild(self):
        """A corrupted DB file triggers graceful fallback to in-memory mode."""
        _make_file(self.target / "a.txt", b"aaa")

        # First run to create DB
        cache1 = op.TargetHashCache(self.target, self.logger)
        cache1.close()

        # Corrupt the DB
        db_path = self.target / ".orgphoto_cache.db"
        db_path.write_bytes(b"this is not a valid sqlite database")

        # Second run should still work (fallback to in-memory)
        cache2 = op.TargetHashCache(self.target, self.logger)
        # Should have hashed the file even without DB
        self.assertEqual(cache2.get_stats()["total_files"], 1)
        cache2.close()

    def test_deleted_db_rebuilds(self):
        """Deleting the DB file causes a full rebuild on next run."""
        _make_file(self.target / "a.txt", b"aaa")

        cache1 = op.TargetHashCache(self.target, self.logger)
        cache1.close()

        # Delete DB
        db_path = self.target / ".orgphoto_cache.db"
        db_path.unlink()

        # Should rebuild from scratch
        cache2 = op.TargetHashCache(self.target, self.logger)
        stats = cache2.get_build_stats()
        self.assertEqual(stats["hashed"], 1)
        self.assertEqual(stats["reused"], 0)
        cache2.close()

    def test_empty_target_dir(self):
        """Cache works correctly with an empty target directory."""
        cache = op.TargetHashCache(self.target, self.logger)
        self.assertEqual(cache.get_stats()["total_files"], 0)
        build_stats = cache.get_build_stats()
        self.assertEqual(build_stats["hashed"], 0)
        self.assertEqual(build_stats["reused"], 0)
        cache.close()

    def test_nonexistent_target_dir(self):
        """Cache handles a nonexistent target directory gracefully."""
        nonexistent = self.tmp / "does_not_exist"
        cache = op.TargetHashCache(nonexistent, self.logger)
        self.assertEqual(cache.get_stats()["total_files"], 0)
        cache.close()


class TestHashCacheSchemaVersion(unittest.TestCase):
    """Test schema version migration."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.target = self.tmp / "target"
        self.target.mkdir()
        self.logger = _get_test_logger()

    def test_schema_version_mismatch_rebuilds(self):
        """Bumping schema version causes a full table rebuild."""
        _make_file(self.target / "a.txt", b"aaa")

        # First run
        cache1 = op.TargetHashCache(self.target, self.logger)
        cache1.close()

        # Tamper with schema version in DB
        db_path = self.target / ".orgphoto_cache.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("UPDATE cache_meta SET value='0' WHERE key='schema_version'")
        conn.commit()
        conn.close()

        # Second run should detect mismatch and rebuild
        cache2 = op.TargetHashCache(self.target, self.logger)
        stats = cache2.get_build_stats()
        # All files should be freshly hashed (table was dropped and recreated)
        self.assertEqual(stats["hashed"], 1)
        self.assertEqual(stats["reused"], 0)
        cache2.close()


class TestHashCacheSkipsOwnFiles(unittest.TestCase):
    """Test that .orgphoto_cache.db* files are excluded from hashing."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.target = self.tmp / "target"
        self.target.mkdir()
        self.logger = _get_test_logger()

    def test_db_files_not_indexed(self):
        """The .orgphoto_cache.db file itself is not indexed."""
        _make_file(self.target / "photo.jpg", b"photo data")
        cache = op.TargetHashCache(self.target, self.logger)

        # Only the photo should be indexed, not the .db file
        self.assertEqual(cache.get_stats()["total_files"], 1)

        # Verify no path in cache contains the db filename
        for file_path in cache.file_to_hash_mtime:
            self.assertNotIn(".orgphoto_cache", file_path.name)
        cache.close()


# ---------------------------------------------------------------------------
# Fast EXIF extraction
# ---------------------------------------------------------------------------


class TestFastExifExtraction(unittest.TestCase):
    """Test get_created_date_fast function."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.logger = _get_test_logger()

    def test_non_image_falls_back_to_hachoir(self):
        """Non-image file (e.g. .mp4) falls back to hachoir."""
        f = _make_file(self.tmp / "video.mp4", b"not a real video")
        with patch("op.get_created_date") as mock_hachoir:
            mock_hachoir.return_value = None
            result = op.get_created_date_fast(f, self.logger)
            mock_hachoir.assert_called_once_with(f, self.logger)
            self.assertIsNone(result)

    def test_txt_file_falls_back_to_hachoir(self):
        """A .txt file is not in _EXIFREAD_EXTENSIONS, falls back."""
        f = _make_file(self.tmp / "notes.txt", b"some text")
        with patch("op.get_created_date") as mock_hachoir:
            mock_hachoir.return_value = None
            op.get_created_date_fast(f, self.logger)
            mock_hachoir.assert_called_once()

    def test_jpg_without_exif_falls_back(self):
        """A .jpg with no EXIF data falls back to hachoir."""
        # Create a fake jpg (no actual EXIF)
        f = _make_file(self.tmp / "fake.jpg", b"not a real jpeg")
        with patch("op.get_created_date") as mock_hachoir:
            mock_hachoir.return_value = None
            result = op.get_created_date_fast(f, self.logger)
            # exifread should have been tried (and found no tags),
            # then fallen back to hachoir
            mock_hachoir.assert_called_once()
            self.assertIsNone(result)

    def test_exifread_extensions_set(self):
        """Verify _EXIFREAD_EXTENSIONS covers key image/RAW formats."""
        expected = {
            ".jpg",
            ".jpeg",
            ".tif",
            ".tiff",
            ".heic",
            ".heif",
            ".cr2",
            ".nef",
            ".arw",
            ".dng",
            ".orf",
            ".png",
            ".webp",
        }
        for ext in expected:
            self.assertIn(ext, op._EXIFREAD_EXTENSIONS, f"{ext} missing")

    @patch("op._HAS_EXIFREAD", False)
    def test_no_exifread_falls_back(self):
        """When exifread is not installed, always falls back to hachoir."""
        f = _make_file(self.tmp / "photo.jpg", b"fake jpeg")
        with patch("op.get_created_date") as mock_hachoir:
            mock_hachoir.return_value = None
            op.get_created_date_fast(f, self.logger)
            mock_hachoir.assert_called_once()


class TestFastExifWithRealJpeg(unittest.TestCase):
    """Test fast EXIF with a minimal valid JPEG containing EXIF data."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.logger = _get_test_logger()

    def _make_jpeg_with_exif(self, path: Path, date_str: str = "2024:06:15 14:30:00"):
        """Create a minimal JPEG file with an EXIF DateTimeOriginal tag.

        This builds a bare-minimum JPEG: SOI, APP1 (EXIF), EOI.
        The EXIF structure is: TIFF header + IFD0 (with pointer to ExifIFD)
        + ExifIFD containing DateTimeOriginal.
        """
        import struct

        # EXIF date is always 19 chars + null terminator = 20 bytes
        date_bytes = date_str.encode("ascii") + b"\x00"

        # Build TIFF body (little-endian)
        # IFD0: 1 entry pointing to ExifIFD
        # ExifIFD: 1 entry for DateTimeOriginal
        tiff_header = b"II"  # little-endian
        tiff_header += struct.pack("<H", 42)  # TIFF magic
        tiff_header += struct.pack("<I", 8)  # offset to IFD0

        # IFD0 at offset 8
        ifd0_count = struct.pack("<H", 1)
        # ExifIFD pointer tag (0x8769), type LONG (4), count 1, value = offset to ExifIFD
        exif_ifd_offset = 8 + 2 + 12 + 4  # after IFD0
        ifd0_entry = struct.pack("<HHII", 0x8769, 4, 1, exif_ifd_offset)
        ifd0_next = struct.pack("<I", 0)  # no next IFD

        # ExifIFD
        exif_count = struct.pack("<H", 1)
        # DateTimeOriginal (0x9003), type ASCII (2), count 20
        date_data_offset = exif_ifd_offset + 2 + 12 + 4
        exif_entry = struct.pack("<HHII", 0x9003, 2, 20, date_data_offset)
        exif_next = struct.pack("<I", 0)

        tiff_body = (
            tiff_header
            + ifd0_count
            + ifd0_entry
            + ifd0_next
            + exif_count
            + exif_entry
            + exif_next
            + date_bytes
        )

        # APP1 marker
        exif_header = b"Exif\x00\x00"
        app1_data = exif_header + tiff_body
        app1_length = len(app1_data) + 2  # +2 for the length field itself

        # JPEG = SOI + APP1 + EOI
        jpeg = b"\xff\xd8"  # SOI
        jpeg += b"\xff\xe1"  # APP1 marker
        jpeg += struct.pack(">H", app1_length)
        jpeg += app1_data
        jpeg += b"\xff\xd9"  # EOI

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(jpeg)
        return path

    def test_fast_exif_reads_date_from_jpeg(self):
        """get_created_date_fast extracts DateTimeOriginal from a real JPEG."""
        jpeg_path = self._make_jpeg_with_exif(
            self.tmp / "test.jpg", "2024:06:15 14:30:00"
        )
        result = op.get_created_date_fast(jpeg_path, self.logger)
        self.assertIsNotNone(result)
        self.assertEqual(result, datetime.datetime(2024, 6, 15, 14, 30, 0))

    def test_fast_and_hachoir_agree_on_date(self):
        """get_created_date_fast and get_created_date return the same date."""
        jpeg_path = self._make_jpeg_with_exif(
            self.tmp / "test.jpg", "2023:12:25 09:00:00"
        )
        fast_result = op.get_created_date_fast(jpeg_path, self.logger)
        hachoir_result = op.get_created_date(jpeg_path, self.logger)

        # Both should find the date (hachoir may or may not parse our minimal JPEG)
        if hachoir_result is not None:
            self.assertEqual(fast_result, hachoir_result)
        else:
            # At minimum, fast should have found it via exifread
            self.assertIsNotNone(fast_result)


# ---------------------------------------------------------------------------
# CLI flag tests
# ---------------------------------------------------------------------------


class TestNoComprehensiveCheckFlag(unittest.TestCase):
    """Test -N flag skips cache creation."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.source = self.tmp / "source"
        self.dest = self.tmp / "dest"
        self.source.mkdir()
        self.dest.mkdir()

    def _cleanup_logger(self):
        """Remove file handlers from the op logger to avoid stale references."""
        logger = logging.getLogger("op")
        for handler in logger.handlers[:]:
            handler.close()
            logger.removeHandler(handler)

    def test_no_db_created_with_N_flag(self):
        """-N flag means no TargetHashCache, so no .orgphoto_cache.db."""
        _make_file(self.source / "photo.jpg", b"photo data")

        with patch("op.get_created_date") as mock_date:
            mock_date.return_value = datetime.datetime(2023, 5, 15)
            args = [
                "-c",
                "-N",
                "-j",
                "jpg",
                str(self.source),
                str(self.dest),
            ]
            with patch("sys.argv", ["op.py"] + args):
                op.main()

        self._cleanup_logger()
        db_path = self.dest / ".orgphoto_cache.db"
        self.assertFalse(db_path.exists())


class TestBenchmarkFlag(unittest.TestCase):
    """Test -B flag prints benchmark output."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.source = self.tmp / "source"
        self.dest = self.tmp / "dest"
        self.source.mkdir()
        self.dest.mkdir()

    def _cleanup_logger(self):
        logger = logging.getLogger("op")
        for handler in logger.handlers[:]:
            handler.close()
            logger.removeHandler(handler)

    def test_benchmark_prints_stats(self):
        """-B flag prints benchmark info including key fields."""
        _make_file(self.source / "photo.jpg", b"photo data")
        _make_file(self.dest / "existing.jpg", b"existing data")

        with patch("op.get_created_date") as mock_date:
            mock_date.return_value = datetime.datetime(2023, 5, 15)
            args = [
                "-c",
                "-B",
                "-j",
                "jpg",
                str(self.source),
                str(self.dest),
            ]
            with patch("sys.argv", ["op.py"] + args):
                with patch("sys.stdout", new_callable=StringIO) as mock_out:
                    op.main()
                    output = mock_out.getvalue()

        self._cleanup_logger()
        self.assertIn("Hash Cache Benchmark", output)
        self.assertIn("Total files indexed", output)
        self.assertIn("Reused from cache", output)
        self.assertIn("Freshly hashed", output)
        self.assertIn("Elapsed time", output)


class TestCacheDirFlag(unittest.TestCase):
    """Test -C flag for custom cache directory."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.source = self.tmp / "source"
        self.dest = self.tmp / "dest"
        self.cache_dir = self.tmp / "cache"
        self.source.mkdir()
        self.dest.mkdir()

    def _cleanup_logger(self):
        logger = logging.getLogger("op")
        for handler in logger.handlers[:]:
            handler.close()
            logger.removeHandler(handler)

    def test_cache_dir_flag(self):
        """-C places the DB in the specified directory."""
        _make_file(self.source / "photo.jpg", b"photo data")

        with patch("op.get_created_date") as mock_date:
            mock_date.return_value = datetime.datetime(2023, 5, 15)
            args = [
                "-c",
                "-C",
                str(self.cache_dir),
                "-j",
                "jpg",
                str(self.source),
                str(self.dest),
            ]
            with patch("sys.argv", ["op.py"] + args):
                op.main()

        self._cleanup_logger()
        self.assertTrue((self.cache_dir / ".orgphoto_cache.db").exists())
        self.assertFalse((self.dest / ".orgphoto_cache.db").exists())


class TestNoFastExifFlag(unittest.TestCase):
    """Test --no-fast-exif flag forces hachoir-only."""

    def test_flag_parsed(self):
        """--no-fast-exif is parsed correctly."""
        args = [
            "-c",
            "--no-fast-exif",
            "-j",
            "jpg",
            "/tmp/src",
            "/tmp/dst",
        ]
        parsed = op.parse_arguments(args)
        self.assertTrue(parsed.no_fast_exif)

    def test_flag_not_set_by_default(self):
        """By default, no_fast_exif is False (fast exif is enabled)."""
        args = ["-c", "-j", "jpg", "/tmp/src", "/tmp/dst"]
        parsed = op.parse_arguments(args)
        self.assertFalse(parsed.no_fast_exif)


# ---------------------------------------------------------------------------
# Console progress output
# ---------------------------------------------------------------------------


class TestConsoleProgress(unittest.TestCase):
    """Test console progress output."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.source = self.tmp / "source"
        self.dest = self.tmp / "dest"
        self.source.mkdir()
        self.dest.mkdir()

    def _cleanup_logger(self):
        logger = logging.getLogger("op")
        for handler in logger.handlers[:]:
            handler.close()
            logger.removeHandler(handler)

    def test_done_line_printed(self):
        """Console shows 'Done:' summary line after processing."""
        _make_file(self.source / "photo.jpg", b"photo data")

        with patch("op.get_created_date") as mock_date:
            mock_date.return_value = datetime.datetime(2023, 5, 15)
            args = [
                "-c",
                "-j",
                "jpg",
                str(self.source),
                str(self.dest),
            ]
            with patch("sys.argv", ["op.py"] + args):
                with patch("sys.stdout", new_callable=StringIO) as mock_out:
                    op.main()
                    output = mock_out.getvalue()

        self._cleanup_logger()
        self.assertIn("Done:", output)
        self.assertIn("1 files scanned", output)

    def test_hash_cache_ready_printed(self):
        """Console shows 'Hash cache ready' line."""
        _make_file(self.source / "photo.jpg", b"photo data")

        with patch("op.get_created_date") as mock_date:
            mock_date.return_value = datetime.datetime(2023, 5, 15)
            args = [
                "-c",
                "-j",
                "jpg",
                str(self.source),
                str(self.dest),
            ]
            with patch("sys.argv", ["op.py"] + args):
                with patch("sys.stdout", new_callable=StringIO) as mock_out:
                    op.main()
                    output = mock_out.getvalue()

        self._cleanup_logger()
        self.assertIn("Hash cache ready", output)


# ---------------------------------------------------------------------------
# Fix for pre-existing integration test failures
# ---------------------------------------------------------------------------


class TestIntegrationFixed(unittest.TestCase):
    """Integration tests with proper logger cleanup to prevent FileNotFoundError.

    The pre-existing test failures were caused by the op module's logger
    retaining a FileHandler pointing to a deleted temp directory. We fix this
    by explicitly cleaning up handlers after each test.
    """

    def setUp(self):
        self.test_root = Path(tempfile.mkdtemp())
        self.source_dir = self.test_root / "source"
        self.dest_dir = self.test_root / "dest"
        self.source_dir.mkdir()
        self.dest_dir.mkdir()

    def tearDown(self):
        """Clean up logger handlers and temp dirs."""
        logger = logging.getLogger("op")
        for handler in logger.handlers[:]:
            handler.close()
            logger.removeHandler(handler)
        shutil.rmtree(self.test_root, ignore_errors=True)

    def test_copy_mode(self):
        """Copy mode copies files and preserves originals."""
        source_file = _make_file(self.source_dir / "photo.jpg", b"photo content")

        with patch("op.get_created_date") as mock_date:
            mock_date.return_value = datetime.datetime(2023, 5, 15)
            args = ["-c", "-j", "jpg", str(self.source_dir), str(self.dest_dir)]
            with patch("sys.argv", ["op.py"] + args):
                op.main()

        expected = self.dest_dir / "2023_05_15" / "photo.jpg"
        self.assertTrue(expected.exists())
        self.assertEqual(expected.read_bytes(), b"photo content")
        self.assertTrue(source_file.exists())

    def test_move_mode(self):
        """Move mode moves files and removes originals."""
        source_file = _make_file(self.source_dir / "photo.jpg", b"photo content")

        with patch("op.get_created_date") as mock_date:
            mock_date.return_value = datetime.datetime(2023, 5, 15)
            args = ["-m", "-j", "jpg", str(self.source_dir), str(self.dest_dir)]
            with patch("sys.argv", ["op.py"] + args):
                op.main()

        expected = self.dest_dir / "2023_05_15" / "photo.jpg"
        self.assertTrue(expected.exists())
        self.assertFalse(source_file.exists())

    def test_dry_run_mode(self):
        """Dry run mode does not modify any files."""
        source_file = _make_file(self.source_dir / "photo.jpg", b"photo content")

        with patch("op.get_created_date") as mock_date:
            mock_date.return_value = datetime.datetime(2023, 5, 15)
            args = ["-d", "-c", "-j", "jpg", str(self.source_dir), str(self.dest_dir)]
            with patch("sys.argv", ["op.py"] + args):
                op.main()

        # No files should be created in dest (except events.log and cache db)
        date_dir = self.dest_dir / "2023_05_15"
        self.assertFalse(date_dir.exists())
        self.assertTrue(source_file.exists())

    def test_rename_duplicate_mode(self):
        """Rename mode with master selection: incoming promoted, existing demoted."""
        date_dir = self.dest_dir / "2023_05_15"
        _make_file(date_dir / "photo.jpg", b"existing")
        _make_file(self.source_dir / "photo.jpg", b"new content")

        with patch("op.get_created_date") as mock_date:
            mock_date.return_value = datetime.datetime(2023, 5, 15)
            args = [
                "-c",
                "-D",
                "rename",
                "-j",
                "jpg",
                str(self.source_dir),
                str(self.dest_dir),
            ]
            with patch("sys.argv", ["op.py"] + args):
                op.main()

        # Master selection promotes incoming file to primary position,
        # existing file gets demoted with duplicate suffix
        self.assertTrue((date_dir / "photo.jpg").exists())
        self.assertEqual((date_dir / "photo.jpg").read_bytes(), b"new content")
        renamed = date_dir / "photo_duplicate.jpg"
        self.assertTrue(renamed.exists())
        self.assertEqual(renamed.read_bytes(), b"existing")

    def test_redirect_duplicate_mode(self):
        """Redirect mode with master selection: incoming promoted, existing demoted to Duplicates/."""
        date_dir = self.dest_dir / "2023_05_15"
        _make_file(date_dir / "photo.jpg", b"existing")
        _make_file(self.source_dir / "photo.jpg", b"new content")

        with patch("op.get_created_date") as mock_date:
            mock_date.return_value = datetime.datetime(2023, 5, 15)
            args = [
                "-c",
                "-D",
                "redirect",
                "-j",
                "jpg",
                str(self.source_dir),
                str(self.dest_dir),
            ]
            with patch("sys.argv", ["op.py"] + args):
                op.main()

        # Master selection promotes incoming file to primary position
        self.assertTrue((date_dir / "photo.jpg").exists())
        self.assertEqual((date_dir / "photo.jpg").read_bytes(), b"new content")
        # Demoted file goes to flat Duplicates/ dir with original filename
        redirect_dir = self.dest_dir / "Duplicates"
        redirected = redirect_dir / "photo.jpg"
        self.assertTrue(redirected.exists())
        self.assertEqual(redirected.read_bytes(), b"existing")


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    unittest.main(verbosity=2)

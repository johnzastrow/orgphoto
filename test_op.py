#!/usr/bin/env python3
"""
test_op.py - Comprehensive test suite for op.py

Tests the orgphoto application with unit tests for individual functions
and integration tests for full workflow scenarios.
"""

import unittest
import tempfile
import shutil
import hashlib
import logging
from pathlib import Path
from unittest.mock import patch
from datetime import datetime

# Import the module under test
import op


class TestFileOperations(unittest.TestCase):
    """Test basic file operations and utility functions."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.test_dir)

    def test_calculate_file_hash(self):
        """Test file hash calculation."""
        # Create test file with known content
        test_file = self.test_dir / "test.txt"
        test_content = b"Hello, World!"
        test_file.write_bytes(test_content)

        # Calculate expected hash
        expected_hash = hashlib.sha256(test_content).hexdigest()

        # Test hash calculation
        result_hash = op.calculate_file_hash(test_file)
        self.assertEqual(result_hash, expected_hash)

    def test_calculate_file_hash_nonexistent(self):
        """Test hash calculation with nonexistent file."""
        nonexistent = self.test_dir / "nonexistent.txt"
        result = op.calculate_file_hash(nonexistent)
        self.assertEqual(result, "")

    def test_generate_unique_filename(self):
        """Test unique filename generation."""
        # Create existing file
        existing_file = self.test_dir / "photo.jpg"
        existing_file.touch()

        # Test unique filename generation
        new_path = op.generate_unique_filename(existing_file)
        self.assertNotEqual(new_path, existing_file)
        self.assertTrue(str(new_path).endswith("_001.jpg"))

    def test_generate_duplicate_filename(self):
        """Test duplicate filename generation."""
        original = Path("photo.jpg")

        # Test default keyword
        duplicate = op.generate_duplicate_filename(original)
        self.assertEqual(str(duplicate), "photo_duplicate.jpg")

        # Test custom keyword
        duplicate_custom = op.generate_duplicate_filename(original, "copy")
        self.assertEqual(str(duplicate_custom), "photo_copy.jpg")

    def test_generate_unique_duplicate_filename(self):
        """Test unique duplicate filename with collision handling."""
        dest_dir = self.test_dir
        filename = "photo.jpg"

        # Create conflicting file
        (dest_dir / "photo_duplicate.jpg").touch()

        # Test unique duplicate generation
        result = op.generate_unique_duplicate_filename(dest_dir, filename)
        self.assertEqual(result.name, "photo_duplicate_001.jpg")


class TestDuplicateHandling(unittest.TestCase):
    """Test duplicate handling logic."""

    def test_parse_duplicate_handling_skip(self):
        """Test parsing skip duplicate handling."""
        result = op.parse_duplicate_handling("skip")
        expected = {"skip": True}
        self.assertEqual(result, expected)

    def test_parse_duplicate_handling_content(self):
        """Test parsing content duplicate handling."""
        result = op.parse_duplicate_handling("content")
        expected = {"content": True}
        self.assertEqual(result, expected)

    def test_parse_duplicate_handling_rename(self):
        """Test parsing rename duplicate handling."""
        result = op.parse_duplicate_handling("rename")
        expected = {"rename": True}
        self.assertEqual(result, expected)

    def test_parse_duplicate_handling_invalid(self):
        """Test parsing invalid duplicate handling."""
        with self.assertRaises(ValueError):
            op.parse_duplicate_handling("invalid")


class TestArgumentValidation(unittest.TestCase):
    """Test argument parsing and validation."""

    def test_normalize_extensions(self):
        """Test extension normalization."""
        # Test comma-separated extensions
        result = op.normalize_extensions("jpg,png,gif")
        expected = [".jpg", ".png", ".gif"]
        self.assertEqual(result, expected)

        # Test single extension
        result_single = op.normalize_extensions("jpeg")
        expected_single = [".jpeg"]
        self.assertEqual(result_single, expected_single)

        # Test mixed case
        result_mixed = op.normalize_extensions("JPG,Png,GIF")
        expected_mixed = [".jpg", ".png", ".gif"]
        self.assertEqual(result_mixed, expected_mixed)


class TestBogusMetadataDates(unittest.TestCase):
    """Regression tests for v2.2.4: bogus pre-1970 metadata dates must not crash."""

    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.test_dir)
        self.logger = logging.getLogger("test_bogus_dates")
        self.logger.addHandler(logging.NullHandler())

    def test_is_plausible_creation_date_rejects_quicktime_epoch(self):
        # QuickTime/MP4 atoms with a zero creation_time parse to 1904-01-01
        self.assertFalse(op._is_plausible_creation_date(datetime(1904, 1, 1)))

    def test_is_plausible_creation_date_rejects_unix_epoch(self):
        # A cleared mtime field parses to 1970-01-01, which is before our threshold
        self.assertFalse(op._is_plausible_creation_date(datetime(1970, 1, 1)))

    def test_is_plausible_creation_date_accepts_real_photo_date(self):
        self.assertTrue(
            op._is_plausible_creation_date(datetime(2022, 6, 15, 14, 30, 0))
        )

    def test_is_plausible_creation_date_rejects_non_datetime(self):
        # Hachoir occasionally returns date or string types; we only trust datetime
        self.assertFalse(op._is_plausible_creation_date(None))
        self.assertFalse(op._is_plausible_creation_date("2022-06-15"))

    def test_get_created_date_drops_bogus_quicktime_date(self):
        # Stub extractMetadata to return a metadata object whose creation_date
        # is the 1904 epoch — get_created_date should drop it and return None.
        class FakeMetadata:
            def getValues(self, key):
                return [datetime(1904, 1, 1)] if key == "creation_date" else []

        class FakeParser:
            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

        fake = self.test_dir / "fake.mp4"
        fake.write_bytes(b"not a real mp4")

        with (
            patch("op.createParser", return_value=FakeParser()),
            patch("op.extractMetadata", return_value=FakeMetadata()),
        ):
            result = op.get_created_date(fake, self.logger)

        self.assertIsNone(result)

    def test_get_created_date_keeps_plausible_date(self):
        class FakeMetadata:
            def getValues(self, key):
                return (
                    [datetime(2022, 6, 15, 14, 30, 0)] if key == "creation_date" else []
                )

        class FakeParser:
            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

        fake = self.test_dir / "ok.mp4"
        fake.write_bytes(b"not a real mp4")

        with (
            patch("op.createParser", return_value=FakeParser()),
            patch("op.extractMetadata", return_value=FakeMetadata()),
        ):
            result = op.get_created_date(fake, self.logger)

        self.assertEqual(result, datetime(2022, 6, 15, 14, 30, 0))

    def test_calculate_master_score_handles_pre_epoch_date(self):
        # The core regression: a 1904 date must not crash with OSError on Windows.
        path = self.test_dir / "IMG_0061.MP4"
        path.touch()
        score = op.calculate_master_score(path, datetime(1904, 1, 1), self.logger)
        # Score is (has_dup_keywords, filename_length, date_timestamp).
        # Date component should be the sentinel (float('inf')) so this file
        # *loses* the "oldest wins" tiebreaker rather than winning it.
        self.assertEqual(len(score), 3)
        self.assertEqual(score[2], float("inf"))

    def test_calculate_master_score_pre_epoch_loses_to_real_date(self):
        # End-to-end: a bogus 1904 file must not be selected master over a real one.
        real_path = self.test_dir / "vacation.MP4"
        real_path.touch()
        bogus_path = self.test_dir / "IMG_0061.MP4"
        bogus_path.touch()

        real_score = op.calculate_master_score(
            real_path, datetime(2022, 6, 15), self.logger
        )
        bogus_score = op.calculate_master_score(
            bogus_path, datetime(1904, 1, 1), self.logger
        )
        # Sort ascending; the real-dated file should come first (better master).
        ranked = sorted(
            [("bogus", bogus_score), ("real", real_score)], key=lambda x: x[1]
        )
        self.assertEqual(ranked[0][0], "real")


class TestIntegration(unittest.TestCase):
    """Integration tests for full workflow scenarios."""

    def setUp(self):
        """Set up test environment."""
        self.test_root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.test_root)

        self.source_dir = self.test_root / "source"
        self.dest_dir = self.test_root / "dest"
        self.source_dir.mkdir()
        self.dest_dir.mkdir()

        # Create test logger
        self.logger = logging.getLogger("test")
        self.logger.setLevel(logging.DEBUG)

    def create_test_image(
        self, path: Path, content: bytes = None, create_dirs: bool = True
    ):
        """Create a test image file with specified content."""
        if create_dirs:
            path.parent.mkdir(parents=True, exist_ok=True)

        if content is None:
            # Create unique content based on filename
            content = f"Test image content for {path.name}".encode()

        path.write_bytes(content)
        return path

    def test_dry_run_mode(self):
        """Test dry run mode doesn't modify files."""
        # Create source files
        self.create_test_image(self.source_dir / "photo.jpg")

        # Mock datetime to return fixed date
        with patch("op.get_created_date") as mock_date:
            mock_date.return_value = datetime(2023, 5, 15)

            # Run in dry run mode
            args = [
                "-d",  # dry run
                "-c",  # copy mode
                "-j",
                "jpg",
                str(self.source_dir),
                str(self.dest_dir),
            ]

            with patch("sys.argv", ["op.py"] + args):
                with patch("builtins.input", return_value="y"):
                    op.main()

        # Verify no files were actually copied
        date_dir = self.dest_dir / "2023_05_15"
        self.assertFalse(date_dir.exists())

    def test_copy_mode_basic(self):
        """Test basic copy operation."""
        # Create source file
        source_file = self.create_test_image(self.source_dir / "photo.jpg")
        original_content = source_file.read_bytes()

        # Mock datetime to return fixed date
        with patch("op.get_created_date") as mock_date:
            mock_date.return_value = datetime(2023, 5, 15)

            args = [
                "-c",  # copy mode
                "-j",
                "jpg",
                str(self.source_dir),
                str(self.dest_dir),
            ]

            with patch("sys.argv", ["op.py"] + args):
                op.main()

        # Verify file was copied
        expected_path = self.dest_dir / "2023_05_15" / "photo.jpg"
        self.assertTrue(expected_path.exists())
        self.assertEqual(expected_path.read_bytes(), original_content)

        # Verify original still exists (copy mode)
        self.assertTrue(source_file.exists())

    def test_move_mode_basic(self):
        """Test basic move operation."""
        # Create source file
        source_file = self.create_test_image(self.source_dir / "photo.jpg")
        original_content = source_file.read_bytes()

        # Mock datetime to return fixed date
        with patch("op.get_created_date") as mock_date:
            mock_date.return_value = datetime(2023, 5, 15)

            args = [
                "-m",  # move mode
                "-j",
                "jpg",
                str(self.source_dir),
                str(self.dest_dir),
            ]

            with patch("sys.argv", ["op.py"] + args):
                op.main()

        # Verify file was moved
        expected_path = self.dest_dir / "2023_05_15" / "photo.jpg"
        self.assertTrue(expected_path.exists())
        self.assertEqual(expected_path.read_bytes(), original_content)

        # Verify original was removed (move mode)
        self.assertFalse(source_file.exists())


if __name__ == "__main__":
    # Configure logging for tests
    logging.basicConfig(level=logging.WARNING)

    # Run tests
    unittest.main(verbosity=2)

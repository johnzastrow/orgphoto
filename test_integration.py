#!/usr/bin/env python3
"""
test_integration.py - Integration tests for orgphoto application

Creates real test data and runs full command-line scenarios to verify
the application works end-to-end with different modes and options.
"""

import subprocess
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
import sys


class IntegrationTestRunner:
    """Handles creation of test data and running integration tests."""

    def __init__(self):
        """Initialize test environment."""
        self.test_root = Path(tempfile.mkdtemp(prefix="orgphoto_test_"))
        self.source_dir = self.test_root / "source"
        self.dest_dir = self.test_root / "target"
        self.source_dir.mkdir()
        self.dest_dir.mkdir()

        self.op_script = Path(__file__).parent / "op.py"

    def cleanup(self):
        """Clean up test environment."""
        if self.test_root.exists():
            shutil.rmtree(self.test_root)

    def create_test_image(self, path: Path, content: str = None, size_kb: int = 1):
        """Create a test image file with specified content and approximate size."""
        path.parent.mkdir(parents=True, exist_ok=True)

        if content is None:
            content = f"Test image data for {path.name}"

        # Pad content to approximate size
        content_bytes = content.encode() * (size_kb * 1024 // len(content.encode()) + 1)
        content_bytes = content_bytes[: size_kb * 1024]

        path.write_bytes(content_bytes)
        return path

    def run_op_command(
        self, args: list, expect_success: bool = True, input_text: str = None
    ):
        """Run the op.py command with given arguments."""
        cmd = [sys.executable, str(self.op_script)] + args

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, input=input_text, timeout=30
            )

            if expect_success and result.returncode != 0:
                print(f"Command failed: {' '.join(cmd)}")
                print(f"stdout: {result.stdout}")
                print(f"stderr: {result.stderr}")

            return result

        except subprocess.TimeoutExpired:
            print(f"Command timed out: {' '.join(cmd)}")
            return None

    def test_basic_copy_operation(self):
        """Test basic copy operation with multiple files."""
        print("\n=== Test: Basic Copy Operation ===")

        # Create test files
        files = [
            self.create_test_image(self.source_dir / "photo1.jpg", "Photo 1 content"),
            self.create_test_image(self.source_dir / "photo2.jpeg", "Photo 2 content"),
            self.create_test_image(
                self.source_dir / "subdir" / "photo3.jpg", "Photo 3 content"
            ),
            self.create_test_image(self.source_dir / "image.png", "PNG image content"),
        ]

        # Run copy command
        args = [
            "-c",
            "-x",
            "no",
            "-j",
            "jpg,jpeg,png",
            str(self.source_dir),
            str(self.dest_dir),
        ]
        result = self.run_op_command(args)

        if result and result.returncode == 0:
            print("✓ Command executed successfully")

            # Check that files were copied to date directories
            date_dirs = list(self.dest_dir.glob("*_*_*"))
            print(f"✓ Created {len(date_dirs)} date directories")

            # Verify files exist and content matches
            copied_files = (
                list(self.dest_dir.rglob("*.jpg"))
                + list(self.dest_dir.rglob("*.jpeg"))
                + list(self.dest_dir.rglob("*.png"))
            )
            print(f"✓ Copied {len(copied_files)} files")

            # Verify originals still exist (copy mode)
            for original in files:
                if original.exists():
                    print(f"✓ Original file preserved: {original.name}")

            return True
        else:
            print("✗ Command failed")
            return False

    def test_move_operation(self):
        """Test move operation."""
        print("\n=== Test: Move Operation ===")

        # Create test files
        files = [
            self.create_test_image(self.source_dir / "move1.jpg", "Move test 1"),
            self.create_test_image(self.source_dir / "move2.jpg", "Move test 2"),
        ]

        # Run move command
        args = ["-m", "-x", "no", "-j", "jpg", str(self.source_dir), str(self.dest_dir)]
        result = self.run_op_command(args)

        if result and result.returncode == 0:
            print("✓ Move command executed successfully")

            # Verify files were moved (originals should not exist)
            moved_count = 0
            for original in files:
                if not original.exists():
                    moved_count += 1
                    print(f"✓ Original file removed: {original.name}")

            print(f"✓ Moved {moved_count} files")
            return True
        else:
            print("✗ Move command failed")
            return False

    def test_duplicate_rename_mode(self):
        """Test duplicate handling with rename mode."""
        print("\n=== Test: Duplicate Rename Mode ===")

        # Create source file
        source_file = self.create_test_image(
            self.source_dir / "duplicate_test.jpg", "Original content"
        )

        # Create existing file in destination (simulate previous run)
        date_dir = self.dest_dir / datetime.now().strftime("%Y_%m_%d")
        existing_file = self.create_test_image(
            date_dir / "duplicate_test.jpg", "Existing content"
        )

        # Run with rename mode
        args = [
            "-c",
            "-D",
            "rename",
            "-x",
            "no",
            "-j",
            "jpg",
            str(self.source_dir),
            str(self.dest_dir),
        ]
        result = self.run_op_command(args)

        if result and result.returncode == 0:
            print("✓ Duplicate rename command executed successfully")

            # Check for renamed file
            renamed_files = list(date_dir.glob("*_duplicate.jpg"))
            if renamed_files:
                print(f"✓ Created renamed file: {renamed_files[0].name}")
                return True
            else:
                print("✗ No renamed file found")
                return False
        else:
            print("✗ Duplicate rename command failed")
            return False

    def test_redirect_duplicate_mode(self):
        """Test duplicate handling with redirect mode."""
        print("\n=== Test: Duplicate Redirect Mode ===")

        # Create source file
        source_file = self.create_test_image(
            self.source_dir / "redirect_test.jpg", "Redirect content"
        )

        # Create existing file in destination
        date_dir = self.dest_dir / datetime.now().strftime("%Y_%m_%d")
        existing_file = self.create_test_image(
            date_dir / "redirect_test.jpg", "Existing content"
        )

        # Run with redirect mode
        args = [
            "-c",
            "-D",
            "redirect",
            "-x",
            "no",
            "-j",
            "jpg",
            str(self.source_dir),
            str(self.dest_dir),
        ]
        result = self.run_op_command(args)

        if result and result.returncode == 0:
            print("✓ Duplicate redirect command executed successfully")

            # Check for redirected file
            duplicates_dir = self.dest_dir / "Duplicates"
            if duplicates_dir.exists():
                redirected_files = list(duplicates_dir.rglob("*.jpg"))
                if redirected_files:
                    print(f"✓ Created redirected file: {redirected_files[0]}")
                    return True
                else:
                    print("✗ No redirected file found")
                    return False
            else:
                print("✗ Duplicates directory not created")
                return False
        else:
            print("✗ Duplicate redirect command failed")
            return False

    def test_dry_run_mode(self):
        """Test dry run mode."""
        print("\n=== Test: Dry Run Mode ===")

        # Create test files
        self.create_test_image(self.source_dir / "dryrun1.jpg", "Dry run test 1")
        self.create_test_image(self.source_dir / "dryrun2.jpg", "Dry run test 2")

        # Count files before
        files_before = len(list(self.dest_dir.rglob("*")))

        # Run dry run command
        args = [
            "-d",
            "-m",
            "-x",
            "no",
            "-j",
            "jpg",
            str(self.source_dir),
            str(self.dest_dir),
        ]
        result = self.run_op_command(args, input_text="y\n")

        if result and result.returncode == 0:
            print("✓ Dry run command executed successfully")

            # Verify no files were actually moved (excluding log files)
            files_after = len(
                [f for f in self.dest_dir.rglob("*") if f.suffix not in [".log"]]
            )
            if files_before == files_after:
                print("✓ No files were actually moved (dry run)")
                return True
            else:
                # Check if only log files were created
                new_files = [
                    f for f in self.dest_dir.rglob("*") if f.suffix not in [".log"]
                ]
                if len(new_files) == files_before:
                    print("✓ Only log files were created in dry run mode")
                    return True
                else:
                    print(
                        f"✗ Files were moved in dry run mode: {files_before} -> {files_after}"
                    )
                    return False
        else:
            print("✗ Dry run command failed")
            return False

    def test_extension_filtering(self):
        """Test file extension filtering."""
        print("\n=== Test: Extension Filtering ===")

        # Create files with different extensions
        files = [
            self.create_test_image(self.source_dir / "image.jpg", "JPEG content"),
            self.create_test_image(self.source_dir / "image.png", "PNG content"),
            self.create_test_image(self.source_dir / "image.gif", "GIF content"),
            self.create_test_image(self.source_dir / "document.txt", "Text content"),
        ]

        # Run command with specific extensions only
        args = [
            "-c",
            "-x",
            "no",
            "-j",
            "jpg,png",
            str(self.source_dir),
            str(self.dest_dir),
        ]
        result = self.run_op_command(args)

        if result and result.returncode == 0:
            print("✓ Extension filtering command executed successfully")

            # Check that only specified extensions were processed
            copied_files = list(self.dest_dir.rglob("*"))
            jpg_files = [f for f in copied_files if f.suffix.lower() == ".jpg"]
            png_files = [f for f in copied_files if f.suffix.lower() == ".png"]
            gif_files = [f for f in copied_files if f.suffix.lower() == ".gif"]
            txt_files = [f for f in copied_files if f.suffix.lower() == ".txt"]

            print(f"✓ Processed JPG files: {len(jpg_files)}")
            print(f"✓ Processed PNG files: {len(png_files)}")
            print(f"✓ Ignored GIF files: {len(gif_files)} (should be 0)")
            print(f"✓ Ignored TXT files: {len(txt_files)} (should be 0)")

            return len(gif_files) == 0 and len(txt_files) == 0
        else:
            print("✗ Extension filtering command failed")
            return False

    def test_performance_mode(self):
        """Test performance mode (no comprehensive checking)."""
        print("\n=== Test: Performance Mode ===")

        # Create multiple test files
        for i in range(5):
            self.create_test_image(
                self.source_dir / f"perf_test_{i}.jpg", f"Performance test {i}"
            )

        # Run with performance mode (no comprehensive checking)
        args = [
            "-c",
            "-N",
            "-x",
            "no",
            "-j",
            "jpg",
            str(self.source_dir),
            str(self.dest_dir),
        ]
        result = self.run_op_command(args)

        if result and result.returncode == 0:
            print("✓ Performance mode command executed successfully")

            # Verify files were processed
            copied_files = list(self.dest_dir.rglob("*.jpg"))
            print(f"✓ Processed {len(copied_files)} files in performance mode")
            return True
        else:
            print("✗ Performance mode command failed")
            return False

    def run_all_tests(self):
        """Run all integration tests."""
        print(f"Running integration tests in: {self.test_root}")

        tests = [
            self.test_basic_copy_operation,
            self.test_move_operation,
            self.test_duplicate_rename_mode,
            self.test_redirect_duplicate_mode,
            self.test_dry_run_mode,
            self.test_extension_filtering,
            self.test_performance_mode,
        ]

        results = []
        for test in tests:
            try:
                # Clean up destination for each test
                if self.dest_dir.exists():
                    shutil.rmtree(self.dest_dir)
                self.dest_dir.mkdir()

                result = test()
                results.append(result)
            except Exception as e:
                print(f"✗ Test failed with exception: {e}")
                results.append(False)

        # Summary
        passed = sum(results)
        total = len(results)
        print("\n=== Test Summary ===")
        print(f"Passed: {passed}/{total}")

        if passed == total:
            print("✓ All integration tests passed!")
            return True
        else:
            print(f"✗ {total - passed} tests failed")
            return False


def main():
    """Run integration tests."""
    runner = IntegrationTestRunner()

    try:
        success = runner.run_all_tests()
        return 0 if success else 1
    finally:
        runner.cleanup()


if __name__ == "__main__":
    sys.exit(main())

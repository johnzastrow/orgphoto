#!/usr/bin/env python

r"""
op.py - Organize and copy/move photos and videos by date

SUMMARY:
--------
This script scans a source directory (recursively) for files (all types by default, or specified extensions),
extracts their creation date (preferably from EXIF metadata, or falls back to the file system date),
and copies or moves them into subfolders in a destination directory, organized by date (YYYY_MM_DD).

FEATURES:
---------
- Supports any file extension recognized by hachoir (processes all file types by default).
- Recursively processes all subfolders in the source directory.
- Uses EXIF metadata for creation date if available; otherwise, uses the file system's modification date.
- Can skip, only process, or fallback to file system date for files without EXIF metadata (configurable).
- Optionally moves files instead of copying.
- Dry run mode: simulate actions without making changes.
- Progress reporting and detailed logging to a file in the destination directory.
- Robust error handling for file operations, directory creation, and metadata extraction.
- Command-line interface with flexible options using argparse.
- Uses pathlib for modern, robust path handling.

USAGE EXAMPLES:
---------------
1. Process ALL file types (default behavior - no extension filtering):
    python op.py -c Z:\\photosync target/

2. Move JPG files from source to destination, organizing by EXIF date, skipping files without EXIF:
    python op.py -m -j jpg Z:\\photosync target/

3. Copy various file types, using file system date if EXIF is missing:
    python op.py -c -j gif,png,jpg,mov,mp4 -x no Z:\\photosync target/

4. Dry run: Simulate moving files without making changes:
    python op.py -m -d -j jpg Z:\\photosync target/

5. Only process files that do not have EXIF data (using file system date):
    python op.py -c -x fs -j jpg Z:\\photosync target/

6. Move PNG and JPEG files, verbose logging enabled:
    python op.py -m -v -j png,jpeg Z:\\photosync target/

7. Copy files with content-based duplicate detection (skip identical, rename different):
    python op.py -c -D content -j jpg Z:\\photosync target/

8. Move files with interactive duplicate handling:
    python op.py -m -D interactive -j jpg Z:\\photosync target/

9. Copy files always renaming duplicates:
    python op.py -c -D rename -j jpg Z:\\photosync target/

10. Redirect duplicates to separate directory:
    python op.py -c -D redirect -j jpg Z:\\photosync target/

11. Redirect duplicates with custom directory and keyword:
    python op.py -c -D redirect -R MyDuplicates -K copy -j jpg Z:\\photosync target/

12. Disable comprehensive SHA256 checking for better performance:
    python op.py -c -N -j jpg Z:\\photosync target/

13. Copy with comprehensive duplicate detection (checks against ALL target files):
    python op.py -c -D content -j jpg Z:\\photosync target/

14. Process all file types with dry run (no extension filtering):
    python op.py -d -x no Z:\\photosync target/

15. If neither -m nor -c is specified, the script will prompt to run in dryrun mode simulating moving files.

See --help for all options.
"""

# Standard library imports
import sys
import datetime
import logging
import shutil
import argparse
from pathlib import Path
import os
import hashlib

# Third-party library imports for metadata extraction
from hachoir.parser import createParser
from hachoir.metadata import extractMetadata
from hachoir.core import config

# Suppress hachoir warnings to keep console output clean
config.quiet = True

# Script version information
# Version History:
# v1.3.x - Original comprehensive duplicate detection system
# v1.4.0 - Added all file types as default (no extension requirement)
#          Enhanced comprehensive help text for all options
# v1.4.1 - Updated documentation and README with new features and examples
# v1.5.0 - Added version display in help output header and when run without arguments
#          Enhanced user experience with version visibility throughout interface
# v1.5.1 - Fixed version output appearing multiple times
# v1.6.0 - Added detailed conflict logging showing duplicate files and conflict reasons
#          Logs conflicting file paths and whether conflict is filename, content, or both
# v2.0.0 - MAJOR UPDATE: Intelligent master file selection system
#          Automatically determines best master file based on: shortest filename, oldest date, no duplicate keywords
#          Demotes existing files when incoming file is better master candidate
#          Protects master files from being overwritten by inferior duplicates
#          Comprehensive logging of master selection criteria and demotion actions
# v2.0.1 - Enhanced session header in log file with clear version information and formatting
#          Improved log readability with structured headers and session separators
__version__ = "2.0.1"
myversion = f"v. {__version__} 2025-10-14"


def calculate_file_hash(file_path: Path, algorithm: str = 'sha256') -> str:
    """
    Calculate hash of a file for content comparison.
    
    Args:
        file_path (Path): Path to the file to hash
        algorithm (str): Hash algorithm to use (default: sha256)
    
    Returns:
        str: Hexadecimal hash string, or empty string if error
    """
    try:
        hash_obj = hashlib.new(algorithm)
        with open(file_path, 'rb') as f:
            # Read file in chunks to handle large files efficiently
            for chunk in iter(lambda: f.read(8192), b""):
                hash_obj.update(chunk)
        return hash_obj.hexdigest()
    except Exception as e:
        logging.getLogger(__name__).error(f"Failed to calculate hash for {file_path}: {e}")
        return ""


def generate_unique_filename(dest_file_path: Path) -> Path:
    """
    Generate a unique filename by adding a numeric suffix.
    
    Args:
        dest_file_path (Path): Original destination file path
    
    Returns:
        Path: Unique file path with suffix if needed
    """
    if not dest_file_path.exists():
        return dest_file_path
    
    base_name = dest_file_path.stem
    suffix = dest_file_path.suffix
    parent = dest_file_path.parent
    counter = 1
    
    while True:
        new_name = f"{base_name}_{counter:03d}{suffix}"
        new_path = parent / new_name
        if not new_path.exists():
            return new_path
        counter += 1
        
        # Safety limit to prevent infinite loop
        if counter > 9999:
            raise ValueError(f"Too many duplicates for {dest_file_path}")


def generate_duplicate_filename(original_path: Path, duplicate_keyword: str = "duplicate") -> Path:
    """
    Generate a duplicate filename by inserting the duplicate keyword.
    
    Args:
        original_path (Path): Original file path
        duplicate_keyword (str): Keyword to insert (default: "duplicate")
    
    Returns:
        Path: New path with duplicate keyword inserted
        
    Example:
        photo.jpg -> photo_duplicate.jpg
        vacation_2023.png -> vacation_2023_duplicate.png
    """
    base_name = original_path.stem
    suffix = original_path.suffix
    parent = original_path.parent
    
    duplicate_name = f"{base_name}_{duplicate_keyword}{suffix}"
    return parent / duplicate_name


def generate_unique_duplicate_filename(dest_dir: Path, filename: str, duplicate_keyword: str = "duplicate") -> Path:
    """
    Generate a unique duplicate filename with incrementing numbers if needed.
    
    Args:
        dest_dir (Path): Destination directory
        filename (str): Original filename  
        duplicate_keyword (str): Keyword to insert
    
    Returns:
        Path: Unique duplicate filename path
        
    Examples:
        photo.jpg -> photo_duplicate.jpg (if unique)
        photo.jpg -> photo_duplicate_001.jpg (if photo_duplicate.jpg exists)
        photo.jpg -> photo_duplicate_002.jpg (if photo_duplicate_001.jpg exists)
    """
    original_path = dest_dir / filename
    base_duplicate = generate_duplicate_filename(original_path, duplicate_keyword)
    
    if not base_duplicate.exists():
        return base_duplicate
    
    # If duplicate filename exists, add incrementing numbers
    base_name = original_path.stem
    suffix = original_path.suffix
    counter = 1
    
    while True:
        new_name = f"{base_name}_{duplicate_keyword}_{counter:03d}{suffix}"
        new_path = dest_dir / new_name
        if not new_path.exists():
            return new_path
        counter += 1
        
        # Safety limit to prevent infinite loop
        if counter > 9999:
            raise ValueError(f"Too many duplicates for {original_path}")


def parse_duplicate_handling(duplicate_handling_str: str) -> dict:
    """
    Parse duplicate handling string into a dictionary of enabled modes.
    
    Args:
        duplicate_handling_str (str): Comma-separated duplicate handling modes
        
    Returns:
        dict: Dictionary with modes as keys and True as values
        
    Example:
        "redirect,rename" -> {"redirect": True, "rename": True}
        "skip" -> {"skip": True}
    """
    valid_modes = {"skip", "overwrite", "rename", "content", "interactive", "redirect"}
    
    # Split by comma and clean up
    modes = [mode.strip().lower() for mode in duplicate_handling_str.split(",")]
    
    # Validate modes
    for mode in modes:
        if mode not in valid_modes:
            raise ValueError(f"Invalid duplicate handling mode: '{mode}'. Valid modes: {', '.join(valid_modes)}")
    
    # Check for conflicting modes
    conflicts = [
        ("skip", "overwrite"),
        ("skip", "redirect"),
        ("skip", "rename"),
        ("overwrite", "redirect"),
        ("overwrite", "rename"),
    ]
    
    enabled_modes = set(modes)
    for mode1, mode2 in conflicts:
        if mode1 in enabled_modes and mode2 in enabled_modes:
            raise ValueError(f"Conflicting duplicate handling modes: '{mode1}' and '{mode2}' cannot be used together")
    
    return {mode: True for mode in modes}


def setup_redirect_directory(target_dir: Path, redirect_dir_name: str, logger) -> Path:
    """
    Set up the redirect directory for duplicate files.
    
    Args:
        target_dir (Path): Main target directory
        redirect_dir_name (str): Name or path of redirect directory
        logger: Logger instance
    
    Returns:
        Path: Full path to redirect directory
    """
    # Handle absolute vs relative paths
    if Path(redirect_dir_name).is_absolute():
        redirect_path = Path(redirect_dir_name)
    else:
        redirect_path = target_dir / redirect_dir_name
    
    # Create redirect directory if it doesn't exist
    try:
        redirect_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Redirect directory ready: {redirect_path}")
        return redirect_path
    except Exception as e:
        logger.error(f"Failed to create redirect directory {redirect_path}: {e}")
        raise


class TargetHashCache:
    """
    Cache for storing and managing SHA256 hashes of files in the target directory.
    Provides comprehensive duplicate detection across the entire target tree.
    """
    
    def __init__(self, target_dir: Path, logger):
        self.target_dir = target_dir
        self.logger = logger
        # Dictionary mapping hash -> list of file paths with that hash
        self.hash_to_files = {}
        # Dictionary mapping file path -> (hash, mtime) for cache invalidation
        self.file_to_hash_mtime = {}
        self._build_cache()
    
    def _build_cache(self):
        """Build the initial hash cache by scanning all existing files in target directory."""
        if not self.target_dir.exists():
            return
            
        self.logger.info("Building comprehensive hash cache of target directory...")
        cache_count = 0
        
        # Recursively walk through target directory
        for file_path in self.target_dir.rglob('*'):
            if file_path.is_file():
                try:
                    file_hash = calculate_file_hash(file_path)
                    if file_hash:
                        file_mtime = file_path.stat().st_mtime
                        
                        # Add to hash->files mapping
                        if file_hash not in self.hash_to_files:
                            self.hash_to_files[file_hash] = []
                        self.hash_to_files[file_hash].append(file_path)
                        
                        # Add to file->hash mapping with mtime for cache invalidation
                        self.file_to_hash_mtime[file_path] = (file_hash, file_mtime)
                        cache_count += 1
                        
                        if cache_count % 100 == 0:
                            self.logger.debug(f"Cached {cache_count} file hashes...")
                            
                except Exception as e:
                    self.logger.warning(f"Failed to hash existing file {file_path}: {e}")
        
        self.logger.info(f"Hash cache built: {cache_count} files indexed, {len(self.hash_to_files)} unique hashes")
    
    def find_duplicates(self, source_file_path: Path, source_hash: str = None):
        """
        Find all files in target directory that have the same hash as source file.
        
        Args:
            source_file_path (Path): Path to source file to check
            source_hash (str, optional): Pre-calculated hash of source file
        
        Returns:
            list: List of Path objects that are duplicates of the source file
        """
        if source_hash is None:
            source_hash = calculate_file_hash(source_file_path)
        
        if not source_hash:
            return []
        
        return self.hash_to_files.get(source_hash, [])
    
    def add_file(self, file_path: Path, file_hash: str = None):
        """
        Add a newly processed file to the cache.
        
        Args:
            file_path (Path): Path to the file that was added
            file_hash (str, optional): Pre-calculated hash of the file
        """
        if file_hash is None:
            file_hash = calculate_file_hash(file_path)
        
        if file_hash:
            file_mtime = file_path.stat().st_mtime
            
            # Add to hash->files mapping
            if file_hash not in self.hash_to_files:
                self.hash_to_files[file_hash] = []
            self.hash_to_files[file_hash].append(file_path)
            
            # Add to file->hash mapping
            self.file_to_hash_mtime[file_path] = (file_hash, file_mtime)
    
    def invalidate_file(self, file_path: Path):
        """
        Remove a file from the cache (e.g., if it was deleted or modified).
        
        Args:
            file_path (Path): Path to the file to remove from cache
        """
        if file_path in self.file_to_hash_mtime:
            old_hash, _ = self.file_to_hash_mtime[file_path]
            
            # Remove from file->hash mapping
            del self.file_to_hash_mtime[file_path]
            
            # Remove from hash->files mapping
            if old_hash in self.hash_to_files:
                try:
                    self.hash_to_files[old_hash].remove(file_path)
                    # Clean up empty hash entries
                    if not self.hash_to_files[old_hash]:
                        del self.hash_to_files[old_hash]
                except ValueError:
                    pass  # File wasn't in the list
    
    def get_stats(self):
        """Return cache statistics."""
        return {
            'total_files': len(self.file_to_hash_mtime),
            'unique_hashes': len(self.hash_to_files),
            'duplicate_groups': sum(1 for files in self.hash_to_files.values() if len(files) > 1)
        }


def set_up_logging(destination_dir: Path, verbose: bool):
    """
    Set up logging to a file in the destination directory.

    Args:
        destination_dir (Path): Directory where log file will be created
        verbose (bool): Whether to enable verbose (DEBUG) logging

    Returns:
        logging.Logger: Configured logger instance

    This function creates a logger that writes to a file named 'events.log'
    in the destination directory. The logging level is set based on the verbose flag.
    """
    # Create a logger with the module name
    logger = logging.getLogger(__name__)

    # Set logging level based on verbose flag
    level = logging.DEBUG if verbose else logging.INFO

    # Define log file path in the destination directory
    logfile = destination_dir / "events.log"

    # Ensure the log directory exists
    try:
        logfile.parent.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"Failed to create log directory: {e}")
        sys.exit(1)

    # Ensure the log file exists
    try:
        if not logfile.exists():
            logfile.touch()
    except Exception as e:
        print(f"Failed to create log file: {e}")
        sys.exit(1)

    # Configure the logger
    logger.setLevel(level)

    # Create a file handler for the log file
    ch = logging.FileHandler(logfile, encoding="utf-8")
    ch.setLevel(level)

    # Define a simple formatter that just prints the message
    formatter = logging.Formatter("%(message)s")
    ch.setFormatter(formatter)

    # Add the handler to the logger if it doesn't already have handlers
    if not logger.handlers:
        logger.addHandler(ch)

    return logger


def get_created_date(filename: Path, logger):
    """
    Attempt to extract the creation date from the file's EXIF metadata.

    Args:
        filename (Path): Path to the file to extract metadata from
        logger (logging.Logger): Logger for recording issues

    Returns:
        datetime.datetime or None: Creation date if found, otherwise None

    This function uses hachoir to parse the file and extract EXIF metadata.
    It specifically looks for the 'creation_date' metadata field.
    """
    created_date = None

    # Try to create a parser for the file
    try:
        parser = createParser(str(filename))
    except Exception as e:
        logger.debug(f"Failed to create parser for {filename}: {e}")
        return created_date

    # If parser creation failed, return None
    if not parser:
        logger.debug(f"Unable to parse file for created date: {filename}")
        return created_date

    # Extract metadata using the parser
    try:
        with parser:  # Ensure parser is properly closed
            try:
                metadata = extractMetadata(parser)
            except Exception as err:
                logger.debug(f"Metadata extraction error for {filename}: {err}")
                metadata = None

        # Check if metadata was extracted successfully
        if not metadata:
            logger.debug(f"Unable to extract metadata for {filename}")
        else:
            # Try to get creation date from metadata
            cd = metadata.getValues("creation_date")
            if len(cd) > 0:
                created_date = cd[0]
    except Exception as e:
        logger.debug(f"Error during metadata extraction for {filename}: {e}")

    return created_date


def validate_args(source_dir: Path, destination_dir: Path, logger):
    """
    Validate command line arguments for directory paths.

    Args:
        source_dir (Path): Source directory path
        destination_dir (Path): Destination directory path
        logger (logging.Logger): Logger for recording errors

    Exits:
        If source directory doesn't exist or source and destination are the same

    This function ensures that the source directory exists and that source
    and destination directories are not the same to prevent potential data loss.
    """
    # Check if source directory exists
    if not source_dir.exists() or not source_dir.is_dir():
        logger.error(f"Source directory does not exist: {source_dir}")
        sys.exit(1)

    # Check if source and destination are the same
    if source_dir.resolve() == destination_dir.resolve():
        logger.error("Source and destination directories must not be the same.")
        sys.exit(1)


def normalize_extensions(ext_string: str):
    """
    Normalize file extensions to a consistent format.

    Args:
        ext_string (str): Comma-separated list of file extensions

    Returns:
        list: List of normalized extensions, each starting with a dot

    This function processes a comma-separated string of extensions and
    ensures they are lowercase, without leading spaces, and prefixed with a dot.
    """
    # Process each extension in the comma-separated list
    return [
        "." + ext.strip().lower().lstrip(".")  # Ensure lowercase and leading dot
        for ext in ext_string.split(",")  # Split by comma
        if ext.strip()  # Skip empty extensions
    ]


def has_duplicate_keywords(filename: str) -> bool:
    """
    Check if filename contains keywords suggesting it's a duplicate from another program.

    Args:
        filename (str): Filename to check

    Returns:
        bool: True if duplicate keywords found, False otherwise
    """
    # Split filename into name and extension
    from pathlib import Path
    name_part = Path(filename).stem.lower()

    # Word-based duplicate keywords (match anywhere in filename)
    word_keywords = [
        'copy', 'duplicate', 'version', 'backup', 'alt', 'alternative',
        'copy of', 'copie', 'kopie', 'copia',  # International variations
    ]

    # Check for word-based keywords
    for keyword in word_keywords:
        if keyword in name_part:
            return True

    # Numbered duplicates - only match at the END of the filename (more specific)
    # This avoids false positives from timestamps like "20221023_171427392"
    import re

    # Match patterns like: "photo (1)", "photo_1", "photo-1", "photo copy 1"
    # These patterns specifically check for numbers at the end
    numbered_patterns = [
        r'\(\d+\)$',      # (1), (2), (3) at end
        r'_copy_?\d+$',   # _copy1, _copy_1 at end
        r'_duplicate_?\d+$',  # _duplicate1, _duplicate_1 at end
        r' \d+$',         # Space followed by number at end (like "photo 2")
    ]

    for pattern in numbered_patterns:
        if re.search(pattern, name_part):
            return True

    return False


def calculate_master_score(file_path: Path, creation_date: datetime.datetime, logger) -> tuple:
    """
    Calculate a master file score based on multiple criteria.
    Lower score = better master candidate.

    Criteria (in priority order):
    1. No duplicate keywords (highest priority)
    2. Shortest filename
    3. Oldest creation/modification date

    Args:
        file_path (Path): Path to the file
        creation_date (datetime.datetime): Creation date of the file
        logger: Logger instance

    Returns:
        tuple: (has_dup_keywords, filename_length, date_timestamp)
               Lower values = better master candidate
    """
    filename = file_path.name
    has_dup_keywords = has_duplicate_keywords(filename)
    filename_length = len(filename)
    date_timestamp = creation_date.timestamp()

    return (has_dup_keywords, filename_length, date_timestamp)


def select_master_file(incoming_file: Path, incoming_date: datetime.datetime,
                       existing_files: list, logger) -> tuple:
    """
    Determine which file should be the master among duplicates.

    Args:
        incoming_file (Path): Path to incoming file
        incoming_date (datetime.datetime): Creation date of incoming file
        existing_files (list): List of (Path, datetime) tuples for existing files
        logger: Logger instance

    Returns:
        tuple: (master_path, non_master_files)
               master_path: Path to the file that should be master
               non_master_files: List of paths that should be treated as duplicates
    """
    # Calculate scores for all files
    incoming_score = calculate_master_score(incoming_file, incoming_date, logger)

    candidates = [(incoming_file, incoming_date, incoming_score, "incoming")]

    for existing_path in existing_files:
        # Get the creation date for existing file
        try:
            existing_date = get_created_date(existing_path, logger)
            if not existing_date:
                existing_date = datetime.datetime.fromtimestamp(existing_path.stat().st_mtime)
        except Exception as e:
            logger.warning(f"Failed to get date for existing file {existing_path}: {e}")
            existing_date = datetime.datetime.now()

        existing_score = calculate_master_score(existing_path, existing_date, logger)
        candidates.append((existing_path, existing_date, existing_score, "existing"))

    # Sort by score (lower is better)
    candidates.sort(key=lambda x: x[2])

    # The first candidate is the master
    master_path, master_date, master_score, master_origin = candidates[0]
    non_masters = [c[0] for c in candidates[1:]]

    # Log the selection decision
    logger.info(f"  MASTER SELECTION: Chose {master_path.name} as master ({master_origin})")
    logger.info(f"    Criteria: has_dup_keywords={master_score[0]}, name_length={master_score[1]}, date={master_date.strftime('%Y-%m-%d %H:%M:%S')}")

    if len(candidates) > 1:
        logger.info(f"    Non-masters ({len(non_masters)}): {[p.name for p in non_masters]}")

    return (master_path, non_masters, master_origin)


def handle_file_operation(
    source_path: Path, dest_path: Path, action: str, duplicate_handling: str,
    hash_cache, redirect_path: Path, duplicate_keyword: str,
    dryrun: bool, logger, creation_date, comment: str, space: int, filename: str, flag_action: str
):
    """
    Handle file operation with comprehensive duplicate detection and various handling modes.
    
    Returns:
        int: 1 if file was processed successfully, 0 otherwise
    """
    duplicate_action = ""
    
    # Check for filename-based duplicates
    filename_exists = dest_path.exists()
    
    # Check for content-based duplicates using hash cache (if enabled)
    content_duplicates = []
    source_hash = None
    if hash_cache:
        source_hash = calculate_file_hash(source_path)
        if source_hash:
            content_duplicates = hash_cache.find_duplicates(source_path, source_hash)
    
    # Determine if we have any kind of duplicate
    has_filename_duplicate = filename_exists
    has_content_duplicate = len(content_duplicates) > 0

    # Log conflict information if duplicates detected
    if has_filename_duplicate or has_content_duplicate:
        conflict_reasons = []
        if has_filename_duplicate:
            conflict_reasons.append(f"filename conflict at {dest_path}")
        if has_content_duplicate:
            conflict_reasons.append(f"content duplicate (SHA-256 match)")
            for dup_path in content_duplicates:
                logger.info(f"  DUPLICATE CONFLICT: {filename} matches existing file {dup_path} (reason: identical content)")

        # Log combined reason if both types of conflict
        if has_filename_duplicate and has_content_duplicate:
            logger.info(f"  DUPLICATE CONFLICT: {filename} -> {dest_path} (reason: filename AND content match)")
        elif has_filename_duplicate:
            logger.info(f"  DUPLICATE CONFLICT: {filename} -> {dest_path} (reason: filename exists)")

    # Handle different duplicate scenarios based on mode
    final_dest_path = dest_path
    files_to_demote = []  # Existing files that need to be moved to duplicate location

    if has_filename_duplicate or has_content_duplicate:
        # Collect all conflicting files for master selection
        all_conflicting_files = set()
        if has_filename_duplicate and dest_path.exists():
            all_conflicting_files.add(dest_path)
        if has_content_duplicate:
            all_conflicting_files.update(content_duplicates)

        # Perform master selection to determine which file should be the master
        master_path, non_masters, master_origin = select_master_file(
            source_path, creation_date, list(all_conflicting_files), logger
        )

        # Check if incoming file is the master
        incoming_is_master = (master_origin == "incoming")

        if incoming_is_master:
            # Incoming file is the better master - need to demote existing file(s)
            logger.info(f"  MASTER PROMOTION: Incoming file {filename} is the better master")

            # Demote all non-master files (existing files in target)
            for existing_file in non_masters:
                if existing_file.exists():
                    files_to_demote.append(existing_file)
                    logger.info(f"    DEMOTION: {existing_file.name} will be moved to duplicate location")

            # The incoming file will go to the intended destination
            final_dest_path = dest_path
            duplicate_action = " [PROMOTED TO MASTER]"

        else:
            # An existing file is the master - handle incoming file per duplicate mode
            logger.info(f"  MASTER RETAINED: Existing file {master_path.name} remains as master")

            # Now handle the incoming file according to duplicate_handling mode
            if duplicate_handling == "skip":
                duplicate_action = " [SKIPPED - not master]"
                logger.info(f"  {filename}  {comment:>{space}}    skipped - existing file is better master")
                return 0

            elif duplicate_handling == "overwrite":
                # Don't overwrite the master - instead rename the incoming file
                final_dest_path = generate_unique_duplicate_filename(dest_path.parent, filename, duplicate_keyword)
                duplicate_action = f" [RENAMED - master protected -> {final_dest_path.name}]"
                logger.info(f"    Overwrite blocked - master file protected")

            elif duplicate_handling == "rename":
                final_dest_path = generate_unique_duplicate_filename(dest_path.parent, filename, duplicate_keyword)
                duplicate_action = f" [RENAMED - not master -> {final_dest_path.name}]"

            elif duplicate_handling == "content":
                if has_content_duplicate:
                    # Identical content - skip
                    duplicate_action = " [SKIPPED - identical content]"
                    logger.info(f"  {filename}  {comment:>{space}}    skipped - identical content to master")
                    return 0
                else:
                    # Different content - rename
                    final_dest_path = generate_unique_duplicate_filename(dest_path.parent, filename, duplicate_keyword)
                    duplicate_action = f" [RENAMED - different from master -> {final_dest_path.name}]"

            elif duplicate_handling == "interactive":
                choice = prompt_user_for_duplicate_action(
                    source_path, dest_path, has_content_duplicate, content_duplicates, logger
                )
                if choice == "skip":
                    duplicate_action = " [SKIPPED - user choice]"
                    logger.info(f"  {filename}  {comment:>{space}}    skipped - user choice")
                    return 0
                elif choice == "overwrite":
                    # Even in interactive mode, protect the master
                    final_dest_path = generate_unique_duplicate_filename(dest_path.parent, filename, duplicate_keyword)
                    duplicate_action = f" [RENAMED - master protected -> {final_dest_path.name}]"
                    logger.info(f"    Overwrite blocked - master file protected")
                elif choice == "rename":
                    final_dest_path = generate_unique_duplicate_filename(dest_path.parent, filename, duplicate_keyword)
                    duplicate_action = f" [RENAMED - user choice -> {final_dest_path.name}]"
                elif choice == "redirect":
                    if not redirect_path:
                        redirect_path = setup_redirect_directory(dest_path.parent.parent, "Duplicates", logger)
                    final_dest_path = redirect_path / filename
                    if final_dest_path.exists():
                        final_dest_path = generate_unique_duplicate_filename(redirect_path, filename, duplicate_keyword)
                    duplicate_action = f" [REDIRECTED - user choice -> {final_dest_path}]"

            elif duplicate_handling == "redirect":
                if not redirect_path:
                    redirect_path = setup_redirect_directory(dest_path.parent.parent, "Duplicates", logger)
                final_dest_path = redirect_path / filename
                if final_dest_path.exists():
                    final_dest_path = generate_unique_duplicate_filename(redirect_path, filename, duplicate_keyword)
                duplicate_action = f" [REDIRECTED - not master -> {final_dest_path}]"

    # Perform the actual file operation
    try:
        # First, demote any existing files if incoming file is promoted to master
        if files_to_demote and not dryrun:
            for demoted_file in files_to_demote:
                # Determine where to move the demoted file
                if duplicate_handling == "redirect" or duplicate_handling == "interactive":
                    # Move to redirect directory
                    if not redirect_path:
                        redirect_path = setup_redirect_directory(demoted_file.parent.parent, "Duplicates", logger)

                    demoted_dest = redirect_path / demoted_file.name
                    if demoted_dest.exists():
                        demoted_dest = generate_unique_duplicate_filename(redirect_path, demoted_file.name, duplicate_keyword)
                else:
                    # Rename in place
                    demoted_dest = generate_duplicate_filename(demoted_file, duplicate_keyword)
                    if demoted_dest.exists():
                        demoted_dest = generate_unique_filename(demoted_dest)

                try:
                    # Move the demoted file
                    shutil.move(str(demoted_file), str(demoted_dest))
                    logger.info(f"    DEMOTED: {demoted_file.name} -> {demoted_dest}")

                    # Update hash cache - remove old location, add new location
                    if hash_cache:
                        hash_cache.invalidate_file(demoted_file)
                        demoted_hash = calculate_file_hash(demoted_dest)
                        if demoted_hash:
                            hash_cache.add_file(demoted_dest, demoted_hash)

                except Exception as e:
                    logger.error(f"Failed to demote {demoted_file} to {demoted_dest}: {e}")
                    # Continue with other demotions even if one fails

        # Log demotion actions even in dry run mode
        if files_to_demote and dryrun:
            for demoted_file in files_to_demote:
                logger.info(f"    WOULD DEMOTE: {demoted_file.name} [DRY RUN]")

        if not dryrun:
            # Ensure destination directory exists
            final_dest_path.parent.mkdir(parents=True, exist_ok=True)

            if action == "move":
                shutil.move(str(source_path), str(final_dest_path))
            else:
                shutil.copy2(str(source_path), str(final_dest_path))

            # Update hash cache with new file (if enabled)
            if hash_cache and source_hash:
                hash_cache.add_file(final_dest_path, source_hash)

        # Format timestamp in MariaDB format (YYYY-MM-DD HH:MM:SS)
        timestamp = creation_date.strftime("%Y-%m-%d %H:%M:%S")

        # Log the operation
        logger.info(
            f"  {filename}  {comment:>{space}}  {timestamp} {flag_action:>3} {final_dest_path.parent}{duplicate_action}"
            + (" [DRY RUN]" if dryrun else "")
        )
        
        return 1
        
    except Exception as e:
        logger.error(f"Failed to {flag_action} {source_path} to {final_dest_path}: {e}")
        return 0


def prompt_user_for_duplicate_action(source_path: Path, dest_path: Path, has_content_duplicate: bool, content_duplicates: list, logger):
    """
    Prompt user interactively for how to handle a duplicate file.
    
    Returns:
        str: User's choice - 'skip', 'overwrite', 'rename', or 'redirect'
    """
    print(f"\nDuplicate detected for: {source_path.name}")
    print(f"Target location: {dest_path}")
    
    if has_content_duplicate:
        print("Content duplicates found at:")
        for dup_path in content_duplicates:
            print(f"  - {dup_path}")
    
    if dest_path.exists():
        print(f"Filename conflict at: {dest_path}")
    
    while True:
        print("\nChoose action:")
        print("  s) Skip this file")
        print("  o) Overwrite existing file(s)")
        print("  r) Rename with suffix")
        print("  R) Redirect to duplicates directory")
        choice = input("Your choice [s/o/r/R]: ").lower().strip()
        
        if choice in ['s', 'skip']:
            return 'skip'
        elif choice in ['o', 'overwrite']:
            return 'overwrite'
        elif choice in ['r', 'rename']:
            return 'rename'
        elif choice in ['R', 'redirect']:
            return 'redirect'
        else:
            print("Invalid choice. Please enter s, o, r, or R.")


def recursive_walk(
    source_dir: Path,
    destination_dir: Path,
    ext_list,
    action,
    exif_only,
    logger,
    dryrun=False,
    duplicate_handling="skip",
    no_comprehensive_check=False,
    redirect_dir="Duplicates",
    duplicate_keyword="duplicate",
    hash_cache=None,
):
    """
    Recursively walk through directories and process matching files.

    Args:
        source_dir (Path): Source directory to scan
        destination_dir (Path): Destination directory for processed files
        ext_list (list or None): List of file extensions to process, or None to process all file types
        action (str): Action to perform ("move" or "copy")
        exif_only (str): How to handle files without EXIF data
        logger (logging.Logger): Logger for recording operations
        dryrun (bool): Whether to simulate operations without making changes

    This function traverses all directories under source_dir, identifying files
    with matching extensions and processing them according to the specified action.
    It keeps track of statistics and reports progress.
    """
    # Initialize redirect path if using redirect duplicate handling
    redirect_path = None
    if duplicate_handling == "redirect":
        redirect_path = setup_redirect_directory(destination_dir, redirect_dir, logger)
    
    # Initialize counters for statistics
    total_files = 0
    processed_files = 0

    # Walk through all directories and files recursively
    for folderName, _, filenames in os.walk(source_dir):
        logger.info(f"Source Folder: {folderName}")

        # Process each file in the current folder
        for filename in filenames:
            file_extension = Path(filename).suffix.lower()

            # Check if file should be processed (either matching extension or all files mode)
            if ext_list is None or file_extension in ext_list:
                total_files += 1

                # Process the file and update count if successful
                processed_files += moveFile(
                    Path(folderName),
                    filename,
                    destination_dir,
                    action,
                    exif_only,
                    logger,
                    dryrun,
                    duplicate_handling,
                    hash_cache,
                    redirect_path,
                    duplicate_keyword,
                )

                # Report progress periodically
                if processed_files % 100 == 0:
                    logger.info(f"Processed {processed_files} files so far...")

    # Log final statistics
    logger.info(f"Total files matched: {total_files}, processed: {processed_files}")


def moveFile(
    folder: Path,
    filename: str,
    destination_dir: Path,
    action: str,
    exif_only: str,
    logger,
    dryrun=False,
    duplicate_handling="skip",
    hash_cache=None,
    redirect_path=None,
    duplicate_keyword="duplicate",
):
    """
    Move or copy a file to the destination directory, organizing by date.

    Args:
        folder (Path): Directory containing the file
        filename (str): Name of the file to process
        destination_dir (Path): Base destination directory
        action (str): "move" or "copy"
        exif_only (str): How to handle files without EXIF data
        logger (logging.Logger): Logger for recording operations
        dryrun (bool): Whether to simulate operations without making changes

    Returns:
        int: 1 if file was processed, 0 otherwise

    This function extracts the creation date from the file (either from EXIF
    or file system), creates a destination folder based on the date, and
    then copies or moves the file to that destination.
    """
    # Initialize duplicate action tracking
    duplicate_action = ""
    
    # Construct full path to the file
    fullpath = folder / filename

    # Try to get creation date from EXIF metadata
    try:
        cd = get_created_date(fullpath, logger)
    except Exception as e:
        logger.error(f"Error extracting date from {fullpath}: {e}")
        return 0

    # Default comment indicates EXIF metadata is present
    comment = " " * 9

    # If no EXIF data found, potentially fall back to file system date
    if not cd:
        # If no EXIF, fallback to file system modification time
        try:
            cd = datetime.datetime.fromtimestamp(fullpath.stat().st_mtime)
            comment = " no EXIF "  # Mark files without EXIF data
        except Exception as e:
            logger.error(f"Failed to get file system date for {fullpath}: {e}")
            return 0

    # Format the date for destination folder naming
    try:
        created_date = cd.strftime("%Y_%m_%d")
    except Exception as e:
        logger.error(f"Failed to format date for {fullpath}: {e}")
        return 0

    # Calculate space for log formatting
    space = 40 - len(filename)
    if space <= 0:
        space = 4

    # Define destination folder based on date
    destf = destination_dir / created_date

    # Handle files based on EXIF status and user preferences
    # exifOnly logic: skip, only process, or fallback for files without EXIF
    if not comment.isspace() and exif_only == "yes":
        # Skip files without EXIF if exifOnly is "yes"
        logger.info(f"  {filename}  {comment:>{space}}    skipped")
        return 0
    else:
        # Determine action label for logging
        flagM = "moved" if action == "move" else "copied"

        # Process file based on exifOnly setting
        if (
            exif_only == "no"  # Process all files
            or (exif_only == "yes" and comment.isspace())  # Only files with EXIF
            or (exif_only == "fs" and not comment.isspace())  # Only files without EXIF
        ):
            # Create destination directory if it doesn't exist
            try:
                if not destf.exists():
                    if not dryrun:
                        destf.mkdir(parents=True, exist_ok=True)
                    logger.info(f"created new destination subdir: {destf}")
            except Exception as e:
                logger.error(f"Failed to create destination subdir {destf}: {e}")
                return 0

            # Define full destination file path
            dest_file_path = destf / filename
            
            # Comprehensive duplicate detection and handling
            return handle_file_operation(
                fullpath, dest_file_path, action, duplicate_handling, 
                hash_cache, redirect_path, duplicate_keyword, 
                dryrun, logger, cd, comment, space, filename, flagM
            )
        elif exif_only == "fs" and comment.isspace():
            # Skip files with EXIF when exifOnly is "fs" (only process files without EXIF)
            logger.info(f"  {filename}  {comment:>{space}}    skipped")
            return 0
    return 0


def print_examples():
    """
    Print usage examples to the user.

    This function extracts and displays the examples section from the module's docstring.
    It's used when the --examples flag is provided.
    """
    # Extract the examples section from the module docstring
    doc_lines = __doc__.split("\n")
    examples_start = doc_lines.index("USAGE EXAMPLES:")
    examples_end = next(
        (
            i
            for i, line in enumerate(doc_lines[examples_start:], examples_start)
            if line.startswith("See --help")
        ),
        len(doc_lines),
    )

    examples = "\n".join(doc_lines[examples_start : examples_end + 1])
    print(examples)


class VersionedArgumentParser(argparse.ArgumentParser):
    """Custom ArgumentParser that displays version on error when no arguments provided."""

    def error(self, message):
        """Override error method to show version before error message."""
        # Check if this is a "required arguments" error with no args provided
        if "required" in message and len(sys.argv) == 1:
            sys.stderr.write(f"orgphoto {myversion}\n\n")
            sys.stderr.write(f"error: {message}\n")
            sys.stderr.write(f"Try 'op.py --help' for more information.\n")
        else:
            sys.stderr.write(f"{self.prog}: error: {message}\n")
            sys.stderr.write(f"Try '{self.prog} --help' for more information.\n")
        sys.exit(2)


def parse_arguments(args=None):
    """
    Parse command line arguments using argparse.

    Args:
        args (list, optional): Command line arguments. Defaults to None.

    Returns:
        argparse.Namespace: Parsed arguments

    This function handles command line argument parsing, including special
    handling for the --examples flag which can be used without required positional arguments.
    """
    # First check if --examples is in the args
    if args is None:
        args = sys.argv[1:]

    # Special handling for --examples flag to bypass required arguments
    if "--examples" in args:
        print_examples()
        sys.exit(0)

    # Regular argument parsing with custom parser that shows version on error
    parser = VersionedArgumentParser(
        prog="op.py",
        description="Organize files by date with comprehensive duplicate detection. Scans source directory recursively, extracts creation dates from EXIF metadata or filesystem, and organizes files into date-based subdirectories (YYYY_MM_DD). Supports all file types recognized by hachoir library with advanced duplicate handling strategies.",
        epilog="""
IMPORTANT NOTES:
• If neither --move nor --copy is specified, script prompts for dry-run mode
• All operations are logged to 'events.log' in destination directory
• Use --examples to see comprehensive usage scenarios
• Default behavior processes ALL file types (not just images)
• Comprehensive SHA-256 duplicate checking enabled by default for accuracy
• Use -d/--dryrun to preview operations before making changes""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Required positional arguments
    parser.add_argument(
        "source_dir",
        help="Source directory containing files to organize. Will be scanned recursively for all subdirectories. Example: '/Users/photos/unsorted' or 'C:\\Photos\\Import'",
        metavar="SOURCE_DIR",
    )

    parser.add_argument(
        "destination_dir",
        help="Destination directory where organized files will be placed in date-based subdirectories (YYYY_MM_DD format). Directory will be created if it doesn't exist. Example: '/Users/photos/organized' or 'C:\\Photos\\Archive'",
        metavar="DEST_DIR",
    )

    # Create a mutually exclusive group for move/copy options
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "-m",
        "--move",
        action="store_true",
        help="Move files from source to destination (removes originals). Files are physically relocated, freeing up space in source directory. Use for permanent organization. Cannot be used with --copy.",
    )

    group.add_argument(
        "-c",
        "--copy",
        action="store_true",
        help="Copy files from source to destination (preserves originals). Files remain in source directory and are duplicated to destination. Use for creating organized backup while keeping originals. Cannot be used with --move.",
    )

    # Other optional arguments
    parser.add_argument(
        "-j",
        "--extensions",
        default=None,
        help="File extensions to process, comma-separated without dots. Examples: 'jpg,png,heic' for photos, 'mp4,mov,avi' for videos, 'jpg,png,mp4,mov' for mixed media. Supports all 33+ formats recognized by hachoir library including images (jpg, png, gif, heic, tiff), videos (mp4, mov, avi, flv), audio (mp3, wav, flac), and documents (pdf). If not specified, processes ALL supported file types [default: all types]",
        metavar="EXT",
        dest="extense",
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logging with detailed information about each file operation, duplicate detection results, hash calculations, and comprehensive processing statistics. Useful for troubleshooting and understanding exactly what the script is doing. Output is saved to events.log in destination directory.",
    )

    parser.add_argument(
        "-x",
        "--exifOnly",
        choices=["yes", "no", "fs"],
        default="yes",
        help="Control how files without EXIF metadata are handled: 'yes' (default) = skip files with no EXIF date, only process files with embedded metadata timestamps; 'no' = process ALL files, using EXIF date when available or filesystem modification date as fallback; 'fs' = only process files WITHOUT EXIF data using filesystem dates. Use 'no' for comprehensive processing including documents/videos, 'yes' for photos with reliable timestamps, 'fs' for files that may have been modified but lack metadata.",
    )

    parser.add_argument(
        "-d",
        "--dryrun",
        action="store_true",
        help="Dry run mode: simulate all operations without actually moving or copying files. Shows exactly what would happen including file destinations, duplicate handling actions, and directory creation. All activities are logged with '[DRY RUN]' markers. Perfect for testing settings and previewing results before running actual operation. No files or directories are modified in source or destination.",
    )

    parser.add_argument(
        "-D",
        "--duplicate-handling",
        default="skip",
        help="Duplicate handling strategy when files with same name or content exist: 'skip' (default) = skip duplicates, safest option; 'overwrite' = replace existing files, USE WITH CAUTION; 'rename' = add '_duplicate' suffix to create unique names; 'content' = skip only if content identical (SHA-256), rename if name conflicts but different content; 'interactive' = prompt user for each duplicate with full context; 'redirect' = move duplicates to separate directory (see -R option). Content-based modes use comprehensive SHA-256 checking for accuracy.",
        dest="duplicate_handling",
    )

    parser.add_argument(
        "-N",
        "--no-comprehensive-check",
        action="store_true",
        help="Disable comprehensive SHA-256 content checking for significant performance improvement. By default, every incoming file is checked against ALL existing target files for true duplicate detection. This flag limits checking to filename conflicts only, dramatically faster for large target directories (>50,000 files) but may miss content duplicates with different names. Use for speed when content accuracy is less critical.",
        dest="no_comprehensive_check",
    )

    parser.add_argument(
        "-R",
        "--redirect-dir",
        default="Duplicates",
        help="Directory name for duplicate files when using '-D redirect' mode. Can be relative (created under destination) or absolute path. Examples: 'MyDuplicates', 'Archive/Duplicates', '/backup/duplicates'. Duplicates maintain date organization within this directory. Only used with '--duplicate-handling redirect' [default: Duplicates]",
        dest="redirect_dir",
    )

    parser.add_argument(
        "-K",
        "--duplicate-keyword",
        default="duplicate",
        help="Custom keyword inserted into filenames for duplicate handling. Used with '-D rename', '-D redirect', and '-D content' modes. Examples: 'copy' creates 'photo_copy.jpg', 'version' creates 'photo_version.jpg', 'alt' creates 'photo_alt.jpg'. Multiple duplicates get incremental numbers: 'photo_copy_001.jpg', 'photo_copy_002.jpg'. Keep short to avoid long filenames [default: duplicate]",
        dest="duplicate_keyword",
    )

    parser.add_argument(
        "--examples",
        action="store_true",
        help="Display comprehensive usage examples covering all major features and exit. Shows real-world scenarios for basic operations, duplicate handling modes, performance optimization, and advanced combinations. Useful quick reference for command construction.",
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
        help="Show program version and exit",
    )

    # Parse the arguments
    parsed_args = parser.parse_args(args)
    return parsed_args


def main(args=None):
    """
    Main entry point for the script.

    Args:
        args (list, optional): Command line arguments. Defaults to None.

    This function orchestrates the entire process: parsing arguments,
    setting up logging, validating directories, and initiating the file processing.
    It also handles user interaction when required actions aren't specified.
    """
    # Parse command line arguments
    parsed_args = parse_arguments(args)

    # Normalize and validate extensions
    if parsed_args.extense is None:
        # Process all file types - use None to indicate no extension filtering
        ext_list = None
    else:
        ext_list = normalize_extensions(parsed_args.extense)

    # Determine action: move, copy, or prompt user
    move_flag = parsed_args.move
    copy_flag = parsed_args.copy
    dryrun = parsed_args.dryrun
    action = None

    # Set action based on flags
    if move_flag:
        action = "move"
    elif copy_flag:
        action = "copy"
    else:
        # Neither move nor copy specified: prompt user
        print(f"orgphoto {myversion}")
        print("Warning: Neither --move nor --copy specified.")
        print(
            "Would you like to run in dryrun mode simulating moving files? [Y/n]: ",
            end="",
        )
        try:
            user_input = input().strip().lower()
        except EOFError:
            user_input = "y"
        if user_input in ("", "y", "yes"):
            dryrun = True
            action = "move"
            print("Running in dryrun mode simulating moving files.")
        else:
            print("No action selected. Exiting.")
            sys.exit(1)

    # Convert string paths to Path objects and resolve them
    source_dir = Path(parsed_args.source_dir).expanduser().resolve()
    destination_dir = Path(parsed_args.destination_dir).expanduser().resolve()

    # Set up logging to a file in the destination directory
    logger = set_up_logging(destination_dir, parsed_args.verbose)

    # Log script start with comprehensive version information
    start_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logger.info("=" * 80)
    logger.info(f"orgphoto - Photo Organization Tool")
    logger.info(f"Version: {__version__} (Release Date: 2025-10-14)")
    logger.info(f"Session Started: {start_time}")
    logger.info("=" * 80)
    logger.debug("Command-line options: %s", vars(parsed_args))

    # Validate source and destination directories
    validate_args(source_dir, destination_dir, logger)
    
    # Log extension processing mode
    if ext_list is None:
        logger.info("Processing ALL file types supported by hachoir")
    else:
        logger.info(f"Processing files with extensions: {', '.join(ext_list)}")

    # Ensure destination directory exists
    try:
        if not destination_dir.exists():
            destination_dir.mkdir(parents=True, exist_ok=True)
            logger.info("created: %s", destination_dir)
    except Exception as e:
        logger.error(f"Failed to create destination directory {destination_dir}: {e}")
        sys.exit(1)

    # Initialize hash cache for comprehensive duplicate detection (unless disabled)
    hash_cache = None
    if not parsed_args.no_comprehensive_check:
        hash_cache = TargetHashCache(destination_dir, logger)
    
    # Begin recursive processing of files
    recursive_walk(
        source_dir,
        destination_dir,
        ext_list,
        action,
        parsed_args.exifOnly,
        logger,
        dryrun,
        duplicate_handling=parsed_args.duplicate_handling,
        no_comprehensive_check=parsed_args.no_comprehensive_check,
        redirect_dir=parsed_args.redirect_dir,
        duplicate_keyword=parsed_args.duplicate_keyword,
        hash_cache=hash_cache,
    )

    # Log script end
    end_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logger.info("=" * 80)
    logger.info(f"Session Ended: {end_time}")
    logger.info("=" * 80)
    logger.info("")  # Add blank line between sessions

    # Ensure all log messages are written
    logging.shutdown()


if __name__ == "__main__":
    main()

#!/usr/bin/env python

r"""
op.py - Organize and copy/move photos and videos by date

SUMMARY:
--------
This script scans a source directory (recursively) for image and video files with specified extensions,
extracts their creation date (preferably from EXIF metadata, or falls back to the file system date),
and copies or moves them into subfolders in a destination directory, organized by date (YYYY_MM_DD).

FEATURES:
---------
- Supports any file extension recognized by hachoir (default: jpeg, jpg).
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
1. Move JPG files from source to destination, organizing by EXIF date, skipping files without EXIF:
    python op.py -m -j jpg Z:\\photosync target/

2. Copy various file types, using file system date if EXIF is missing:
    python op.py -c -j gif,png,jpg,mov,mp4 -x no Z:\\photosync target/

3. Dry run: Simulate moving files without making changes:
    python op.py -m -d -j jpg Z:\\photosync target/

4. Only process files that do not have EXIF data (using file system date):
    python op.py -c -x fs -j jpg Z:\\photosync target/

5. Move PNG and JPEG files, verbose logging enabled:
    python op.py -m -v -j png,jpeg Z:\\photosync target/

6. Copy files with content-based duplicate detection (skip identical, rename different):
    python op.py -c -D content -j jpg Z:\\photosync target/

7. Move files with interactive duplicate handling:
    python op.py -m -D interactive -j jpg Z:\\photosync target/

8. Copy files always renaming duplicates:
    python op.py -c -D rename -j jpg Z:\\photosync target/

9. Redirect duplicates to separate directory:
    python op.py -c -D redirect -j jpg Z:\\photosync target/

10. Redirect duplicates with custom directory and keyword:
    python op.py -c -D redirect -R MyDuplicates -K copy -j jpg Z:\\photosync target/

11. Disable comprehensive SHA256 checking for better performance:
    python op.py -c -N -j jpg Z:\\photosync target/

12. Copy with comprehensive duplicate detection (checks against ALL target files):
    python op.py -c -D content -j jpg Z:\\photosync target/

13. If neither -m nor -c is specified, the script will prompt to run in dryrun mode simulating moving files.

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
myversion = "v. 1.3 Cheesy Dibbles 2025-06-17"


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
        for ext in ext_string.split(",")       # Split by comma
        if ext.strip()                         # Skip empty extensions
    ]


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
):
    """
    Recursively walk through directories and process matching files.
    
    Args:
        source_dir (Path): Source directory to scan
        destination_dir (Path): Destination directory for processed files
        ext_list (list): List of file extensions to process
        action (str): Action to perform ("move" or "copy")
        exif_only (str): How to handle files without EXIF data
        logger (logging.Logger): Logger for recording operations
        dryrun (bool): Whether to simulate operations without making changes
        duplicate_handling (str): How to handle duplicate files
        no_comprehensive_check (bool): Whether to skip comprehensive SHA256 checking
        redirect_dir (str): Directory for redirected duplicates
        duplicate_keyword (str): Keyword for duplicate filenames
    
    This function traverses all directories under source_dir, identifying files
    with matching extensions and processing them according to the specified action.
    It keeps track of statistics and reports progress.
    """
    # Initialize counters for statistics
    total_files = 0
    processed_files = 0
    
    # Initialize comprehensive hash cache if enabled
    hash_cache = None
    if not no_comprehensive_check:
        hash_cache = TargetHashCache(destination_dir, logger)
        cache_stats = hash_cache.get_stats()
        if cache_stats['total_files'] > 0:
            logger.info(f"Target directory analysis: {cache_stats['total_files']} files, "
                       f"{cache_stats['unique_hashes']} unique, "
                       f"{cache_stats['duplicate_groups']} duplicate groups found")
    
    # Set up redirect directory if needed
    redirect_path = None
    if duplicate_handling == "redirect":
        redirect_path = setup_redirect_directory(destination_dir, redirect_dir, logger)
    
    # Walk through all directories and files recursively
    for folderName, _, filenames in os.walk(source_dir):
        logger.info(f"Source Folder: {folderName}")
        
        # Process each file in the current folder
        for filename in filenames:
            file_extension = Path(filename).suffix.lower()
            
            # Check if file extension matches any in our list
            if file_extension in ext_list:
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
        duplicate_handling (str): How to handle duplicate files
        hash_cache (TargetHashCache): Cache for comprehensive duplicate detection
        redirect_path (Path): Path to redirect directory for duplicates
        duplicate_keyword (str): Keyword for duplicate filenames
    
    Returns:
        int: 1 if file was processed, 0 otherwise
    
    This function extracts the creation date from the file (either from EXIF
    or file system), creates a destination folder based on the date, and
    then copies or moves the file to that destination.
    """
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
            
            # Handle comprehensive duplicate detection first
            final_dest_path = dest_file_path
            should_process = True
            duplicate_action = ""
            source_hash = None
            existing_duplicates = []
            
            # Step 1: Comprehensive SHA256 checking against all target files
            if hash_cache:
                # Calculate hash of source file for comprehensive checking (even in dry-run)
                source_hash = calculate_file_hash(fullpath)
                if source_hash:
                    existing_duplicates = hash_cache.find_duplicates(fullpath, source_hash)
                    
                    if existing_duplicates:
                        # Found identical file(s) somewhere in target directory
                        duplicate_paths = [str(p.relative_to(destination_dir)) for p in existing_duplicates]
                        logger.info(f"  {filename}  {comment:>{space}}    identical to: {', '.join(duplicate_paths)}")
                        
                        if duplicate_handling == "skip":
                            should_process = False
                            duplicate_action = " [SKIPPED - IDENTICAL FILE EXISTS]"
                        elif duplicate_handling == "overwrite":
                            # Remove existing duplicates from cache since we'll overwrite
                            for dup_path in existing_duplicates:
                                hash_cache.invalidate_file(dup_path)
                            duplicate_action = " [OVERWRITING IDENTICAL FILES]"
                        elif duplicate_handling == "rename":
                            try:
                                final_dest_path = generate_unique_filename(dest_file_path)
                                duplicate_action = f" [RENAMED DUE TO IDENTICAL CONTENT: {final_dest_path.name}]"
                            except ValueError as e:
                                logger.error(f"Failed to generate unique filename: {e}")
                                return 0
                        elif duplicate_handling == "content":
                            # Content mode: skip identical files
                            should_process = False
                            duplicate_action = " [SKIPPED - IDENTICAL CONTENT]"
                        elif duplicate_handling == "redirect":
                            # Redirect to duplicate directory with renaming
                            if redirect_path:
                                try:
                                    final_dest_path = generate_unique_duplicate_filename(redirect_path, filename, duplicate_keyword)
                                    duplicate_action = f" [REDIRECTED TO {redirect_path.name}/{final_dest_path.name}]"
                                except ValueError as e:
                                    logger.error(f"Failed to generate redirect filename: {e}")
                                    return 0
                            else:
                                logger.error("Redirect directory not set up for redirect mode")
                                return 0
                        elif duplicate_handling == "interactive":
                            # Interactive: ask user what to do with comprehensive duplicate
                            print(f"\nIdentical file found in target directory:")
                            print(f"Source: {fullpath}")
                            print(f"Existing: {', '.join(str(p) for p in existing_duplicates)}")
                            while True:
                                prompt = "(s)kip, (o)verwrite existing, (r)ename new file"
                                if redirect_path:
                                    prompt += ", or re(d)irect to duplicate directory"
                                choice = input(f"{prompt}? ").lower().strip()
                                
                                if choice in ['s', 'skip']:
                                    should_process = False
                                    duplicate_action = " [USER CHOSE SKIP - IDENTICAL]"
                                    break
                                elif choice in ['o', 'overwrite']:
                                    for dup_path in existing_duplicates:
                                        hash_cache.invalidate_file(dup_path)
                                    duplicate_action = " [USER CHOSE OVERWRITE - IDENTICAL]"
                                    break
                                elif choice in ['r', 'rename']:
                                    try:
                                        final_dest_path = generate_unique_filename(dest_file_path)
                                        duplicate_action = f" [USER CHOSE RENAME - IDENTICAL: {final_dest_path.name}]"
                                        break
                                    except ValueError as e:
                                        print(f"Error generating unique filename: {e}")
                                        continue
                                elif choice in ['d', 'redirect'] and redirect_path:
                                    try:
                                        final_dest_path = generate_unique_duplicate_filename(redirect_path, filename, duplicate_keyword)
                                        duplicate_action = f" [USER CHOSE REDIRECT - IDENTICAL: {redirect_path.name}/{final_dest_path.name}]"
                                        break
                                    except ValueError as e:
                                        print(f"Error generating redirect filename: {e}")
                                        continue
                                else:
                                    valid_choices = "s, o, r"
                                    if redirect_path:
                                        valid_choices += ", d"
                                    print(f"Invalid choice. Please enter {valid_choices}.")
            
            # Step 2: Traditional filename-based duplicate checking (only if no comprehensive duplicates found)
            if should_process and dest_file_path.exists() and not existing_duplicates:
                if duplicate_handling == "skip":
                    # Current behavior: skip if file exists
                    logger.info("  " + filename + " already exists in " + str(destf))
                    should_process = False
                    
                elif duplicate_handling == "overwrite":
                    # Always overwrite existing files
                    duplicate_action = " [OVERWRITING]"
                    
                elif duplicate_handling == "rename":
                    # Generate unique filename
                    try:
                        final_dest_path = generate_unique_filename(dest_file_path)
                        duplicate_action = f" [RENAMED TO {final_dest_path.name}]"
                    except ValueError as e:
                        logger.error(f"Failed to generate unique filename: {e}")
                        return 0
                        
                elif duplicate_handling == "content":
                    # Compare file hashes
                    if not dryrun:  # Only calculate hashes if not dry run
                        source_hash = calculate_file_hash(fullpath)
                        dest_hash = calculate_file_hash(dest_file_path)
                        
                        if source_hash and dest_hash:
                            if source_hash == dest_hash:
                                # Identical content, skip
                                logger.info(f"  {filename}  {comment:>{space}}    identical content, skipped")
                                should_process = False
                            else:
                                # Different content, rename
                                try:
                                    final_dest_path = generate_unique_filename(dest_file_path)
                                    duplicate_action = f" [DIFFERENT CONTENT, RENAMED TO {final_dest_path.name}]"
                                except ValueError as e:
                                    logger.error(f"Failed to generate unique filename: {e}")
                                    return 0
                        else:
                            # Hash calculation failed, fall back to rename
                            try:
                                final_dest_path = generate_unique_filename(dest_file_path)
                                duplicate_action = f" [HASH FAILED, RENAMED TO {final_dest_path.name}]"
                            except ValueError as e:
                                logger.error(f"Failed to generate unique filename: {e}")
                                return 0
                    else:
                        # Dry run, assume content comparison
                        duplicate_action = " [DRY RUN - WOULD COMPARE CONTENT]"
                        
                elif duplicate_handling == "redirect":
                    # Redirect to duplicate directory with renaming
                    if redirect_path:
                        try:
                            final_dest_path = generate_unique_duplicate_filename(redirect_path, filename, duplicate_keyword)
                            duplicate_action = f" [REDIRECTED TO {redirect_path.name}/{final_dest_path.name}]"
                        except ValueError as e:
                            logger.error(f"Failed to generate redirect filename: {e}")
                            return 0
                    else:
                        logger.error("Redirect directory not set up for redirect mode")
                        return 0
                        
                elif duplicate_handling == "interactive":
                    # Prompt user for decision
                    print(f"\nDuplicate found: {dest_file_path}")
                    print(f"Source: {fullpath}")
                    while True:
                        choice = input("(s)kip, (o)verwrite, (r)ename, or (c)ompare content? ").lower().strip()
                        if choice in ['s', 'skip']:
                            should_process = False
                            duplicate_action = " [USER CHOSE SKIP]"
                            break
                        elif choice in ['o', 'overwrite']:
                            duplicate_action = " [USER CHOSE OVERWRITE]"
                            break
                        elif choice in ['r', 'rename']:
                            try:
                                final_dest_path = generate_unique_filename(dest_file_path)
                                duplicate_action = f" [USER CHOSE RENAME TO {final_dest_path.name}]"
                                break
                            except ValueError as e:
                                print(f"Error generating unique filename: {e}")
                                continue
                        elif choice in ['c', 'compare']:
                            if not dryrun:
                                source_hash = calculate_file_hash(fullpath)
                                dest_hash = calculate_file_hash(dest_file_path)
                                if source_hash and dest_hash and source_hash == dest_hash:
                                    print("Files have identical content.")
                                    should_process = False
                                    duplicate_action = " [IDENTICAL CONTENT, SKIPPED]"
                                    break
                                else:
                                    print("Files have different content.")
                                    try:
                                        final_dest_path = generate_unique_filename(dest_file_path)
                                        duplicate_action = f" [DIFFERENT CONTENT, RENAMED TO {final_dest_path.name}]"
                                        break
                                    except ValueError as e:
                                        print(f"Error generating unique filename: {e}")
                                        continue
                            else:
                                duplicate_action = " [DRY RUN - WOULD COMPARE]"
                                break
                        else:
                            print("Invalid choice. Please enter s, o, r, or c.")
            
            if should_process:
                try:
                    # Perform the actual move or copy operation
                    if not dryrun:
                        final_dest_dir = final_dest_path.parent
                        if action == "move":
                            shutil.move(str(fullpath), str(final_dest_path))
                        else:
                            shutil.copy2(str(fullpath), str(final_dest_path))
                        
                        # Update hash cache with the newly added file
                        if hash_cache:
                            # Use the already calculated hash if available
                            if source_hash is None:
                                source_hash = calculate_file_hash(final_dest_path)
                            hash_cache.add_file(final_dest_path, source_hash)
                            
                    # Format timestamp in MariaDB format (YYYY-MM-DD HH:MM:SS)
                    timestamp = cd.strftime("%Y-%m-%d %H:%M:%S")
                    
                    # Log the operation
                    logger.info(
                        f"  {filename}  {comment:>{space}}  {timestamp} {flagM:>3} {final_dest_path.parent}{duplicate_action}"
                        + (" [DRY RUN]" if dryrun else "")
                    )
                except Exception as e:
                    logger.error(f"Failed to {flagM} {fullpath} to {final_dest_path}: {e}")
                    return 0
            return 1
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
    doc_lines = __doc__.split('\n')
    examples_start = doc_lines.index("USAGE EXAMPLES:") 
    examples_end = next((i for i, line in enumerate(doc_lines[examples_start:], examples_start) 
                         if line.startswith("See --help")), len(doc_lines))
    
    examples = '\n'.join(doc_lines[examples_start:examples_end+1])
    print(examples)


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
    
    # Regular argument parsing
    parser = argparse.ArgumentParser(
        description="Organize and copy/move photos and videos by date",
        epilog="If neither --move nor --copy is specified, the script will prompt to run in dryrun mode simulating moving files.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    # Required positional arguments
    parser.add_argument(
        "source_dir",
        help="Source directory containing images/videos to organize",
        metavar="SOURCE_DIR",
    )
    
    parser.add_argument(
        "destination_dir",
        help="Destination directory where organized files will be placed",
        metavar="DEST_DIR",
    )
    
    # Create a mutually exclusive group for move/copy options
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "-m", "--move",
        action="store_true",
        help="Move files (cannot be used with --copy)",
    )
    
    group.add_argument(
        "-c", "--copy",
        action="store_true",
        help="Copy files (cannot be used with --move)",
    )
    
    # Other optional arguments
    parser.add_argument(
        "-j", "--extensions",
        default="jpeg,jpg",
        help="Extension list - comma separated [default: jpeg,jpg]. Supports all extensions of hachoir",
        metavar="EXT",
        dest="extense",
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Talk more",
    )
    
    parser.add_argument(
        "-x", "--exifOnly",
        choices=["yes", "no", "fs"],
        default="yes",
        help="'yes': skip files with no EXIF, 'no': process all files (fallback to filesystem date), 'fs': only process files with no EXIF [default: yes]",
    )
    
    parser.add_argument(
        "-d", "--dryrun",
        action="store_true",
        help="Dry run mode: simulate actions, do not move/copy files",
    )
    
    parser.add_argument(
        "-D", "--duplicate-handling",
        default="skip",
        help="How to handle duplicate files: 'skip' (default, current behavior), 'overwrite' (replace existing), 'rename' (add suffix), 'content' (compare file hashes, skip identical, rename different), 'interactive' (prompt for each), 'redirect' (move duplicates to redirect directory), or comma-separated combinations like 'redirect,rename'",
    )
    
    parser.add_argument(
        "-N", "--no-comprehensive-check",
        action="store_true",
        help="Disable comprehensive SHA256 checking against all existing target files (default: enabled). When disabled, only checks for filename conflicts. Use this for better performance with large target directories.",
    )
    
    parser.add_argument(
        "-R", "--redirect-dir",
        default="Duplicates",
        help="Directory name for redirected duplicate files (default: 'Duplicates'). Created in target root directory. Can be absolute path or relative to target.",
        metavar="DIR",
    )
    
    parser.add_argument(
        "-K", "--duplicate-keyword",
        default="duplicate",
        help="Keyword to insert in filenames when renaming duplicates (default: 'duplicate'). Used with redirect mode and rename mode.",
        metavar="WORD",
    )
    
    parser.add_argument(
        "--examples",
        action="store_true",
        help="Show usage examples and exit",
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

    # Log script start with MariaDB TIMESTAMP format (YYYY-MM-DD HH:MM:SS)
    start_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logger.info(f"{10 * '-'}{myversion}++ Started: {start_time}")
    logger.debug(f"options: {vars(parsed_args)}")

    # Validate source and destination directories
    validate_args(source_dir, destination_dir, logger)

    # Ensure destination directory exists
    try:
        if not destination_dir.exists():
            destination_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"created: {destination_dir}")
    except Exception as e:
        logger.error(f"Failed to create destination directory {destination_dir}: {e}")
        sys.exit(1)

    # Begin recursive processing of files
    recursive_walk(
        source_dir, destination_dir, ext_list, action, parsed_args.exifOnly, logger, dryrun, parsed_args.duplicate_handling, parsed_args.no_comprehensive_check, parsed_args.redirect_dir, parsed_args.duplicate_keyword
    )

    # Log script end with MariaDB TIMESTAMP format
    end_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logger.info(f"{10 * '_'}** Ended: {end_time}")
    
    # Ensure all log messages are written
    logging.shutdown()


if __name__ == "__main__":
    main()

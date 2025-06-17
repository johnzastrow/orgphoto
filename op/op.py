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

6. If neither -m nor -c is specified, the script will prompt to run in dryrun mode simulating moving files.

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

# Third-party library imports for metadata extraction
from hachoir.parser import createParser
from hachoir.metadata import extractMetadata
from hachoir.core import config

# Suppress hachoir warnings to keep console output clean
config.quiet = True

# Script version information
myversion = "v. 1.3 Cheesy Dibbles 2025-06-17"


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
    
    This function traverses all directories under source_dir, identifying files
    with matching extensions and processing them according to the specified action.
    It keeps track of statistics and reports progress.
    """
    # Initialize counters for statistics
    total_files = 0
    processed_files = 0
    
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
            
            # Only process if destination file doesn't already exist
            if not dest_file_path.exists():
                try:
                    # Perform the actual move or copy operation
                    if not dryrun:
                        if action == "move":
                            shutil.move(str(fullpath), str(destf))
                        else:
                            shutil.copy2(str(fullpath), str(destf))
                            
                    # Format timestamp in MariaDB format (YYYY-MM-DD HH:MM:SS)
                    timestamp = cd.strftime("%Y-%m-%d %H:%M:%S")
                    
                    # Log the operation
                    logger.info(
                        f"  {filename}  {comment:>{space}}  {timestamp} {flagM:>3} {destf}"
                        + (" [DRY RUN]" if dryrun else "")
                    )
                except Exception as e:
                    logger.error(f"Failed to {flagM} {fullpath} to {destf}: {e}")
                    return 0
            else:
                # Log if file already exists in destination
                logger.info("  " + filename + " already exists in " + str(destf))
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
        source_dir, destination_dir, ext_list, action, parsed_args.exifOnly, logger, dryrun
    )

    # Log script end with MariaDB TIMESTAMP format
    end_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logger.info(f"{10 * '_'}** Ended: {end_time}")
    
    # Ensure all log messages are written
    logging.shutdown()


if __name__ == "__main__":
    main()

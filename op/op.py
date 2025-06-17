#!/usr/bin/env python

import datetime
import logging
import sys
import shutil
from pathlib import Path

from docopt import docopt
from hachoir.parser import createParser
from hachoir.metadata import extractMetadata
from hachoir.core import config

# Usage string for docopt, describes how to use the script and its options
usage = """Usage:
  photocopy.py [options] <source_dir> <destination_dir>

Options:
  -h --help                Show this help and exit.
  -j --extense=str         Extension list - comma separated [default: jpeg,jpg]. Supports all extensions of hachoir
  -m --move=str            move files (--move=yes) or copy (--move=no) [default: no, copy instead]
  -v --verbose             Talk more.
  -x --exifOnly=str        skip file processing if no EXIF (--exifOnly =yes)
                           or process files with no EXIF (--exifOnly =no)
                           or Only process files with no EXIF (--exifOnly =fs) [default: yes]
  -d --dryrun              Dry run mode: simulate actions, do not move/copy files.

Examples:
    1. Simple. Copy jpg or JPG files from source (Z:\photosync) to target into folders
       named YYYY_MM_DD using the EXIF Creation Date in the JPG files. Ignore files without
       EXIF date, but log everything.
        # python photocopy.py -j jpg Z:\photosync target/

    2. More complex. Move (-m yes) files by extensions shown from source (Z:\photosync) to target into folders
        named YYYY_MM_DD using the EXIF Creation Date in the files. File without EXIF date will use the file
        system creation date to name target folders. Log everything.
        # python photocopy.py -m yes -x no -j gif,png,jpg,mov,mp4 Z:\photosync target/
"""

config.quiet = True  # Suppress hachoir warnings

myversion = "v. 1.2 Farfengruven"


def set_up_logging(destination_dir: Path, verbose: bool):
    """
    Set up logging to a file in the destination directory.
    Logging level is set based on the --verbose flag.
    """
    logger = logging.getLogger(__name__)
    level = logging.DEBUG if verbose else logging.INFO
    logfile = destination_dir / "events.log"

    try:
        logfile.parent.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"Failed to create log directory: {e}")
        sys.exit(1)
    try:
        if not logfile.exists():
            logfile.touch()
    except Exception as e:
        print(f"Failed to create log file: {e}")
        sys.exit(1)
    logger.setLevel(level)
    ch = logging.FileHandler(logfile, encoding="utf-8")
    ch.setLevel(level)
    formatter = logging.Formatter("%(message)s")
    ch.setFormatter(formatter)
    if not logger.handlers:
        logger.addHandler(ch)
    return logger


def get_created_date(filename: Path, logger):
    """
    Attempt to extract the creation date from the file's metadata (EXIF).
    Returns a datetime object if successful, otherwise None.
    """
    created_date = None
    try:
        parser = createParser(str(filename))
    except Exception as e:
        logger.debug(f"Failed to create parser for {filename}: {e}")
        return created_date
    if not parser:
        logger.debug(f"Unable to parse file for created date: {filename}")
        return created_date

    try:
        with parser:
            try:
                metadata = extractMetadata(parser)
            except Exception as err:
                logger.debug(f"Metadata extraction error for {filename}: {err}")
                metadata = None
        if not metadata:
            logger.debug(f"Unable to extract metadata for {filename}")
        else:
            cd = metadata.getValues("creation_date")
            if len(cd) > 0:
                created_date = cd[0]
    except Exception as e:
        logger.debug(f"Error during metadata extraction for {filename}: {e}")
    return created_date


def validate_args(source_dir: Path, destination_dir: Path, logger):
    """
    Validate that source and destination directories are not the same,
    and that the source exists before proceeding.
    """
    if not source_dir.exists() or not source_dir.is_dir():
        logger.error(f"Source directory does not exist: {source_dir}")
        sys.exit(1)
    if source_dir.resolve() == destination_dir.resolve():
        logger.error("Source and destination directories must not be the same.")
        sys.exit(1)


def normalize_extensions(ext_string: str):
    """
    Normalize extensions to lowercase, strip whitespace, and ensure they start with a dot.
    """
    return [
        "." + ext.strip().lower().lstrip(".")
        for ext in ext_string.split(",")
        if ext.strip()
    ]


def recursive_walk(
    source_dir: Path,
    destination_dir: Path,
    ext_list,
    act_move,
    exif_only,
    logger,
    dryrun=False,
):
    """
    Walk through the folder and process files with matching extensions.
    Progress reporting is included.
    """
    total_files = 0
    processed_files = 0
    for folderName, _, filenames in os.walk(source_dir):
        logger.info(f"Source Folder: {folderName}")
        for filename in filenames:
            file_extension = Path(filename).suffix.lower()
            if file_extension in ext_list:
                total_files += 1
                processed_files += moveFile(
                    Path(folderName),
                    filename,
                    destination_dir,
                    act_move,
                    exif_only,
                    logger,
                    dryrun,
                )
                if processed_files % 100 == 0:
                    logger.info(f"Processed {processed_files} files so far...")
    logger.info(f"Total files matched: {total_files}, processed: {processed_files}")


def moveFile(
    folder: Path,
    filename: str,
    destination_dir: Path,
    act_move: str,
    exif_only: str,
    logger,
    dryrun=False,
):
    """
    Move or copy a file to the destination directory, organizing by date.
    Uses EXIF creation date if available, otherwise uses file system date.
    Handles skipping or processing files based on exifOnly option.
    Adds robust error handling for file and directory operations.
    Returns 1 if file was processed, 0 otherwise.
    """
    fullpath = folder / filename
    try:
        cd = get_created_date(fullpath, logger)
    except Exception as e:
        logger.error(f"Error extracting date from {fullpath}: {e}")
        return 0
    comment = " " * 9
    if not cd:
        try:
            cd = datetime.datetime.fromtimestamp(fullpath.stat().st_mtime)
            comment = " no EXIF "
        except Exception as e:
            logger.error(f"Failed to get file system date for {fullpath}: {e}")
            return 0
    try:
        created_date = cd.strftime("%Y_%m_%d")
    except Exception as e:
        logger.error(f"Failed to format date for {fullpath}: {e}")
        return 0
    space = 40 - len(filename)
    if space <= 0:
        space = 4
    destf = destination_dir / created_date

    # exifOnly logic
    if not comment.isspace() and exif_only == "yes":
        logger.info(f"  {filename}  {comment:>{space}}    skipped")
        return 0
    else:
        flagM = "moved" if act_move == "yes" else "copied"
        if (
            exif_only == "no"
            or (exif_only == "yes" and comment.isspace())
            or (exif_only == "fs" and not comment.isspace())
        ):
            try:
                if not destf.exists():
                    if not dryrun:
                        destf.mkdir(parents=True, exist_ok=True)
                    logger.info(f"created new destination subdir: {destf}")
            except Exception as e:
                logger.error(f"Failed to create destination subdir {destf}: {e}")
                return 0
            dest_file_path = destf / filename
            if not dest_file_path.exists():
                try:
                    if not dryrun:
                        if act_move == "yes":
                            shutil.move(str(fullpath), str(destf))
                        else:
                            shutil.copy2(str(fullpath), str(destf))
                    logger.info(
                        f"  {filename}  {comment:>{space}}  {str(cd)} {flagM:>3} {destf}"
                        + (" [DRY RUN]" if dryrun else "")
                    )
                except Exception as e:
                    logger.error(f"Failed to {flagM} {fullpath} to {destf}: {e}")
                    return 0
            else:
                logger.info("  " + filename + " already exists in " + str(destf))
            return 1
        elif exif_only == "fs" and comment.isspace():
            logger.info(f"  {filename}  {comment:>{space}}    skipped")
            return 0
    return 0


def main(args=None):
    """
    Main entry point for the script.
    Parses arguments, sets up logging, validates arguments, and starts processing files.
    """
    if args is None:
        args = sys.argv[1:]
    arguments = docopt(usage)

    # Normalize and validate extensions
    ext_list = normalize_extensions(arguments["--extense"])

    act_move = arguments["--move"].lower()
    exif_only = arguments["--exifOnly"].lower()
    dryrun = arguments["--dryrun"]

    source_dir = Path(arguments["<source_dir>"]).expanduser().resolve()
    destination_dir = Path(arguments["<destination_dir>"]).expanduser().resolve()

    logger = set_up_logging(destination_dir, arguments["--verbose"])

    logger.info(
        10 * "-"
        + myversion
        + "++ Started: "
        + datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S")
    )
    logger.debug("options: " + str(arguments))

    validate_args(source_dir, destination_dir, logger)

    try:
        if not destination_dir.exists():
            destination_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"created: {destination_dir}")
    except Exception as e:
        logger.error(f"Failed to create destination directory {destination_dir}: {e}")
        sys.exit(1)

    recursive_walk(
        source_dir, destination_dir, ext_list, act_move, exif_only, logger, dryrun
    )

    logger.info(
        10 * "_" + "** Ended: " + datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S")
    )
    logging.shutdown()


if __name__ == "__main__":
    main()

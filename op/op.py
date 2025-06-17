#!/usr/bin/env python
import datetime
import logging
import os
import sys
import shutil

from docopt import docopt  # For parsing command-line arguments

from hachoir.parser import createParser  # For parsing file metadata
from hachoir.metadata import extractMetadata
from hachoir.core import config

# Usage string for docopt, describes how to use the script and its options
usage = """Usage:
  photocopy.py [options] <source_dir> <destination_dir>

Options:
  -h --help                Show this help and exit.
  -j --extense=str         Extention list - comma separated [default: jpeg,jpg]. Supports all extensions of hachoir
  -m --move=str            move files (--move=yes) or copy (--move=no) [default: no, copy instead]
  -v --verbose             Talk more.
  -x --exifOnly=str        skip file processing if no EXIF (--exifOnly =yes)
                           or process files with no EXIF (--exifOnly =no)
                           or Only process files with no EXIF (--exifOnly =fs) [default: yes]

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

logger = logging.getLogger(__name__)  # Set up logger for this script
myversion = "v. 1.2 Farfengruven"
destination_dir = ""  # Will hold the destination directory path
extList = []  # List of file extensions to process
actMove = "no"  # Whether to move or copy files
exifOnly = ""  # How to handle files without EXIF data
running_file = str(__file__)  # The path of this script file
print(str(running_file) + "\n" + "is the file")  # Print script file path for debugging


def set_up_logging(arguments):
    """
    Set up logging to a file in the destination directory.
    Logging level is set based on the --verbose flag.
    """
    if arguments["--verbose"]:
        level = logging.DEBUG  # More detailed logs if verbose
    else:
        level = logging.INFO  # Standard logs otherwise
    logfile = os.path.join(destination_dir, "events.log")  # Log file path

    # Ensure the log directory exists
    if not os.path.exists(os.path.dirname(logfile)):
        os.makedirs(os.path.dirname(logfile))
    # Ensure the log file exists
    if not os.path.exists(logfile):
        open(logfile, "a").close()
    logger.setLevel(level)
    ch = logging.FileHandler(logfile)  # Log to file
    ch.setLevel(level)
    formatter = logging.Formatter("%(message)s")  # Simple log format
    ch.setFormatter(formatter)
    logger.addHandler(ch)


def get_created_date(filename):
    """
    Attempt to extract the creation date from the file's metadata (EXIF).
    Returns a datetime object if successful, otherwise None.
    """
    created_date = None
    parser = createParser(filename)  # Create a parser for the file
    if not parser:
        logger.debug("Unable to parse file for created date")
        return created_date

    with parser:
        try:
            metadata = extractMetadata(parser)  # Extract metadata
        except Exception as err:
            logger.debug("Metadata extraction error: %s" % err)
            metadata = None
    if not metadata:
        logger.debug("Unable to extract metadata")
    else:
        cd = metadata.getValues("creation_date")  # Get creation date values
        if len(cd) > 0:
            created_date = cd[0]  # Use the first creation date found
    return created_date


def main(args=None):
    """
    Main entry point for the script.
    Parses arguments, sets up logging, and starts processing files.
    """
    global destination_dir, extList, actMove, exifOnly
    if args is None:
        args = sys.argv[1:]
    arguments = docopt(usage)  # Parse command-line arguments

    # Parse file extensions from arguments
    extensions = arguments["--extense"]
    extList = extensions.split(",")
    extList[:] = ["." + x for x in extList]  # Add '.' to each extension

    # Parse other options
    actMove = arguments["--move"]
    exifOnly = arguments["--exifOnly"]

    source_dir = arguments["<source_dir>"]
    destination_dir = arguments["<destination_dir>"]
    set_up_logging(arguments)  # Set up logging

    # Log job start
    logger.info(
        10 * "-"
        + myversion
        + "++ Started: "
        + datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S")
    )
    logger.debug("options: " + str(arguments))
    if not os.path.isdir(destination_dir):
        os.makedirs(destination_dir)
        logger.info("created: " + destination_dir)
    if os.path.isdir(source_dir):
        # Start recursive processing of source directory
        recursive_walk(source_dir)
    else:
        logger.info("source dir not exists: " + source_dir)
    # Log job end
    logger.info(
        10 * "_" + "** Ended: " + datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S")
    )
    logging.shutdown()


def recursive_walk(folder):
    """
    Recursively walk through the folder and process files with matching extensions.
    """
    for folderName, subfolders, filenames in os.walk(folder):
        logger.info("Source Folder: " + folderName)
        for filename in filenames:
            file_details = os.path.splitext(filename)
            file_extension = file_details[1].lower()
            # Only process files with the specified extensions
            if file_extension in extList:
                moveFile(folderName, filename)
        if subfolders:  # If there are subfolders, process them recursively
            for subfolder in subfolders:
                recursive_walk(subfolder)


def moveFile(folder, filename):
    """
    Move or copy a file to the destination directory, organizing by date.
    Uses EXIF creation date if available, otherwise uses file system date.
    Handles skipping or processing files based on exifOnly option.
    """
    fullpath = os.path.join(folder, filename)
    cd = get_created_date(fullpath)  # Try to get EXIF creation date
    comment = 9 * " "  # Default: assume EXIF present
    if not cd:
        # If no EXIF, use file system modification time
        cd = datetime.datetime.fromtimestamp(os.path.getmtime(fullpath))
        comment = " no EXIF "
    created_date = cd.strftime("%Y_%m_%d")  # Format date for folder name
    space = 40 - len(filename)
    if space <= 0:
        space = 4
    destf = os.path.join(destination_dir, created_date)  # Destination subfolder

    # If file has no EXIF and exifOnly is 'yes', skip processing
    if not comment.isspace() and exifOnly == "yes":
        logger.info(f"  {filename}  {comment:>{space}}    skipped")
    else:
        flagM = "moved" if actMove == "yes" else "copied"
        # Decide whether to process file based on exifOnly option
        if (
            exifOnly == "no"
            or (exifOnly == "yes" and comment.isspace())
            or (exifOnly == "fs" and not comment.isspace())
        ):
            # Create destination subfolder if it doesn't exist
            if not os.path.isdir(destf):
                os.makedirs(destf)
                logger.info(f"created new destination subdir: {destf}")
            # Only move/copy if file doesn't already exist at destination
            if not os.path.exists(os.path.join(destf, filename)):
                if actMove == "yes":
                    shutil.move(fullpath, destf)
                else:
                    shutil.copy2(fullpath, destf)
                logger.info(
                    f"  {filename}  {comment:>{space}}  {str(cd)} {flagM:>3} {destf}"
                )
            else:
                logger.info("  " + filename + " already exists in " + destf)
        elif exifOnly == "fs" and comment.isspace():
            logger.info(f"  {filename}  {comment:>{space}}    skipped")


if __name__ == "__main__":
    main()

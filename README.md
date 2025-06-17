orgphoto (op)
=========

![logo](doc/logo.png)

SUMMARY:
--------

This script scans a source directory (recursively) for image and video files with specified extensions,
extracts their creation date (preferably from EXIF metadata, or falls back to the file system date),
and copies or moves them into subfolders in a destination directory, organized by date (YYYY_MM_DD).

A common use case might be to move them from a mobile device into archive folders, or to reorganize archives. 

It will prefer to use the EXIF date in the file. If not present it will skip file unless the flag `-x no` (do not skip files without EXIF date) is passed in which case it will use file system creation date. All operations are logged into a text file saved into the target directory.

Note this is a major rewrite of the upstream project skorokithakis/photocopy and this code is not downstreamed from it any longer.



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
- Command-line interface with flexible options using docopt.
- Uses pathlib for modern, robust path handling.

USAGE:
---------
From the packaged .exe. But the script is the same code.

```bash
C:\Users\user\Github\orgphoto\output>op.exe -h
usage: op.exe [-h] [-m | -c] [-j EXT] [-v] [-x {yes,no,fs}] [-d] [--examples] SOURCE_DIR DEST_DIR

Organize and copy/move photos and videos by date

positional arguments:
  SOURCE_DIR            Source directory containing images/videos to organize
  DEST_DIR              Destination directory where organized files will be placed

options:
  -h, --help            show this help message and exit
  -m, --move            Move files (cannot be used with --copy)
  -c, --copy            Copy files (cannot be used with --move)
  -j, --extensions EXT  Extension list - comma separated [default: jpeg,jpg]. Supports all extensions of hachoir
  -v, --verbose         Talk more
  -x, --exifOnly {yes,no,fs}
                        'yes': skip files with no EXIF, 'no': process all files (fallback to filesystem date), 'fs': only process
                        files with no EXIF [default: yes]
  -d, --dryrun          Dry run mode: simulate actions, do not move/copy files
  --examples            Show usage examples and exit

If neither --move nor --copy is specified, the script will prompt to run in dryrun mode simulating moving files.
```

USAGE EXAMPLES:
---------------

1. Move JPG files from source to destination, organizing by EXIF date, skipping files without EXIF:
   
   `python op.py -m -j jpg Z:\\photosync target/`

2. Copy various file types, using file system date if EXIF is missing:

   `python op.py -c -x no -j gif,png,jpg,mov,mp4 Z:\\photosync target/`

3. Dry run: Simulate moving files without making changes:

  ` python op.py -m -d -j jpg Z:\\photosync target/`

4. Only process files that do not have EXIF data (using file system date):

   `python op.py -c -x fs -j jpg Z:\\photosync target/`

5. Move PNG and JPEG files, verbose logging enabled:

   `python op.py -m -v -j png,jpeg Z:\\photosync target/`

*If neither -m nor -c is specified, the script will prompt to run in dryrun mode simulating moving files.

See `--help` for all options.

INSTALLATION
------------
**<u>pip</u>** 
Just run:

    1. Clone the repo, or just download `op.py`
    2. pip install hachoir
    3. Then execute the script using python as in # python op.py

**<u>uv</u>** - Thank you uv! ![uv installation here](https://docs.astral.sh/uv/getting-started/installation/)

    1. Clone the repo (you'll also want the supporting files)
    2. Make sure uv is installed. It will handle dependencies 
    3. Then execute the script using python as in # uv run op.py

Usage - Windows .exe
-----
This project also contains a Windows executable made by simply compiling the script with this project https://pypi.org/project/auto-py-to-exe/ "A .py to .exe converter using a simple graphical interface and PyInstaller in Python." It works EXACTLY like the script without the hassle of setting up Python where you want to run it. There is a copy of the .exe of some vintage here in this repo.

This is the command I used to build the .exe, though I cheated by using the UI

``` pyinstaller --noconfirm --onefile --console --icon "C:\Github\orgphoto\doc\favicon.ico"  "C:\Github\orgphoto\op\op.py" ```


Here's an example of running the built .exe in Windows, where op.exe is asked to Move all files even if No eXif data is found (ahem heic files), move files of extensions (case-insensitive) jpg,png,jpeg,heic,mov, from `src1` (and its sub directories) to `target` into folders by date.

```op.exe -m -x no -j jpg,png,jpeg,heic,mov C:\\Users\\user\\Github\\orgphoto\\testing\\src1 C:\\Users\\user\\Github\\orgphoto\\testing\\target```

Examples of log entries
------------------------

#### Plain info logging on top, verbose debug logging on the bottom

![logging](../main/doc/log2.png)


 File Formats
 -------------

This version of orgphoto (op) uses the [https://pypi.org/project/hachoir/](hachoir) software to extract EXIF metadata. Hachoir supports the following 
file formats as of version 3.3.0 in November 2024.

#### Total: 33 file formats, from https://hachoir.readthedocs.io/en/latest/metadata.html#supported-file-formats

#### Archive
* bzip2: bzip2 archive
* cab: Microsoft Cabinet archive
* gzip: gzip archive
* mar: Microsoft Archive
* tar: TAR archive
* zip: ZIP archive

#### Audio
* aiff: Audio Interchange File Format (AIFF)
* mpeg_audio: MPEG audio version 1, 2, 2.5
* real_audio: Real audio (.ra)
* sun_next_snd: Sun/NeXT audio

#### Container
* matroska: Matroska multimedia container
* ogg: Ogg multimedia container
* real_media: !RealMedia (rm) Container File
* riff: Microsoft RIFF container

#### Image
* bmp: Microsoft bitmap (BMP) picture
* gif: GIF picture
* ico: Microsoft Windows icon or cursor
* jpeg: JPEG picture
* pcx: PC Paintbrush (PCX) picture
* png: Portable Network Graphics (PNG) picture
* psd: Photoshop (PSD) picture
* targa: Truevision Targa Graphic (TGA)
* tiff: TIFF picture
* wmf: Microsoft Windows Metafile (WMF)
* xcf: Gimp (XCF) picture

#### Misc
* ole2: Microsoft Office document
* pcf: X11 Portable Compiled Font (pcf)
* torrent: Torrent metainfo file
* ttf: !TrueType font

#### Program
* exe: Microsoft Windows Portable Executable

#### Video
* asf: Advanced Streaming Format (ASF), used for WMV (video) and WMA (audio)
* flv: Macromedia Flash video
* mov: Apple !QuickTime movie

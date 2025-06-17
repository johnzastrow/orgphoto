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

USAGE EXAMPLES:
---------------

1. Move JPG files from source to destination, organizing by EXIF date, skipping files without EXIF:
   python photocopy.py -m -j jpg Z:\\photosync target/

2. Copy various file types, using file system date if EXIF is missing:
   python photocopy.py -c -x no -j gif,png,jpg,mov,mp4 Z:\\photosync target/

3. Dry run: Simulate moving files without making changes:
   python photocopy.py -m -d -j jpg Z:\\photosync target/

4. Only process files that do not have EXIF data (using file system date):
   python photocopy.py -c -x fs -j jpg Z:\\photosync target/

5. Move PNG and JPEG files, verbose logging enabled:
   python photocopy.py -m -v -j png,jpeg Z:\\photosync target/

6. If neither -m nor -c is specified, the script will prompt to run in dryrun mode simulating moving files.

See --help for all options.

INSTALLATION
------------
**<u>pip</u>** 
Just run:

    1. Clone down the repo, or just download `op.py`
    2. pip install docopt
    3. pip install hachoir
    4. Then execute the script using python as in # python op.py

**<u>uv</u>** - Thank you uv!

    1. Clone down the repo (you'll also want the supporting files)
    2. make sure uv is installed. It will handle dependencies 
    3. Then execute the script using python as in # uv run op.py

Usage - Windows .exe
-----
This project also contains a Windows executable made by simply compiling the script with this project https://pypi.org/project/auto-py-to-exe/ "A .py to .exe converter using a simple graphical interface and PyInstaller in Python." It works EXACTLY like the script without the hassle of setting up Python where you want to run it. There is a copy of the .exe of some vintage here in this repo.

This is the command I used to build the .exe, though I cheated by using the UI

``` pyinstaller --noconfirm --onefile --console --icon "C:\Github\orgphoto\doc\favicon.ico"  "C:\Github\orgphoto\op\op.py" ```



Examples of log entries
------------------------

#### Plain info logging

![Plain log](../main/doc/log1b.png)


#### Debug, verbose logging

![Debug log](../main/doc/log1.png)



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

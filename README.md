orgphoto (op)
=========

![logo](doc/logo.png)

## Table of Contents

- [Summary](#summary)
- [What's New in v1.4.0](#-whats-new-in-v140)
- [Features](#features)
  - [Core Functionality](#core-functionality)
  - [Advanced Duplicate Detection](#advanced-duplicate-detection)
- [Usage](#usage)
- [Usage Examples](#usage-examples)
  - [Basic Operations](#basic-operations)
  - [Comprehensive Duplicate Detection Examples](#comprehensive-duplicate-detection-examples)
  - [Interactive Duplicate Handling](#interactive-duplicate-handling)
  - [Renaming Duplicate Handling](#renaming-duplicate-handling)
  - [Redirect Duplicate Handling](#redirect-duplicate-handling)
  - [Overwrite Handling](#overwrite-handling)
  - [Performance Optimization Examples](#performance-optimization-examples)
  - [Advanced Combinations](#advanced-combinations)
  - [Real-World Scenarios](#real-world-scenarios)
  - [Using UV (Recommended)](#using-uv-recommended)
- [Duplicate Handling Modes](#duplicate-handling-modes)
- [Redirect Duplicate Handling](#redirect-duplicate-handling-1)
- [Comprehensive Duplicate Detection](#comprehensive-duplicate-detection)
- [Performance Considerations](#performance-considerations)
- [Installation](#installation)
- [Building Windows .exe](#building-windows-exe)
- [File Formats](#file-formats)

## Summary

This script scans a source directory (recursively) for files (all types by default, or specified extensions),
extracts their creation date (preferably from EXIF metadata, or falls back to the file system date),
and copies or moves them into subfolders in a destination directory, organized by date (YYYY_MM_DD).

**Key features**: Comprehensive SHA-256 duplicate detection, intelligent conflict resolution, and flexible duplicate handling modes.

## ✨ What's New in v2.0.1

- **📊 Enhanced Log Headers**: Professional session headers in log files with clear version information
- **🎯 Improved Readability**: Structured log formatting with visual separators between sessions
- **📝 Better Tracking**: Each log session now clearly shows program version and timestamps

### Major Update: v2.0.0 - Intelligent Master File Selection

- **🧠 Smart Master Selection**: Automatically determines the best "master" file among duplicates based on:
  - ✅ No duplicate keywords ("copy", "duplicate", "(1)", etc.) - highest priority
  - ✅ Shortest filename - simpler names are typically originals
  - ✅ Oldest creation/modification date - earlier files are likely originals
- **🔄 Automatic File Demotion**: When incoming file is better master, existing files are automatically demoted
- **🛡️ Master Protection**: Master files are protected from being overwritten by inferior duplicates
- **🔍 Comprehensive Logging**: Detailed logs of master selection criteria, conflict reasons, and demotion actions
- **⚡ Intelligent Conflict Resolution**: Handles complex scenarios with multiple duplicates

### Previous Updates (v1.5.x)

- **📌 Version Visibility**: Version displays in help output and when run without arguments
- **🐛 Bug Fixes**: Fixed version output duplication issues
- **🎯 Enhanced User Experience**: Improved version tracking throughout the interface

### Previous Updates (v1.4.x)

- **🎯 All File Types by Default**: No need to specify extensions - processes all supported formats automatically
- **📖 Enhanced Help System**: Comprehensive help text with detailed explanations and real-world examples
- **🔧 Better User Experience**: Streamlined workflow for both beginners and power users

A common use case might be to move them from a mobile device into archive folders, or to reorganize archives. 

It will prefer to use the EXIF date in the file. If not present it will skip file unless the flag `-x no` (do not skip files without EXIF date) is passed in which case it will use file system creation date. By default, it performs comprehensive duplicate detection using SHA-256 hashing to prevent storing identical files. All operations are logged into a text file saved into the target directory.

Note this is a major rewrite of the upstream project skorokithakis/photocopy and this code is not downstreamed from it any longer.



## Features

### Core Functionality
- **🌟 Processes ALL file types by default** - no extension specification needed (supports 33+ formats via hachoir)
- **📁 Smart file filtering** - optionally specify extensions when targeted processing is needed
- Recursively processes all subfolders in the source directory.
- Uses EXIF metadata for creation date if available; otherwise, uses the file system's modification date.
- Can skip, only process, or fallback to file system date for files without EXIF metadata (configurable).
- Optionally moves files instead of copying.
- **🔍 Dry run mode** with detailed preview of all operations before execution.
- Progress reporting and comprehensive logging to events.log in destination directory.
- **📖 Comprehensive help system** with detailed explanations and real-world examples.
- Robust error handling for file operations, directory creation, and metadata extraction.
- **🎛️ User-friendly command-line interface** with extensive help and examples.
- Uses pathlib for modern, robust path handling.

### Advanced Duplicate Detection
- **🧠 Intelligent Master File Selection** (NEW in v2.0.0):
  - **Automatic master identification**: Determines best file to keep based on multiple criteria
  - **Priority ranking**: No duplicate keywords > Shortest filename > Oldest date
  - **Keyword detection**: Recognizes "copy", "duplicate", "(1)", "_copy", and international variations
  - **Smart demotion**: Automatically moves inferior files when better master arrives
  - **Master protection**: Prevents accidental overwriting of master files
  - **Comprehensive logging**: Details master selection decisions and criteria
- **Comprehensive SHA256 checking**: By default, checks each incoming file against ALL existing files in target directory (not just filename conflicts)
- **Content-based detection**: Uses SHA-256 hashing to detect truly identical files regardless of filename or location
- **Hash caching**: Builds and maintains an in-memory hash database of target files for efficient duplicate detection
- **Multiple duplicate handling modes**:
  - `skip` (default) - Skip if filename exists or identical content found anywhere
  - `overwrite` - Master-aware: protects master files, renames inferior duplicates
  - `rename` - Add numeric suffix to duplicates (e.g., `photo_001.jpg`)
  - `content` - Compare file hashes; skip identical content, rename different content
  - `interactive` - Prompt user for each duplicate with full context
  - `redirect` - Move duplicates to separate directory with intelligent renaming
- **Intelligent duplicate redirection**: Configurable directory and keyword for duplicate organization
- **Performance control**: Use `-N` flag to disable comprehensive checking for large target directories
- **Smart conflict resolution**: Automatically generates unique filenames when needed

## Usage
From the packaged .exe. But the script is the same code.

```bash
C:\Users\user\Github\orgphoto\output>op.exe -h
usage: op.py [-h] [-m | -c] [-j EXT] [-v] [-x {yes,no,fs}] [-d]
              [-D DUPLICATE_HANDLING] [-N] [-R DIR] [-K WORD] [--examples]
              [--version]
              SOURCE_DIR DEST_DIR

Organize files by date with comprehensive duplicate detection

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
  -D, --duplicate-handling DUPLICATE_HANDLING
                        How to handle duplicates: skip, overwrite, rename, content, interactive, redirect [default: skip]
  -N, --no-comprehensive-check
                        Disable comprehensive SHA256 checking for better performance
  -R, --redirect-dir DIR
                        Directory for redirected duplicates [default: Duplicates]
  -K, --duplicate-keyword WORD
                        Keyword for duplicate filenames [default: duplicate]
  --examples            Show usage examples and exit
  --version             Show program version and exit

If neither --move nor --copy is specified, the script will prompt to run in dryrun mode simulating moving files.

Note: Version information displays when running without arguments. Use --version to see the version number.
```

## Usage Examples

### Basic Operations

1. **Process ALL file types (new default behavior - no extension filtering required)**:
   ```bash
   python op.py -c Z:\photosync target/
   ```

2. **Move JPG files only (specify extensions when filtering needed)**:
   ```bash
   python op.py -m -j jpg Z:\photosync target/
   ```

3. **Copy various file types, using file system date if EXIF is missing**:
   ```bash
   python op.py -c -x no -j gif,png,jpg,mov,mp4 Z:\photosync target/
   ```

4. **Dry run: Simulate moving files without making changes**:
   ```bash
   python op.py -m -d -j jpg Z:\photosync target/
   ```

5. **Process only files without EXIF data (using file system date)**:
   ```bash
   python op.py -c -x fs -j jpg Z:\photosync target/
   ```

6. **Move PNG and JPEG files with verbose logging**:
   ```bash
   python op.py -m -v -j png,jpeg Z:\photosync target/
   ```

### Comprehensive Duplicate Detection Examples

7. **Content-based duplicate detection (skip identical, rename different)**:
   ```bash
   python op.py -c -D content -j jpg Z:\photosync target/
   ```
   *This compares SHA-256 hashes to detect truly identical files regardless of filename*

8. **Content-based with custom keyword for different files**:
   ```bash
   python op.py -c -D content -K version -j jpg Z:\photosync target/
   ```
   *Different content with same filename becomes: photo_version.jpg*

### Interactive Duplicate Handling

9. **Interactive duplicate handling (ask user for each conflict)**:
   ```bash
   python op.py -m -D interactive -j jpg Z:\photosync target/
   ```
   *Prompts user with options: Skip, Overwrite, Rename, or Redirect*

10. **Interactive mode with verbose context**:
    ```bash
    python op.py -m -D interactive -v -j jpg,png,heic Z:\photosync target/
    ```
    *Provides detailed information about each duplicate for informed decisions*

### Renaming Duplicate Handling

11. **Always rename duplicates (never skip or overwrite)**:
    ```bash
    python op.py -c -D rename -j jpg Z:\photosync target/
    ```
    *Generates: photo.jpg → photo_duplicate.jpg → photo_duplicate_001.jpg*

12. **Rename with custom keyword**:
    ```bash
    python op.py -c -D rename -K copy -j jpg Z:\photosync target/
    ```
    *Generates: photo.jpg → photo_copy.jpg → photo_copy_001.jpg*

### Redirect Duplicate Handling

13. **Redirect duplicates to separate directory**:
    ```bash
    python op.py -c -D redirect -j jpg Z:\photosync target/
    ```
    *Creates: target/Duplicates/YYYY_MM_DD/filename_duplicate.jpg*

14. **Redirect with custom directory and keyword**:
    ```bash
    python op.py -c -D redirect -R MyDuplicates -K copy -j jpg Z:\photosync target/
    ```
    *Creates: target/MyDuplicates/YYYY_MM_DD/filename_copy.jpg*

15. **Redirect to absolute path**:
    ```bash
    python op.py -c -D redirect -R /backup/duplicates -j jpg Z:\photosync target/
    ```
    *Creates: /backup/duplicates/YYYY_MM_DD/filename_duplicate.jpg*

16. **Redirect with dry run to see what would happen**:
    ```bash
    python op.py -c -d -D redirect -R TestDupes -j jpg Z:\photosync target/
    ```
    *Shows redirect actions in log without making changes*

### Overwrite Handling

17. **Overwrite all duplicates (replace existing files)**:
    ```bash
    python op.py -m -D overwrite -j jpg Z:\photosync target/
    ```
    *Warning: This will replace existing files without backup*

18. **Overwrite with verbose logging for audit trail**:
    ```bash
    python op.py -c -v -D overwrite -j jpg,png Z:\photosync target/
    ```

### Performance Optimization Examples

19. **Disable comprehensive checking for large target directories**:
    ```bash
    python op.py -c -N -j jpg Z:\photosync target/
    ```
    *Skips SHA-256 hashing of existing files for faster processing*

20. **Fast mode: disable comprehensive checking + rename duplicates**:
    ```bash
    python op.py -c -N -D rename -j jpg Z:\photosync target/
    ```
    *Fastest processing - only checks filename conflicts*

21. **Performance mode with redirect**:
    ```bash
    python op.py -c -N -D redirect -R FastDupes -j jpg Z:\photosync target/
    ```

### Advanced Combinations

22. **Content-based detection with verbose logging**:
    ```bash
    python op.py -m -v -D content -j png,jpeg Z:\photosync target/
    ```

23. **Process files without EXIF, redirect duplicates**:
    ```bash
    python op.py -c -x fs -D redirect -R DuplicatesNoExif -j jpg Z:\photosync target/
    ```

24. **Multi-format processing with custom duplicate handling**:
    ```bash
    python op.py -c -x no -D content -K backup -j jpg,png,gif,heic,mov,mp4 Z:\photosync target/
    ```

25. **Maximum safety mode (comprehensive + interactive)**:
    ```bash
    python op.py -c -D interactive -v -j jpg,png,heic,mov Z:\photosync target/
    ```

### Real-World Scenarios

26. **Mobile device photo import with comprehensive deduplication**:
    ```bash
    python op.py -c -x no -D content -j jpg,png,heic,mov /sdcard/DCIM target/photos/
    ```

27. **Archive consolidation with duplicate redirection**:
    ```bash
    python op.py -c -D redirect -R Archive/Duplicates -j jpg,png,gif,tiff old_archive/ consolidated_archive/
    ```

28. **Large photo library processing (performance optimized)**:
    ```bash
    python op.py -c -N -D rename -K alt -j jpg,png,heic source/ target/
    ```

29. **Cautious migration with dry-run and interactive**:
    ```bash
    python op.py -d -D interactive -v -j jpg,png,heic,mov source/ target/
    ```

### Using UV (Recommended)

30. **UV with comprehensive duplicate detection**:
    ```bash
    uv run op.py -c -D content -j jpg source/ target/
    ```

31. **UV with redirect and custom settings**:
    ```bash
    uv run op.py -c -D redirect -R MyDupes -K copy -j jpg,heic source/ target/
    ```

*If neither `-m` nor `-c` is specified, the script will prompt to run in dryrun mode simulating moving files.*

**Short Flag Reference**:
- `-m` = move, `-c` = copy, `-d` = dry run, `-v` = verbose
- `-j` = extensions, `-x` = EXIF handling  
- `-D` = duplicate handling, `-N` = disable comprehensive check
- `-R` = redirect directory, `-K` = duplicate keyword

See `python op.py --help` or `python op.py --examples` for all options.

## DUPLICATE HANDLING MODES

orgphoto provides six different modes for handling duplicate files, each optimized for different use cases:

### 1. Skip Mode (`-D skip`) - **DEFAULT**
**Behavior**: Skip files if filename exists OR identical content found anywhere in target
- **Use case**: Safest option, avoids any duplicate content
- **Performance**: Medium (requires comprehensive hash checking)
- **Output**: Logs "skipped - duplicate detected"

```bash
python op.py -c -D skip -j jpg source/ target/
```

### 2. Content Mode (`-D content`)
**Behavior**: Skip if identical content exists, rename if same filename but different content
- **Content identical**: Skip processing (logged as "skipped - identical content")  
- **Filename conflict, different content**: Rename with suffix
- **Use case**: Preserve all unique content while avoiding true duplicates
- **Performance**: Medium (requires comprehensive hash checking)

```bash
python op.py -c -D content -j jpg source/ target/
# photo.jpg with same content → skipped
# photo.jpg with different content → photo_duplicate.jpg
```

### 3. Rename Mode (`-D rename`)
**Behavior**: Always rename duplicates, never skip or overwrite
- **Filename exists**: Add suffix `_duplicate` (or custom keyword)
- **Multiple conflicts**: Incremental numbering `_duplicate_001`, `_duplicate_002`
- **Use case**: Preserve all files, never lose anything
- **Performance**: Fast (can work without comprehensive checking)

```bash
python op.py -c -D rename -K backup -j jpg source/ target/
# photo.jpg → photo_backup.jpg → photo_backup_001.jpg
```

### 4. Overwrite Mode (`-D overwrite`)
**Behavior**: Replace existing files without confirmation
- **Filename exists**: Overwrite the existing file
- **Content duplicates**: Still overwrite (if comprehensive checking enabled)
- **Use case**: Always use the newest version of files
- **⚠️ Warning**: Data loss possible - existing files are replaced
- **Performance**: Fast

```bash
python op.py -c -D overwrite -j jpg source/ target/
```

### 5. Interactive Mode (`-D interactive`)
**Behavior**: Prompt user for each duplicate with full context
- **Shows**: Filename conflicts, content duplicates, file sizes, dates
- **Options**: Skip, Overwrite, Rename, Redirect
- **Use case**: Maximum control, good for one-time migrations
- **Performance**: Depends on user interaction speed

```bash
python op.py -c -D interactive -v -j jpg source/ target/
```
**Interactive prompt example**:
```
Duplicate detected for: photo.jpg
Target location: /target/2023_05_01/photo.jpg
Content duplicates found at:
  - /target/2023_05_01/photo.jpg
Filename conflict at: /target/2023_05_01/photo.jpg

Choose action:
  s) Skip this file
  o) Overwrite existing file(s)  
  r) Rename with suffix
  R) Redirect to duplicates directory
Your choice [s/o/r/R]:
```

### 6. Redirect Mode (`-D redirect`)
**Behavior**: Move duplicates to separate directory structure
- **Directory**: Creates `Duplicates/` (or custom with `-R`)
- **Structure**: Maintains date organization in redirect location
- **Naming**: Uses intelligent suffix generation
- **Use case**: Keep organized but separate duplicate files
- **Performance**: Fast, minimal overhead

```bash
python op.py -c -D redirect -R MyDupes -K copy -j jpg source/ target/
```

## REDIRECT DUPLICATE HANDLING

The redirect mode provides sophisticated duplicate management by moving duplicate files to a separate directory structure while maintaining organization and applying intelligent renaming.

### How Redirect Mode Works

When `--duplicate-handling redirect` (or `-D redirect`) is used:

1. **Directory Creation**: Creates a redirect directory (default: `Duplicates/` in target root)
2. **Duplicate Detection**: Uses comprehensive SHA-256 checking or filename-based detection  
3. **Intelligent Redirection**: Moves duplicates to redirect directory with smart renaming
4. **Organized Structure**: Maintains date-based organization within redirect directory

### Redirect Directory Structure

```
target/
├── 2023_01_01/           # Main organized files
│   ├── photo1.jpg
│   └── photo2.jpg
├── 2023_01_02/
│   └── photo3.jpg
└── Duplicates/           # Redirect directory
    ├── 2023_01_01/
    │   ├── photo1_duplicate.jpg      # Duplicate of main photo1.jpg
    │   └── photo1_duplicate_001.jpg  # Another copy of photo1.jpg
    └── 2023_01_02/
        └── photo3_copy.jpg           # Custom keyword example
```

### Configuration Options

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--redirect-dir` | `-R` | `Duplicates` | Directory name for redirected duplicates |
| `--duplicate-keyword` | `-K` | `duplicate` | Keyword inserted in duplicate filenames |

### Redirect Examples

**Basic redirect usage**:
```bash
python op.py -c -D redirect -j jpg source/ target/
# Creates: target/Duplicates/YYYY_MM_DD/filename_duplicate.jpg
```

**Custom redirect directory**:
```bash  
python op.py -c -D redirect -R Archive/Duplicates -j jpg source/ target/
# Creates: target/Archive/Duplicates/YYYY_MM_DD/filename_duplicate.jpg
```

**Custom duplicate keyword**:
```bash
python op.py -c -D redirect -K copy -j jpg source/ target/  
# Creates: target/Duplicates/YYYY_MM_DD/filename_copy.jpg
```

**Absolute path redirect**:
```bash
python op.py -c -D redirect -R /backup/duplicates -j jpg source/ target/
# Creates: /backup/duplicates/YYYY_MM_DD/filename_duplicate.jpg
```

### Filename Handling

Redirect mode uses intelligent filename generation:

1. **Base duplicate name**: `filename_duplicate.ext`
2. **If name exists**: `filename_duplicate_001.ext`  
3. **Multiple duplicates**: `filename_duplicate_002.ext`, `filename_duplicate_003.ext`, etc.
4. **Custom keyword**: `filename_copy.ext` (with `-K copy`)

### Integration Features

- **Works with comprehensive checking**: Detects true content duplicates via SHA-256
- **Works with filename conflicts**: Handles traditional duplicate scenarios
- **Interactive mode support**: User can choose redirect option when prompted
- **Dry-run compatible**: Shows what would be redirected without making changes
- **Logging integration**: Clear indication of redirect actions in log files

## INTELLIGENT MASTER FILE SELECTION (v2.0.0+)

### Overview

orgphoto automatically determines which file should be the "master" (definitive version) when duplicates are detected. This intelligent system ensures you keep the best quality original files while properly handling copies and duplicates.

### How Master Selection Works

When duplicates are detected, orgphoto evaluates ALL conflicting files (both incoming and existing) using a three-tier priority system:

#### Priority 1: No Duplicate Keywords (Highest Priority)
Files WITHOUT duplicate keywords are strongly preferred as masters:

**Detected keywords**:
- Word-based: `copy`, `duplicate`, `version`, `backup`, `alt`, `alternative`
- International: `copie` (French), `kopie` (German), `copia` (Spanish/Italian)
- Numbered patterns at end: `(1)`, `(2)`, `_copy_1`, `_duplicate_001`, ` 2`

**Examples**:
```
photo.jpg             → NO keywords (score: 0) ✓ BEST
photo_copy.jpg        → Has "copy" (score: 1)
vacation (1).jpg      → Has "(1)" (score: 1)
sunset_duplicate.jpg  → Has "duplicate" (score: 1)
```

#### Priority 2: Shortest Filename
Among files with same keyword status, shorter names are preferred (originals are typically shorter):

**Examples**:
```
photo.jpg                    → Length 9 ✓ BEST
photo_edited.jpg             → Length 16
photo_edited_final.jpg       → Length 22
```

#### Priority 3: Oldest Creation/Modification Date
If names are equally simple, older files are preferred (first created is typically original):

**Examples**:
```
photo.jpg (2023-01-15 10:30) → Older ✓ BEST
photo.jpg (2023-01-15 11:45) → Newer
photo.jpg (2023-01-16 09:00) → Newest
```

### Master Selection Actions

#### When Incoming File is Master
If the incoming file is determined to be the better master:

1. **Existing files are demoted** - Moved according to duplicate handling mode
2. **Incoming file takes primary position** - Placed in intended location
3. **Logged as promotion**: `[PROMOTED TO MASTER]`

**Log example**:
```
MASTER SELECTION: Chose photo.jpg as master (incoming)
  Criteria: has_dup_keywords=False, name_length=9, date=2023-01-15 10:30:00
  Non-masters (1): ['photo_copy.jpg']
MASTER PROMOTION: Incoming file photo.jpg is the better master
  DEMOTION: photo_copy.jpg will be moved to duplicate location
  DEMOTED: photo_copy.jpg -> Duplicates/photo_copy_duplicate.jpg
```

#### When Existing File is Master
If an existing file is the better master:

1. **Master file is protected** - Cannot be overwritten
2. **Incoming file follows duplicate mode** - Skipped, renamed, or redirected
3. **Logged as retention**: `[SKIPPED - not master]` or `[RENAMED - master protected]`

**Log example**:
```
MASTER SELECTION: Chose photo.jpg as master (existing)
  Criteria: has_dup_keywords=False, name_length=9, date=2023-01-15 10:30:00
  Non-masters (1): ['photo copy.jpg']
MASTER RETAINED: Existing file photo.jpg remains as master
  photo copy.jpg -> skipped - existing file is better master
```

### Master-Aware Duplicate Modes

All duplicate handling modes now respect master file selection:

| Mode | Master is Existing | Master is Incoming |
|------|-------------------|-------------------|
| `skip` | Skip incoming | Demote existing, place incoming |
| `overwrite` | **Protect master**, rename incoming | Demote existing, place incoming |
| `rename` | Rename incoming | Demote existing, place incoming |
| `content` | Check content, handle accordingly | Demote existing if different |
| `interactive` | Master indicated in prompt | Demote existing with user confirmation |
| `redirect` | Redirect incoming | Demote existing to redirect |

### Real-World Scenarios

#### Scenario 1: Consolidating Multiple Archives
```bash
# Situation: Three archives with duplicates
archive1/vacation.jpg
archive2/vacation_copy.jpg
archive3/vacation (1).jpg

# Result: Master selection picks vacation.jpg (no keywords)
# Others demoted: vacation_copy_duplicate.jpg, vacation (1)_duplicate.jpg
```

#### Scenario 2: Mobile Device Sync
```bash
# Phone creates: IMG_1234.jpg (original)
# Computer backup: IMG_1234 (1).jpg (duplicate)

# Result: Original IMG_1234.jpg recognized as master
# Backup version demoted automatically
```

#### Scenario 3: Mixed Quality Duplicates
```bash
# High quality original: photo.jpg (5MB, 2023-01-15)
# Lower quality copy: photo_compressed.jpg (1MB, 2023-01-16)

# Result: photo.jpg selected (shorter name, older)
# Compressed version handled as duplicate
```

### Configuration

Master selection is **automatic and always enabled**. No configuration needed, but behavior adapts to duplicate handling mode:

```bash
# Master selection with skip mode
python op.py -c -D skip -j jpg source/ target/

# Master selection with redirect (demoted files go to redirect dir)
python op.py -c -D redirect -R Duplicates -j jpg source/ target/

# Master selection with rename (demoted files renamed in place)
python op.py -c -D rename -K old -j jpg source/ target/
```

### Benefits

- **Intelligent organization**: Best files automatically prioritized
- **Prevents data loss**: Never lose original files to inferior duplicates
- **Automatic cleanup**: Inferior duplicates properly categorized
- **Audit trail**: Comprehensive logging of all decisions
- **Time saving**: No manual sorting of duplicates needed

## COMPREHENSIVE DUPLICATE DETECTION

### How It Works

orgphoto's comprehensive duplicate detection goes beyond simple filename checking by using SHA-256 content hashing:

#### 1. **Hash Cache Building**
- Scans ALL existing files in target directory at startup
- Calculates SHA-256 hash for each file
- Builds in-memory database: `{hash: [file_path1, file_path2, ...]}`
- Stores file modification times for cache invalidation

#### 2. **Duplicate Detection Process**
```
For each source file:
1. Calculate SHA-256 hash
2. Check hash cache for matching content
3. Check filename conflicts in destination
4. Apply duplicate handling strategy
5. Update hash cache if file is processed
```

#### 3. **Content vs Filename Detection**
- **Content duplicates**: Same SHA-256 hash, any filename, anywhere in target
- **Filename conflicts**: Same filename in same date directory
- **Both types**: Can be detected simultaneously

### Technical Details

#### Hash Cache Statistics
```bash
# Example log output:
Building comprehensive hash cache of target directory...
Hash cache built: 15,432 files indexed, 14,891 unique hashes
# Shows: 541 files had duplicate content
```

#### Memory Usage
- **Hash storage**: ~64 bytes per hash (SHA-256)
- **Path storage**: Variable, ~100-200 bytes per file path  
- **Cache metadata**: File modification times, ~16 bytes per file
- **Total estimate**: ~200-300 bytes per target file

#### Performance Characteristics
- **Cache building**: ~500-2000 files/second (depends on storage speed)
- **Hash calculation**: ~50-200 MB/second (depends on CPU)
- **Duplicate checking**: Near-instant lookup in memory cache

## PERFORMANCE CONSIDERATIONS

### Comprehensive Duplicate Detection (Default)

By default, orgphoto performs comprehensive SHA-256 checking of each incoming file against ALL existing files in the target directory.

**Benefits**:
- **True duplicate detection**: Finds identical files regardless of filename or location
- **Space efficiency**: Prevents storing duplicate content under different names  
- **Data integrity**: Ensures you're not losing unique content
- **Cross-directory detection**: Finds duplicates anywhere in target tree

**Performance Impact**:
- **Startup time**: 10-60 seconds for 10,000 files (depends on storage speed)
- **Memory usage**: ~200-300 bytes per target file for hash cache
- **Processing time**: Each incoming file hashed once (~10-50 MB/second)
- **Disk I/O**: One-time read of all target files during cache build

### Performance Benchmarks

| Target Files | Cache Build Time | Memory Usage | Processing Speed |
|-------------|------------------|---------------|-----------------|
| 1,000 files | 2-5 seconds | ~300 KB | 200-500 files/min |
| 10,000 files | 20-60 seconds | ~3 MB | 150-300 files/min |
| 50,000 files | 2-5 minutes | ~15 MB | 100-200 files/min |
| 100,000 files | 5-15 minutes | ~30 MB | 50-150 files/min |

*Benchmarks vary by storage type (SSD vs HDD), network latency, and CPU speed*

### When to Disable Comprehensive Checking (`-N`)

Use the `-N` flag to disable comprehensive checking when:

**Large Target Directories**:
- **>50,000 files**: Cache building becomes time-consuming
- **Network storage**: Reading all files over network is slow
- **Limited memory**: Cache may use significant RAM

**Performance Priority**:
- **Frequent runs**: Cache rebuilt each time (not persistent between runs)
- **Fast import needed**: Only care about filename conflicts
- **Batch processing**: Processing speed more important than deduplication

**Use Cases for `-N`**:
```bash
# Fast processing, only filename-based duplicate detection
python op.py -c -N -D rename -j jpg source/ target/

# Large target directory, redirect filename conflicts only  
python op.py -c -N -D redirect -j jpg source/ huge_target/

# Speed-optimized batch import
python op.py -c -N -D overwrite -j jpg,png,heic batch_source/ target/
```

### Performance Optimization Strategies

#### 1. **Mode Selection by Use Case**
```bash
# Maximum safety (comprehensive + interactive)
python op.py -c -D interactive -j jpg source/ target/

# Balanced (comprehensive + automatic handling)  
python op.py -c -D content -j jpg source/ target/

# Speed optimized (filename-only + rename)
python op.py -c -N -D rename -j jpg source/ target/

# Maximum speed (filename-only + overwrite)
python op.py -c -N -D overwrite -j jpg source/ target/
```

#### 2. **Target Directory Management**
- **Separate by date**: Use different target directories for different time periods
- **Archive old files**: Move older files to separate directories
- **Clean duplicates**: Periodically clean up redirect directories

#### 3. **Hardware Considerations**
- **SSD storage**: 5-10x faster cache building than HDD
- **More RAM**: Allows larger caches without performance impact
- **Faster CPU**: Improves hash calculation speed
- **Network storage**: Consider local staging for large operations

### Duplicate Handling Performance Comparison

| Mode | Requires Comprehensive | Speed | Memory | Safety |
|------|----------------------|--------|---------|---------|
| `skip` | Yes (default) | Medium | High | Maximum |
| `content` | Yes (recommended) | Medium | High | Maximum |
| `interactive` | Yes (optional) | Slow* | High | Maximum |
| `rename` | No (optional) | Fast | Low | High |
| `redirect` | No (optional) | Fast | Low | High |
| `overwrite` | No (optional) | Fastest | Low | Minimal |

*Interactive mode speed depends on user response time

### Real-World Performance Tips

1. **Initial import**: Use comprehensive checking for first-time setup
2. **Regular updates**: Consider `-N` for frequent incremental updates
3. **Archive consolidation**: Use `content` mode for merging archives
4. **Mobile import**: Use default settings for safety
5. **Bulk processing**: Use `-N -D rename` for speed
6. **Migration projects**: Use `interactive` mode for control

The hash cache provides excellent performance for most use cases, typically processing 100-500 files per minute even with comprehensive checking enabled.

## Installation
**<u>pip</u>** 
Just run:

    1. Clone the repo, or just download `op.py`
    2. pip install hachoir
    3. Then execute the script using python as in # python op.py

**<u>uv</u>** - Thank you uv! ![uv installation here](https://docs.astral.sh/uv/getting-started/installation/)

    1. Clone the repo (you'll also want the supporting files)
    2. Make sure uv is installed. It will handle dependencies 
    3. Then execute the script using python as in # uv run op.py

## Building Windows .exe

### Recommended Build Method (using uv)

This project supports building Windows executables using PyInstaller with proper dependency resolution:

```bash
# Recommended approach - ensures proper dependency resolution
uv run pyinstaller --noconfirm --onefile --console --collect-all hachoir --exclude-module hachoir.wx.tree_view --icon "doc/favicon.ico" "op.py"

# Alternative using existing spec file (after running uv sync)
uv run pyinstaller op.spec
```

**Why use `uv run pyinstaller`?**
- **Dependency Resolution**: `uv run` ensures PyInstaller runs within the project's virtual environment where `hachoir` and other dependencies are properly installed
- **Module Discovery**: The `--collect-all hachoir` flag tells PyInstaller to include all hachoir submodules and data files
- **Reliability**: Avoids "ModuleNotFoundError" issues that occur when PyInstaller can't find project dependencies
- **Consistency**: Uses the same dependency versions as your development environment

### Legacy Build Methods

```bash
# Using auto-py-to-exe with existing config (may have dependency issues)
auto-py-to-exe op/pyinstallerconfig.json

# Manual PyInstaller command (not recommended - missing dependencies)
pyinstaller --noconfirm --onefile --console --icon "doc/favicon.ico" "op.py"
```

**Note**: Legacy methods may fail with `ModuleNotFoundError: No module named 'hachoir'` because they don't properly resolve dependencies from the uv environment.


Here's an example of running the built .exe in Windows, where op.exe is asked to Move all files even if No eXif data is found (ahem heic files), move files of extensions (case-insensitive) jpg,png,jpeg,heic,mov, from `src1` (and its sub directories) to `target` into folders by date:

```bash
# With comprehensive duplicate detection (default)
op.exe -m -x no -j jpg,png,jpeg,heic,mov C:\Users\user\Github\orgphoto\testing\src1 C:\Users\user\Github\orgphoto\testing\target

# Redirect duplicates to separate folder
op.exe -m -x no -D redirect -j jpg,png,jpeg,heic,mov C:\Users\user\Github\orgphoto\testing\src1 C:\Users\user\Github\orgphoto\testing\target

# Custom redirect directory and duplicate keyword
op.exe -m -x no -D redirect -R Archive\Duplicates -K copy -j jpg,png,jpeg,heic,mov C:\Users\user\Github\orgphoto\testing\src1 C:\Users\user\Github\orgphoto\testing\target

# For faster processing on large target directories
op.exe -m -x no -N -D rename -j jpg,png,jpeg,heic,mov C:\Users\user\Github\orgphoto\testing\src1 C:\Users\user\Github\orgphoto\testing\target
```

Examples of log entries
------------------------

#### Plain info logging on top, verbose debug logging on the bottom

![logging](../main/doc/log2.png)


## File Formats

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

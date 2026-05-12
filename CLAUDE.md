# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

orgphoto (op) is a Python command-line tool that organizes photos and videos by date. It scans source directories recursively, extracts creation dates from EXIF metadata or file system dates, and copies/moves files into date-organized folders (YYYY_MM_DD format).

## Key Architecture

- **Main executable**: `op.py` - The primary CLI application (single-file).
- **Dependencies**: `hachoir` (file-format-agnostic metadata), `exifread` (fast EXIF for images/RAW), `pathlib` (file operations).
- **Build system**: `uv` for dependency management. PyInstaller produces the Windows `.exe`; the canonical build runs via `.github/workflows/build.yml` on every push, and tagged pushes auto-publish a GitHub Release.

## Common Commands

### Running the application
```bash
# Using uv (recommended - handles dependencies automatically)
uv run op.py [options] SOURCE_DIR DEST_DIR

# Using python directly (requires hachoir + exifread installed)
python op.py [options] SOURCE_DIR DEST_DIR

# Examples with short flags:
uv run op.py -c -D content -j jpg source/ target/        # Content-based duplicates
uv run op.py -m -D interactive -j jpg source/ target/    # Interactive mode
uv run op.py -c -D redirect -j jpg source/ target/       # Redirect duplicates
uv run op.py -c -N -j jpg source/ target/                # Disable comprehensive check
uv run op.py -c -D redirect -R MyDups -K copy source/ target/  # Custom redirect
uv run op.py -c -D rename -K backup -j jpg source/ target/     # Rename mode
uv run op.py -c -D overwrite -v -j jpg source/ target/         # Overwrite mode
uv run op.py -O -B target/                                      # Refresh hash cache only (no copy)
```

### Scheduling cache refresh (v2.2.0+)
For very large backup trees (100k+ files), pre-warm the cache so copy jobs find it up to date:
```bash
# Linux cron: refresh every night at 02:00
0 2 * * * cd /path/to/orgphoto && uv run op.py --cache-only /backups/photos >> /var/log/orgphoto-cache.log 2>&1

# Windows Task Scheduler equivalent: run op.exe --cache-only D:\Backups\Photos
```
The next real copy job will report most files as `reused` rather than `freshly hashed`.

### Development setup
```bash
# Install dependencies with uv
uv sync

# check the code after each round of development
uv run ruff check --fix . && uv run ruff format . 

# Install dependencies with pip
pip install hachoir auto-py-to-exe
```

### Building Windows executable

**Preferred: GitHub Actions (`.github/workflows/build.yml`)**
Every push to `main`, every PR, and every `v*` tag triggers the `Build` workflow,
which runs tests on Linux + Windows and produces `op.exe` as a downloadable
artifact. Tagged pushes also attach the `.exe` to a GitHub Release automatically.
Grab the artifact from the workflow run page, or `gh run download <run-id>`.

For a one-off local build (must run on a Windows host — PyInstaller does not
cross-compile):

```bash
# Recommended (uv ensures correct dependency resolution)
uv run pyinstaller --noconfirm --onefile --console --collect-all hachoir --collect-all exifread --icon "doc/favicon.ico" "op.py"

# Alternative using the existing spec file (after running uv sync)
uv run pyinstaller op.spec
```

**Why use `uv run pyinstaller`?**
- **Dependency Resolution**: `uv run` ensures PyInstaller runs within the project's virtual environment where `hachoir` and other dependencies are properly installed
- **Module Discovery**: The `--collect-all hachoir` flag tells PyInstaller to include all hachoir submodules and data files
- **Reliability**: Avoids "ModuleNotFoundError" issues that occur when PyInstaller can't find project dependencies
- **Consistency**: Uses the same dependency versions as your development environment

## Core Functionality

The application processes images and videos with these key features:
- **EXIF-first approach**: Prefers metadata creation dates over filesystem dates
- **Flexible filtering**: Three modes for handling files without EXIF (`yes`/`no`/`fs`)
- **Batch operations**: Copy or move operations with dry-run support
- **Comprehensive duplicate detection**: By default, performs SHA-256 checking of each incoming file against ALL existing files in target directory (not just same filename)
- **Advanced duplicate handling**: Six modes for handling duplicate files:
  - `skip` (default) - Skip if filename exists or identical content found
  - `overwrite` - Always replace existing files
  - `rename` - Add numeric suffix to duplicates (e.g., `photo_001.jpg`)
  - `content` - Compare file hashes; skip identical content, rename different content
  - `interactive` - Prompt user for each duplicate
  - `redirect` - Move duplicates to separate directory with intelligent renaming
- **Performance control**: Use `-N` or `--no-comprehensive-check` to disable comprehensive checking for large target directories
- **Hash caching**: Builds and maintains a persistent SQLite hash database of target files for efficient duplicate detection; only rehashes new or modified files on subsequent runs
- **Extensible formats**: Supports all file types recognized by hachoir library
- **Detailed logging**: Progress reporting and operation logging to destination directory

## Redirect Duplicate Handling

The redirect mode (`-D redirect`) provides intelligent duplicate management:

### Key Features
- **Automatic directory creation**: Creates `Duplicates/` folder in target root by default
- **Custom redirect directory**: Use `-R DIR` to specify alternative location (relative or absolute)
- **Intelligent renaming**: Uses configurable keyword (default "duplicate") with `-K WORD`
- **Incremental numbering**: Handles multiple duplicates automatically
  - `photo.jpg` → `photo_duplicate.jpg`
  - If exists → `photo_duplicate_001.jpg`
  - If exists → `photo_duplicate_002.jpg`, etc.

### Usage Examples
```bash
# Basic redirect to target/Duplicates/
uv run op.py -c -D redirect -j jpg source/ target/

# Custom directory and keyword
uv run op.py -c -D redirect -R Archive/Duplicates -K copy -j jpg source/ target/

# Interactive mode includes redirect option
uv run op.py -m -D interactive -j jpg source/ target/  # User can choose redirect
```

### Integration with Comprehensive Checking
- Works with SHA256-based duplicate detection (detects true content duplicates)
- Works with filename-based conflicts (traditional duplicate detection)
- Maintains all existing comprehensive checking benefits

## File Organization

- `op.py` - Main application (CLI parsing, file processing, EXIF extraction, cache)
- `op.spec` - PyInstaller specification file for the Windows build
- `test_op.py`, `test_v210.py` - pytest test suites (71 tests as of v2.2.4)
- `.github/workflows/build.yml` - CI: tests on Linux + Windows, builds .exe, attaches to GitHub Release on tag push
- `docs/` - Topic deep-dives (usage, performance, duplicate handling, etc.)
- `testing/` - Sample photo fixtures for manual / exploratory testing
- `doc/` - Image assets (logo, favicon, log screenshot)

## VERSION TRACKING REQUIREMENT - CRITICAL REMINDER FOR CLAUDE

**MANDATORY**: Every time you make functional changes to op.py, you MUST:

1. **Increment version number** in `__version__` variable in op.py
2. **Update version history comment** with changes made
3. **Update date** in `myversion` variable to current date
4. **Use semantic versioning**: MAJOR.MINOR.PATCH
   - MAJOR: Breaking changes or major architecture changes
   - MINOR: New features, significant enhancements (like new default behavior)
   - PATCH: Bug fixes, minor improvements, documentation updates

**Current version: 2.2.5** (as of 2026-05-12)

**Recent version history:**
- v2.2.5: Cross-platform fix for the v2.2.4 master-score guard. Linux's
  `mktime()` accepts pre-1970 datetimes and returns a negative timestamp, so
  the `try/except OSError` guard from v2.2.4 never fired there — a
  sub-threshold date would *win* the "oldest wins" master tiebreaker instead
  of losing it. CI caught this on the Linux test job. `calculate_master_score`
  now checks `< _MIN_REASONABLE_DATE` before calling `.timestamp()` so
  behavior is identical on both platforms.
- v2.2.4: Fix crash on files with bogus pre-1970 metadata dates. QuickTime/MP4
  files whose `creation_time` atom is zero parse to 1904-01-01, which causes
  `datetime.timestamp()` to raise `OSError 22 (EINVAL)` on Windows from the
  underlying `mktime()` call. `get_created_date` and `get_created_date_fast`
  now drop dates before `_MIN_REASONABLE_DATE` (1990-01-01) so the caller
  falls back to filesystem mtime, and `calculate_master_score` wraps the
  `.timestamp()` call in `try/except OSError` as a defensive guard. 8 new
  regression tests in `TestBogusMetadataDates`.
- v2.2.3: Docs-only release. README slimmed from 1063 → <70 lines with
  deep-dive content moved into 8 topic files under `docs/`. Added proper
  Keep-a-Changelog `CHANGELOG.md`. Removed 12 stale files (~12 MB freed):
  legacy `main.py`, `MANIFEST.in`, `pyinstallerconfig.json`, `pm.png`,
  the old v2.0.1 `dist/op.exe`, three v1.x test scaffold files, three
  unreferenced log screenshots, and `doc/cassette.tape`. Test suite
  dropped 71 → 63 with zero coverage loss.
- v2.2.2: Fixed SQLite handle leak when `TargetHashCache` init fails — a
  partially-opened `sqlite3.Connection` is now closed before `self.conn` is
  cleared, and `__init__` closes the cache if `_build_cache()` raises. On
  Windows this previously caused `WinError 32` on tempdir cleanup. Hardened
  `TestSetupLoggerHandlerLeak` for Windows (no longer rmtrees an open log
  file; path comparison handles 8.3 short names). Added GitHub Actions
  `build.yml`: runs pytest on Linux + Windows, builds `op.exe`, uploads it
  as a 30-day artifact, and attaches it to a GitHub Release on `v*` tags.
- v2.2.1: Cache build now commits to SQLite incrementally (every 1000
  freshly-hashed files) instead of buffering everything in memory until the
  walk completes. A crash or kill during a multi-hour build on a 200k-file
  tree now loses at most ~1000 files of work; the next run resumes from
  where it left off via the existing mtime+size cache-hit logic. Stale
  deletions still happen once at the end of the walk (they require the full
  walk to determine what's actually gone).
- v2.2.0: Added `-O`/`--cache-only` mode: build or refresh the hash cache for a
  target directory without copying or moving any files. Pass the target as the
  single positional argument. Intended to be scheduled (cron / Task Scheduler)
  so that subsequent copy jobs find the cache already warm. Useful for stable
  backup trees with 100k+ files.
- v2.1.1: Fixed logger handler leak in `set_up_logging()` — stale FileHandlers
  from prior invocations were not removed, causing FileNotFoundError when a
  second job (or test) targeted a different destination. All handlers are now
  closed and detached before the new one is attached.
- v2.1.0: Persistent SQLite hash cache (.orgphoto_cache.db) with mtime+size validation
  - Only rehashes new/modified files; reuses cached hashes for unchanged files
  - Added `-C`/`--cache-dir` flag to place cache DB on a different (faster) drive
  - Added `-B`/`--benchmark` flag to print cache build timing and hit-rate statistics
  - Added `-F`/`--fast-exif` flag: uses exifread for fast header-only EXIF extraction
    on image/RAW files, falls back to hachoir for video/audio. Also adds HEIC/RAW support.
- v2.0.2: Enhanced logging to include full source path for better traceability
- v2.0.1: Enhanced session header in log file with clear version information and formatting
- v2.0.0: MAJOR UPDATE - Intelligent master file selection system
  - Automatically determines best master file based on: shortest filename, oldest date, no duplicate keywords
  - Demotes existing files when incoming file is better master candidate
  - Protects master files from being overwritten by inferior duplicates
  - Comprehensive logging of master selection criteria and demotion actions
- v1.5.1: Fixed version output appearing multiple times
- v1.5.0: Added version display in help output header and when run without arguments
- v1.4.1: Updated documentation and README with new features and examples
- v1.4.0: Added all file types as default (no extension requirement), enhanced comprehensive help text
- v1.3.x: Original comprehensive duplicate detection system

This ensures users can track changes and compatibility across versions.
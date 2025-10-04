# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

orgphoto (op) is a Python command-line tool that organizes photos and videos by date. It scans source directories recursively, extracts creation dates from EXIF metadata or file system dates, and copies/moves files into date-organized folders (YYYY_MM_DD format).

## Key Architecture

- **Main executable**: `op.py` - The primary CLI application with full functionality
- **Entry point**: `main.py` - Simple entry point that imports and runs the main application
- **Dependencies**: Uses `hachoir` for metadata extraction, `pathlib` for file operations
- **Build system**: Uses `uv` for dependency management and PyInstaller for Windows executable compilation

## Common Commands

### Running the application
```bash
# Using uv (recommended - handles dependencies automatically)
uv run op.py [options] SOURCE_DIR DEST_DIR

# Using python directly (requires hachoir installed)  
python op.py [options] SOURCE_DIR DEST_DIR

# From main entry point
uv run main.py  # (currently just prints hello message)

# Examples with short flags:
uv run op.py -c -D content -j jpg source/ target/        # Content-based duplicates
uv run op.py -m -D interactive -j jpg source/ target/    # Interactive mode
uv run op.py -c -D redirect -j jpg source/ target/       # Redirect duplicates
uv run op.py -c -N -j jpg source/ target/                # Disable comprehensive check
uv run op.py -c -D redirect -R MyDups -K copy source/ target/  # Custom redirect
uv run op.py -c -D rename -K backup -j jpg source/ target/     # Rename mode
uv run op.py -c -D overwrite -v -j jpg source/ target/         # Overwrite mode
```

### Development setup
```bash
# Install dependencies with uv
uv sync

# Install dependencies with pip
pip install hachoir auto-py-to-exe
```

### Building Windows executable
```bash
# Recommended approach using uv (ensures proper dependency resolution)
uv run pyinstaller --noconfirm --onefile --console --collect-all hachoir --icon "doc/favicon.ico" "op.py"

# Alternative using existing spec file (after running uv sync)
uv run pyinstaller op.spec

# Legacy approaches (may fail with dependency issues)
# Using auto-py-to-exe with existing config
auto-py-to-exe op/pyinstallerconfig.json

# Manual PyInstaller command (not recommended - missing dependencies)
pyinstaller --noconfirm --onefile --console --icon "doc/favicon.ico" "op.py"
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
- **Hash caching**: Builds and maintains an in-memory hash database of target files for efficient duplicate detection
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

- `op.py` - Main application logic (CLI parsing, file processing, EXIF extraction)
- `op/op.spec` - PyInstaller specification file (legacy, references old filename)
- `op/pyinstallerconfig.json` - auto-py-to-exe configuration for building executable
- `testing/` - Contains test directories with sample photos for validation
- `doc/` - Documentation assets (logos, screenshots)

## VERSION TRACKING REQUIREMENT - CRITICAL REMINDER FOR CLAUDE

**MANDATORY**: Every time you make functional changes to op.py, you MUST:

1. **Increment version number** in `__version__` variable in op.py
2. **Update version history comment** with changes made
3. **Update date** in `myversion` variable to current date
4. **Use semantic versioning**: MAJOR.MINOR.PATCH
   - MAJOR: Breaking changes or major architecture changes
   - MINOR: New features, significant enhancements (like new default behavior)
   - PATCH: Bug fixes, minor improvements, documentation updates

**Current version: 1.5.1** (as of 2025-10-04)

**Recent version history:**
- v1.5.1: Fixed version output appearing multiple times
- v1.5.0: Added version display in help output header and when run without arguments
- v1.4.1: Updated documentation and README with new features and examples
- v1.4.0: Added all file types as default (no extension requirement), enhanced comprehensive help text
- v1.3.x: Original comprehensive duplicate detection system

This ensures users can track changes and compatibility across versions.
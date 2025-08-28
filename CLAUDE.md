# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

orgphoto (op) is a Python command-line tool that organizes photos and videos by date. It scans source directories recursively, extracts creation dates from EXIF metadata or file system dates, and copies/moves files into date-organized folders (YYYY_MM_DD format).

## Key Architecture

- **Main executable**: `op/op.py` - The primary CLI application with full functionality
- **Entry point**: `main.py` - Simple entry point that imports and runs the main application
- **Dependencies**: Uses `hachoir` for metadata extraction, `pathlib` for file operations
- **Build system**: Uses `uv` for dependency management and PyInstaller for Windows executable compilation

## Common Commands

### Running the application
```bash
# Using uv (recommended - handles dependencies automatically)
uv run op/op.py [options] SOURCE_DIR DEST_DIR

# Using python directly (requires hachoir installed)
python op/op.py [options] SOURCE_DIR DEST_DIR

# From main entry point
uv run main.py  # (currently just prints hello message)
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
# Using auto-py-to-exe with existing config
auto-py-to-exe op/pyinstallerconfig.json

# Manual PyInstaller command
pyinstaller --noconfirm --onefile --console --icon "doc/favicon.ico" "op/op.py"
```

## Core Functionality

The application processes images and videos with these key features:
- **EXIF-first approach**: Prefers metadata creation dates over filesystem dates
- **Flexible filtering**: Three modes for handling files without EXIF (`yes`/`no`/`fs`)
- **Batch operations**: Copy or move operations with dry-run support
- **Comprehensive duplicate detection**: By default, performs SHA-256 checking of each incoming file against ALL existing files in target directory (not just same filename)
- **Advanced duplicate handling**: Five modes for handling duplicate files:
  - `skip` (default) - Skip if filename exists or identical content found
  - `overwrite` - Always replace existing files
  - `rename` - Add numeric suffix to duplicates (e.g., `photo_001.jpg`)
  - `content` - Compare file hashes; skip identical content, rename different content
  - `interactive` - Prompt user for each duplicate
- **Performance control**: Use `--no-comprehensive-check` to disable comprehensive checking for large target directories
- **Hash caching**: Builds and maintains an in-memory hash database of target files for efficient duplicate detection
- **Extensible formats**: Supports all file types recognized by hachoir library
- **Detailed logging**: Progress reporting and operation logging to destination directory

## File Organization

- `op/op.py` - Main application logic (CLI parsing, file processing, EXIF extraction)
- `op/op.spec` - PyInstaller specification file (legacy, references old filename)
- `op/pyinstallerconfig.json` - auto-py-to-exe configuration for building executable
- `testing/` - Contains test directories with sample photos for validation
- `doc/` - Documentation assets (logos, screenshots)
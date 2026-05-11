# orgphoto (op)

![logo](doc/logo.png)

Organize photos and videos by date. Recursively scans a source directory, extracts creation dates from EXIF metadata (or filesystem timestamps as fallback), and copies / moves files into date-organized subdirectories (`YYYY_MM_DD`). Comprehensive SHA-256 duplicate detection with six handling modes, intelligent master-file selection, and a persistent hash cache designed for archives with hundreds of thousands of files.

[![Build](https://github.com/johnzastrow/orgphoto/actions/workflows/build.yml/badge.svg)](https://github.com/johnzastrow/orgphoto/actions/workflows/build.yml)
[![Release](https://img.shields.io/github/v/release/johnzastrow/orgphoto)](https://github.com/johnzastrow/orgphoto/releases)

---

## Quick start

```bash
# Install (uv recommended)
git clone https://github.com/johnzastrow/orgphoto.git
cd orgphoto
uv sync

# Copy photos into date-organized subdirectories
uv run op.py -c source/ target/

# Refresh the hash cache for a large backup tree (no copying)
uv run op.py -O -B /backups/photos

# Help
uv run op.py --help
uv run op.py --examples
```

For Windows users: grab the prebuilt `op.exe` from the [latest GitHub Release](https://github.com/johnzastrow/orgphoto/releases) — no Python required.

---

## ✨ Highlights

- **🗓️ Scheduled cache refresh** (v2.2.0+) — `-O / --cache-only` builds the SHA-256 hash cache without copying, so cron / Task Scheduler can keep huge backup trees pre-warmed.
- **🛡️ Crash-safe builds** (v2.2.1+) — cache commits incrementally to SQLite; an interrupted multi-hour build loses at most one batch (~1000 files) instead of starting over.
- **⚡ Persistent hash cache** (v2.1.0+) — `.orgphoto_cache.db` validated by mtime+size; subsequent runs only rehash new or modified files.
- **⚡ Fast EXIF via exifread** (v2.1.0+) — header-only reads for JPEG, TIFF, PNG, WebP, HEIC/HEIF, and all major RAW formats; 5-50× faster than hachoir, with automatic fallback for video/audio.
- **📁 HEIC / RAW support** — exifread reads creation dates from formats hachoir doesn't handle (CR2, CR3, NEF, ARW, DNG, ORF, RW2, RAF, PEF, SRW).
- **🧠 Intelligent master selection** (v2.0+) — when duplicates collide, automatically picks the best file (no duplicate keywords → shortest name → oldest date) and demotes the rest.
- **🔄 Six duplicate handling modes** — `skip`, `content`, `rename`, `overwrite`, `interactive`, `redirect`.
- **🔍 Dry-run mode** — preview every action without touching files.

Full changelog: [CHANGELOG.md](CHANGELOG.md).

---

## Documentation

| Topic | What it covers |
|-------|----------------|
| [docs/usage.md](docs/usage.md) | Full CLI synopsis and every option |
| [docs/usage-examples.md](docs/usage-examples.md) | 30+ worked command-line examples |
| [docs/duplicate-handling.md](docs/duplicate-handling.md) | All six `-D` modes, comprehensive checking, redirect layout |
| [docs/master-selection.md](docs/master-selection.md) | v2.0+ intelligent master selection logic |
| [docs/performance.md](docs/performance.md) | Cache tuning, `-N` / `-O` / `-C` / `-B`, scheduled refresh |
| [docs/installation.md](docs/installation.md) | uv, pip, prebuilt `.exe` paths |
| [docs/building.md](docs/building.md) | CI workflow + local Windows build |
| [docs/file-formats.md](docs/file-formats.md) | exifread vs hachoir routing, supported formats |
| [CHANGELOG.md](CHANGELOG.md) | Release history |

---

## A note on heritage

This is a major rewrite of the upstream `skorokithakis/photocopy` project. Code has not been downstreamed from it for many versions.

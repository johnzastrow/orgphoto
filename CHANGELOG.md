# Changelog

All notable changes to **orgphoto** are documented in this file. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project adheres
to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Releases since v2.0.0 are tagged in git (`v<MAJOR>.<MINOR>.<PATCH>`) and have
matching GitHub Releases with the prebuilt Windows `op.exe` attached as of v2.2.2.

---

## [Unreleased]

Nothing in flight. Open issues and PRs:
- https://github.com/johnzastrow/orgphoto/issues
- https://github.com/johnzastrow/orgphoto/pulls

---

## [2.2.2] — 2026-05-11

### Fixed
- **SQLite handle leak when `TargetHashCache` init fails.**
  `_init_db()` now closes a partially-opened `sqlite3.Connection` in its `except`
  clause before setting `self.conn = None`, and `__init__()` closes the cache (via
  `self.close()`) if `_build_cache()` raises. Without these fixes, a corrupt DB
  file or a crash during cache build would orphan the underlying file handle.
  Linux silently allowed deleting the open files; Windows raised `WinError 32`
  on tempdir cleanup or any later attempt to remove the cache file. No behavior
  change on the happy path.
- Hardened `TestSetupLoggerHandlerLeak` so it no longer `shutil.rmtree`s an
  open log file and so its path comparison is robust to Windows 8.3 short
  names (`RUNNER~1` vs `runneradmin`).

### Added
- **CI: GitHub Actions Windows build.** `.github/workflows/build.yml` runs the
  full pytest suite on Linux (Ubuntu) **and** Windows, builds `op.exe` on
  `windows-latest` with `--collect-all hachoir --collect-all exifread`,
  smoke-tests it, and uploads it as a 30-day artifact named
  `op-windows-<sha>`. Tagged pushes (`v*`) also publish a GitHub Release with
  the `.exe` auto-attached and release notes generated from git history.

### Removed
- 12 stale files (~12 MB freed): `main.py`, `MANIFEST.in`, `pyinstallerconfig.json`,
  `pm.png`, the old `dist/op.exe` (v2.0.1), `test_simple.py`, `test_integration.py`,
  `run_tests.py`, and three unreferenced log screenshots. The v1.x test
  scaffolding removal drops the suite from 71 → 63 tests with zero coverage
  loss — those tests duplicated `test_op.py` / `test_v210.py` coverage.

### Internal
- `dist/` added to `.gitignore` so local PyInstaller output no longer risks
  being committed.

---

## [2.2.1] — 2026-05-11

### Fixed
- **Crash-safe cache builds.** `_build_cache()` now commits to SQLite every
  1000 freshly-hashed files via a new `_flush_inserts()` helper, instead of
  buffering everything in memory until the walk completes. A crash, kill, or
  power loss during a multi-hour build on a 200k-file tree now loses at most
  ~1000 files of work; the next run resumes from where it left off via the
  existing mtime+size cache-hit logic. ~200 extra commits on a 200k-file
  build (~1s overhead) — negligible compared to the hours protected.
- New class constant `TargetHashCache._COMMIT_BATCH_SIZE = 1000` gates the
  flush cadence.
- Stale deletions still happen once at the end of the walk — they require the
  full walk to know what's actually gone.

### Added
- Regression test `TestIncrementalCommit` shrinks the batch size, injects a
  `RuntimeError` into `calculate_file_hash` partway through, and verifies
  that a subsequent build reuses the partially-persisted rows instead of
  rehashing them.

---

## [2.2.0] — 2026-05-11

### Added
- **`-O` / `--cache-only` mode.** Build or refresh the SQLite hash cache for a
  target directory and exit, **without copying or moving any files**. Pass the
  target as the single positional argument; `SOURCE_DIR` is unused. Honors
  `-C` / `-B` / `-v`. Incompatible with `-m` / `-c` / `-d` / `-N` (exits 2).
  If both positionals are supplied, `DEST_DIR` wins and `SOURCE_DIR` is
  ignored with a stderr warning so a cron entry can reuse a copy-job's
  argument layout.

  Designed to be scheduled via cron / Task Scheduler so subsequent copy jobs
  always find a warm cache. Especially valuable for stable backup trees with
  100k+ files where the first cache build is hours of I/O but every
  subsequent build only rehashes new or modified files.

  Example cron entry:
  ```cron
  0 2 * * * cd /opt/orgphoto && uv run op.py --cache-only /backups/photos
  ```

### Added — tests
- `TestCacheOnlyMode` (8 tests): DB creation, second-run reuse, custom cache
  dir, rejection of incompatible flags, requirement of a target argument,
  nonexistent-target handling, source-arg-ignored warning.
- `TestNormalModeRequiresBothPositionals` — without `-O`, both `SOURCE_DIR`
  and `DEST_DIR` must be supplied (exits 2 with a clear error if not).

---

## [2.1.1] — 2026-05-11

### Fixed
- **Logger handler leak in `set_up_logging()`.** The function now closes and
  detaches stale `FileHandler`s from earlier invocations before attaching the
  new one. Before this fix, calling `set_up_logging()` twice in the same
  Python process (or test invocation) would leave the original handler
  attached, pointing at a deleted log file in a previous destination, and the
  next `logger.info()` call would raise `FileNotFoundError`.
- Removed two stale `test_op.py` tests for v1.x duplicate-mode behavior that
  the v2.0 master-selection feature had superseded; `test_v210.py` already
  has correct v2.0+ coverage in `TestIntegrationFixed`.

### Added
- Regression test `TestSetupLoggerHandlerLeak::test_second_call_replaces_stale_handler`.

---

## [2.1.0] — 2026-02-08

### Added
- **Persistent SQLite hash cache.** SHA-256 hashes are stored in
  `.orgphoto_cache.db` in the target directory and reused across runs. Each
  entry records `(file_path, file_hash, file_size, file_mtime)`; on
  subsequent runs, files whose size + mtime match the cached values skip the
  expensive hash recomputation. Reduces startup on large libraries from
  minutes to seconds.
- **Fast EXIF extraction (default).** Image files (JPEG, TIFF, PNG, WebP,
  HEIC/HEIF) and RAW formats (CR2, CR3, NEF, ARW, DNG, ORF, RW2, RAF, PEF,
  SRW) now route through `exifread`, which reads only the file header — 5-50x
  faster than hachoir's full parse. Falls back to hachoir for video/audio or
  on exifread failure. Disable globally with `--no-fast-exif`.
- **HEIC and RAW format support** that hachoir does not provide on its own.
- `-C` / `--cache-dir DIR` — place `.orgphoto_cache.db` on a different (faster)
  drive than the target. Useful when target is on a slow HDD or NAS.
- `-B` / `--benchmark` — print cache build timing and hit-rate statistics to
  the console.
- Console progress output during both hash cache building and file
  processing.

### Internal
- Comprehensive `test_v210.py` test suite covering the new cache, fast EXIF,
  console progress, and `-B` / `-C` / `-N` / `--no-fast-exif` flags.

---

## [2.0.2] — 2025

### Changed
- Log entries now include the full source path instead of just the filename,
  for better traceability when consolidating multiple archives.

---

## [2.0.1] — 2025-10-14

### Changed
- Enhanced log session headers: 80-character separator lines, clear version
  information, ISO timestamps for session start/end, blank lines between
  sessions for readability.

---

## [2.0.0] — 2025-10-14

### Added — **MAJOR**: Intelligent Master File Selection

When duplicates are detected, orgphoto now automatically determines which file
should be the "master" (definitive version) using a three-tier priority system:

1. **No duplicate keywords** — files with names like `photo_copy.jpg`,
   `vacation (1).jpg`, `sunset_duplicate.jpg`, `image_backup.jpg`, etc. are
   demoted relative to files without those markers.
2. **Shortest filename** — among same-keyword-status files, the shorter name
   wins (originals tend to be shorter).
3. **Oldest creation/modification date** — if names are equally simple, the
   older file wins (first-created tends to be the original).

When the incoming file is the better master, the existing file is **demoted**
according to the active duplicate-handling mode (skip/rename/redirect). When
the existing file is the better master, it is **protected** from being
overwritten even in overwrite mode.

Comprehensive logging records the selection criteria, non-master files, and
the demotion / retention action for every conflict.

### Added — duplicate handling modes
- `-D content` — skip if SHA-256 matches, rename if same filename but
  different content.
- `-D interactive` — prompt for each conflict with full context (filename,
  content match, file sizes, dates) and per-file action choice.
- `-D redirect` — move duplicates to a separate directory structure that
  mirrors the date-based layout.
- `-R DIR` / `--redirect-dir` — directory for redirected duplicates
  (default `Duplicates`).
- `-K WORD` / `--duplicate-keyword` — keyword inserted into duplicate
  filenames (default `duplicate`, e.g. `photo_duplicate.jpg`).
- `-N` / `--no-comprehensive-check` — disable SHA-256 checking for speed on
  very large target directories.

---

## [1.6.0] — 2025

### Added
- Detailed conflict logging showing duplicate file paths and whether the
  conflict is by filename, content, or both.

---

## [1.5.1] — 2025

### Fixed
- Version output appearing multiple times in some invocations.

---

## [1.5.0] — 2025

### Added
- Version displayed in `--help` output header and when run without arguments,
  so users can confirm at a glance which build they're running.

---

## [1.4.1] — 2025

### Changed
- Documentation and README expanded with new features and examples.

---

## [1.4.0] — 2025

### Changed
- **All file types processed by default.** Omitting `-j` / `--extensions` no
  longer restricts processing to a hard-coded list — every file in the
  source tree is considered. Provide `-j` only when you want to filter.

### Added
- Comprehensive help text for all options, with examples in `--examples`.

---

## [1.3.x] — earlier 2025

### Added
- Original comprehensive (SHA-256) duplicate detection system. Builds an
  in-memory hash map of the target tree at startup and compares each
  incoming file against it.

---

[Unreleased]: https://github.com/johnzastrow/orgphoto/compare/v2.2.2...HEAD
[2.2.2]: https://github.com/johnzastrow/orgphoto/releases/tag/v2.2.2
[2.2.1]: https://github.com/johnzastrow/orgphoto/compare/v2.2.0...v2.2.1
[2.2.0]: https://github.com/johnzastrow/orgphoto/compare/v2.1.1...v2.2.0
[2.1.1]: https://github.com/johnzastrow/orgphoto/compare/v2.1.0...v2.1.1
[2.1.0]: https://github.com/johnzastrow/orgphoto/compare/v2.0.2...v2.1.0
[2.0.2]: https://github.com/johnzastrow/orgphoto/compare/v2.0.1...v2.0.2
[2.0.1]: https://github.com/johnzastrow/orgphoto/compare/v2.0.0...v2.0.1
[2.0.0]: https://github.com/johnzastrow/orgphoto/compare/v1.6.0...v2.0.0

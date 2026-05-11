# orgphoto Test Suite

## Overview

The test suite has been substantially expanded since the initial 15-test snapshot in this file. As of v2.2.0 (2026-05-11) it covers core file operations, v2.0 master-selection behavior, the v2.1.0 persistent SQLite hash cache, fast EXIF extraction via exifread, the `-B`/`-C`/`-N`/`--no-fast-exif` flags, console progress output, and the v2.2.0 cache-only mode.

## Current Status

**71 passing / 0 failing** (`uv run pytest --tb=no -q`)

## Test Files

### `test_op.py` — Core helpers and integration smoke tests
- File hash calculation, duplicate filename generation, extension normalization
- Argument parsing and duplicate-mode parsing
- Integration tests for copy / move / dry-run flows

### `test_v210.py` — v2.1.0 + v2.2.0 feature tests
Organized by feature class:

- `TestHashCacheCreation` — DB file creation in target / custom cache dir, indexing, close
- `TestHashCacheReuse` — unchanged files reused, modified files rehashed, deleted entries pruned, new files picked up
- `TestHashCacheDBOperations` — `add_file()`, `invalidate_file()`, `find_duplicates()`, persistence across restart
- `TestHashCacheGracefulFallback` — corrupted/deleted DB triggers rebuild, empty/missing target dir handled
- `TestHashCacheSchemaVersion` — schema-version mismatch triggers rebuild
- `TestHashCacheSkipsOwnFiles` — `.orgphoto_cache.db` itself is not indexed
- `TestFastExifExtraction` — JPEG / TIFF / HEIC / RAW route through exifread; non-image and unsupported files fall back to hachoir
- `TestFastExifWithRealJpeg` — exifread and hachoir agree on dates for a minimal real JPEG
- `TestNoComprehensiveCheckFlag` — `-N` skips DB creation entirely
- `TestBenchmarkFlag` — `-B` prints all five stat fields including "Stale entries purged"
- `TestCacheDirFlag` — `-C` places the DB in the custom directory
- `TestNoFastExifFlag` — `--no-fast-exif` parses correctly and defaults to off
- `TestConsoleProgress` — "Done:" and "Hash cache ready" lines are emitted
- `TestIntegrationFixed` — copy / move / dry-run / rename / redirect against v2.0 master-selection
- `TestCacheOnlyMode` (v2.2.0) — `-O` builds DB and exits; second run reuses; `-C` honored; rejects `-c`/`-m`/`-d`/`-N`; requires a target directory; warns and uses DEST_DIR when both positionals are supplied; nonexistent target errors out
- `TestNormalModeRequiresBothPositionals` — without `-O`, both SOURCE_DIR and DEST_DIR are required
- `TestIncrementalCommit` (v2.2.1) — injects a fault mid-build to confirm batched commits actually flush to SQLite, and that a subsequent build reuses what was persisted
- `TestSetupLoggerHandlerLeak` (v2.1.1) — regression check that `set_up_logging()` replaces stale FileHandlers across calls

### `test_simple.py` and `test_integration.py`
Earlier test scaffolding from the v1.x era. Kept for now but mostly superseded by the categorized suites above.

## Running the suite

```bash
uv run pytest          # full suite, verbose
uv run pytest -q       # quiet
uv run pytest --tb=no  # only failures, no traceback noise
uv run pytest test_v210.py::TestCacheOnlyMode -v  # one class
```

## History

- **v2.2.0 (2026-05-11)**: 70 tests / 0 failures. Added `TestCacheOnlyMode` (8 tests) and `TestNormalModeRequiresBothPositionals`.
- **v2.1.1 (2026-05-11)**: 61 tests / 0 failures. Fixed `set_up_logging()` handler leak; removed two stale v1.x duplicate-mode tests in `test_op.py` that the v2.0 master-selection feature had superseded; added `TestSetupLoggerHandlerLeak` regression test.
- **v2.1.0 (2026-02-08)**: First comprehensive v2.1.0 test coverage in `test_v210.py`.
- **Initial snapshot (Feb 2026)**: 15 tests across `test_simple.py` and `test_integration.py`.

# Usage

Quick CLI synopsis. Run `op.py --help` for the same output with full descriptions, or `op.py --examples` for a built-in example list.

```text
usage: op.py [-h] [-m | -c] [-j EXT] [-v] [-x {yes,no,fs}] [-d]
             [-D DUPLICATE_HANDLING] [-N] [-R DIR] [-K WORD]
             [-C DIR] [-B] [-O] [--no-fast-exif] [--examples] [--version]
             [SOURCE_DIR] [DEST_DIR]
```

## Positional arguments

| Argument     | When required                                       | Notes |
|--------------|-----------------------------------------------------|-------|
| `SOURCE_DIR` | Required for copy/move; **omit** with `--cache-only`. | Scanned recursively. |
| `DEST_DIR`   | Required for copy/move; **target dir** for `--cache-only`. | Created if missing. |

## Options

| Flag | Long form | Purpose |
|------|-----------|---------|
| `-m` | `--move`               | Move files (mutually exclusive with `-c`). |
| `-c` | `--copy`               | Copy files (mutually exclusive with `-m`). |
| `-j EXT` | `--extensions EXT` | Comma-separated extensions to process, no dots. Default: **all** types. |
| `-v` | `--verbose`            | Verbose logging to `events.log`. |
| `-x {yes,no,fs}` | `--exifOnly` | How to handle files without EXIF: `yes` (default, skip them) / `no` (process, fall back to filesystem date) / `fs` (only process files without EXIF, using filesystem date). |
| `-d` | `--dryrun`             | Simulate; never touch files. |
| `-D MODE` | `--duplicate-handling` | `skip` / `overwrite` / `rename` / `content` / `interactive` / `redirect`. See [duplicate-handling.md](duplicate-handling.md). |
| `-N` | `--no-comprehensive-check` | Skip SHA-256 checking; filename-only conflicts. Faster on huge target trees. |
| `-R DIR` | `--redirect-dir`       | Directory for redirected duplicates [default: `Duplicates`]. |
| `-K WORD` | `--duplicate-keyword` | Keyword inserted into duplicate filenames [default: `duplicate`]. |
| `-C DIR` | `--cache-dir`          | Where to put `.orgphoto_cache.db`. Default: target dir. Useful when target is on slow storage. |
| `-B` | `--benchmark`          | Print hash cache build timing and hit rate to stdout. |
| `-O` | `--cache-only`         | Build/refresh the hash cache and exit — no copy or move. See [performance.md](performance.md#scheduled-cache-refresh). Incompatible with `-m`/`-c`/`-d`/`-N`. |
|      | `--no-fast-exif`       | Disable exifread; route all files through hachoir. |
|      | `--examples`           | Print usage examples and exit. |
|      | `--version`            | Print version and exit. |

## Defaults at a glance

- No `-m` / `-c` / `-O` → prompts for dry-run confirmation.
- No `-j` → all file types processed.
- `-x yes` → skip files without EXIF.
- `-D skip` → safest duplicate handling.
- Comprehensive SHA-256 checking is **on by default**; disable with `-N` only for very large targets where you don't need content-based dedup.
- Fast EXIF via exifread is **on by default**; disable with `--no-fast-exif` only if exifread misbehaves on your files.

## See also

- [usage-examples.md](usage-examples.md) — 30+ worked examples.
- [duplicate-handling.md](duplicate-handling.md) — every `-D MODE` explained.
- [performance.md](performance.md) — when to use `-N`, `-O`, `-C`, and `-B`.

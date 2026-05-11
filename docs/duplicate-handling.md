# Duplicate Handling

orgphoto detects duplicates two ways:

1. **By filename** — same name in the same date directory.
2. **By content** — same SHA-256 hash anywhere in the target tree (comprehensive checking; on by default, disable with `-N`).

The `-D MODE` flag controls what happens when a duplicate is detected. All modes respect v2.0's [intelligent master file selection](master-selection.md).

---

## Modes

### `-D skip` *(default)*
Skip the incoming file if its filename exists **or** if its content is found anywhere in the target tree.

- **Use case**: safest option; never produce duplicates.
- **Performance**: medium — requires comprehensive SHA-256 checking.

```bash
uv run op.py -c -D skip -j jpg source/ target/
```

### `-D content`
Skip if identical content already exists; rename if the filename conflicts but content differs.

- Content identical → skip ("skipped - identical content").
- Filename conflict, different content → rename with `-K` suffix.
- **Use case**: preserve every unique image while avoiding true content duplicates.

```bash
uv run op.py -c -D content -j jpg source/ target/
# photo.jpg with same content → skipped
# photo.jpg with different content → photo_duplicate.jpg
```

### `-D rename`
Always rename duplicates. Never skip, never overwrite.

- First conflict → `<name>_duplicate.<ext>` (or custom keyword via `-K`).
- Multiple → incremental: `_duplicate_001`, `_duplicate_002`, etc.
- **Use case**: preserve every file unconditionally.

```bash
uv run op.py -c -D rename -K backup -j jpg source/ target/
# photo.jpg → photo_backup.jpg → photo_backup_001.jpg
```

### `-D overwrite`
Replace existing files without confirmation.

- ⚠️ **Data loss possible** — existing files are replaced.
- Still honors master protection: a master file is **never** overwritten even in this mode (the incoming file gets renamed instead).
- **Use case**: only when you're certain the incoming files are authoritative.

```bash
uv run op.py -c -D overwrite -j jpg source/ target/
```

### `-D interactive`
Prompt for each conflict with full context.

Shown to the user:
- Source path, target path
- Filename conflict location(s)
- Content duplicate location(s)
- File sizes and dates

Options: **s**kip, **o**verwrite, **r**ename, **R**edirect.

```bash
uv run op.py -c -D interactive -v -j jpg source/ target/
```

Example prompt:
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

### `-D redirect`
Move duplicates to a separate directory (default: `<target>/Duplicates/`).

- The redirect dir mirrors the date-based layout of the main target.
- Custom path via `-R DIR` (relative to target, or absolute).
- Custom keyword via `-K WORD`.

```bash
uv run op.py -c -D redirect -j jpg source/ target/
# Creates: target/Duplicates/YYYY_MM_DD/photo_duplicate.jpg
```

---

## Redirect mode details

When `-D redirect` is active, the duplicate flow becomes:

1. Detect duplicate (filename or content).
2. Determine master via [master selection](master-selection.md).
3. Move the non-master into the redirect directory.
4. Maintain the `YYYY_MM_DD/` subdirectory layout inside the redirect dir.
5. Apply the duplicate keyword: `<name>_duplicate.<ext>`, incremental suffixes if collisions.

### Layout

```
target/
├── 2023_01_01/
│   ├── photo1.jpg
│   └── photo2.jpg
├── 2023_01_02/
│   └── photo3.jpg
└── Duplicates/
    ├── 2023_01_01/
    │   ├── photo1_duplicate.jpg
    │   └── photo1_duplicate_001.jpg
    └── 2023_01_02/
        └── photo3_copy.jpg
```

### `-R` examples

```bash
# Relative — under the target dir
uv run op.py -c -D redirect -R Archive/Duplicates ...
# → target/Archive/Duplicates/YYYY_MM_DD/...

# Absolute — anywhere on the filesystem
uv run op.py -c -D redirect -R /backup/duplicates ...
# → /backup/duplicates/YYYY_MM_DD/...
```

### `-K` examples

```bash
uv run op.py -c -D redirect -K copy ...
# → photo_copy.jpg

uv run op.py -c -D redirect -K version ...
# → photo_version.jpg
```

---

## Comprehensive duplicate detection (SHA-256)

By default, orgphoto **hashes every existing file in the target tree** at startup and checks each incoming file against the resulting in-memory map. This catches content duplicates regardless of filename.

The hash cache is persistent (`.orgphoto_cache.db` in the target dir), validated via mtime+size on each run. Unchanged files are skipped — only new or modified files get rehashed. See [performance.md](performance.md) for details and tuning.

### What gets checked

| Aspect | Result |
|--------|--------|
| Same SHA-256 hash, any filename, anywhere in target | **Content duplicate** |
| Same filename, same date directory, any content | **Filename conflict** |
| Both at the same time | Both detected; mode decides outcome |

### Disabling

```bash
uv run op.py -c -N -D rename ...
```

`-N` / `--no-comprehensive-check` skips the hash-cache build entirely. Useful when:
- The target has **>50,000 files** and you don't need content-based dedup.
- Target is on a slow network share where reading all files is impractical.
- You only care about filename conflicts.

In `-N` mode, the modes `skip`, `content`, and `overwrite` fall back to filename-only behavior. `rename` and `redirect` work identically with or without `-N`.

---

## Mode × master selection cheat sheet

When duplicates are detected, [master selection](master-selection.md) picks the "best" file from {incoming, existing}. The chosen mode then dictates how the non-master is handled:

| Mode | Master is *existing* | Master is *incoming* |
|------|---------------------|----------------------|
| `skip` | Skip incoming | Demote existing, place incoming |
| `overwrite` | **Protect master** — rename incoming | Demote existing, place incoming |
| `rename` | Rename incoming | Demote existing, place incoming |
| `content` | Check content first, then act | Demote existing if different |
| `interactive` | Master indicated in prompt | Demote existing with confirmation |
| `redirect` | Redirect incoming | Demote existing into redirect dir |

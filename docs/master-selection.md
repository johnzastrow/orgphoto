# Intelligent Master File Selection (v2.0.0+)

When duplicates are detected, orgphoto automatically decides which file should be the "master" (definitive version). The non-master is then handled according to the active [`-D MODE`](duplicate-handling.md).

This system is **always on**. No configuration. No flag to opt in.

---

## How it decides

orgphoto evaluates the incoming file against every conflicting existing file using a three-tier priority:

### Priority 1 — No duplicate keywords (highest)

Files **without** common duplicate markers in their filename are preferred.

Detected keywords:
- English: `copy`, `duplicate`, `version`, `backup`, `alt`, `alternative`
- Other languages: `copie` (fr), `kopie` (de), `copia` (es/it)
- Numbered patterns at end: `(1)`, `(2)`, `_copy_1`, `_duplicate_001`, ` 2`

Examples:
```
photo.jpg             → no keywords (score: 0) ✓ best
photo_copy.jpg        → "copy"      (score: 1)
vacation (1).jpg      → "(1)"       (score: 1)
sunset_duplicate.jpg  → "duplicate" (score: 1)
```

### Priority 2 — Shortest filename

Among files with the same keyword score, the shorter name wins. Originals tend to have shorter, terser names than their derivatives.

```
photo.jpg                    → length 9  ✓ best
photo_edited.jpg             → length 16
photo_edited_final.jpg       → length 22
```

### Priority 3 — Oldest creation/modification date

If keyword status and name length tie, the older file wins. First-created tends to be the original.

```
photo.jpg @ 2023-01-15 10:30  → ✓ best (oldest)
photo.jpg @ 2023-01-15 11:45
photo.jpg @ 2023-01-16 09:00
```

---

## What happens to the non-master

### When the incoming file is master

1. The existing file is **demoted** per the active `-D MODE`:
   - `-D skip` → still skipped (existing remains in place)
   - `-D rename` → existing renamed with `_<keyword>` suffix
   - `-D redirect` → existing moved into the redirect dir
   - `-D content` → demoted only if content differs
   - `-D interactive` → user confirms demotion
   - `-D overwrite` → existing replaced
2. The incoming file takes the primary position.
3. The log records this as `[PROMOTED TO MASTER]`.

```
MASTER SELECTION: Chose photo.jpg as master (incoming)
  Criteria: has_dup_keywords=False, name_length=9, date=2023-01-15 10:30:00
  Non-masters (1): ['photo_copy.jpg']
MASTER PROMOTION: Incoming file photo.jpg is the better master
  DEMOTION: photo_copy.jpg will be moved to duplicate location
  DEMOTED: photo_copy.jpg -> Duplicates/photo_copy_duplicate.jpg
```

### When the existing file is master

1. The existing file is **protected** — never overwritten, never renamed, even in `-D overwrite` mode.
2. The incoming file follows the active duplicate mode for non-masters:
   - `-D skip` → incoming skipped
   - `-D rename` → incoming renamed
   - `-D redirect` → incoming redirected
   - `-D overwrite` → incoming renamed (master takes priority over the mode!)
3. The log records this as `[SKIPPED - not master]` or similar.

```
MASTER SELECTION: Chose photo.jpg as master (existing)
  Criteria: has_dup_keywords=False, name_length=9, date=2023-01-15 10:30:00
  Non-masters (1): ['photo copy.jpg']
MASTER RETAINED: Existing file photo.jpg remains as master
  photo copy.jpg -> skipped - existing file is better master
```

---

## Real-world scenarios

### Consolidating multiple archives

```
archive1/vacation.jpg
archive2/vacation_copy.jpg
archive3/vacation (1).jpg
```

→ Master: `vacation.jpg` (no keywords). Others demoted to
`vacation_copy_duplicate.jpg`, `vacation (1)_duplicate.jpg`.

### Mobile import vs computer backup

```
Phone:          IMG_1234.jpg      (original)
Computer backup: IMG_1234 (1).jpg (duplicate)
```

→ Master: `IMG_1234.jpg`. Backup version automatically demoted.

### High-quality original vs compressed copy

```
photo.jpg            (5 MB, 2023-01-15)
photo_compressed.jpg (1 MB, 2023-01-16)
```

→ Master: `photo.jpg` (shorter name, older date). Compressed copy demoted.
Note: orgphoto picks based on **filename / date**, not file size or image quality.

---

## What it doesn't do

- It does **not** inspect EXIF camera settings, image dimensions, or codec quality.
- It does **not** open files to compare image content (beyond the SHA-256 hash used to detect identical content).
- It does **not** delete files. Demoted files are moved/renamed; never deleted.

If filename-and-date heuristics aren't enough, use `-D interactive` to make the call manually per file.

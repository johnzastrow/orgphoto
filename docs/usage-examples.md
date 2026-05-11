# Usage Examples

All examples assume you've cloned the repo and have `uv` installed. Substitute `python op.py` if you prefer plain pip / venv, or `op.exe` for the prebuilt Windows binary.

## Basic Operations

1. Process ALL file types (default — no extension filter):
   ```bash
   uv run op.py -c Z:\photosync target/
   ```

2. Move JPG files only:
   ```bash
   uv run op.py -m -j jpg Z:\photosync target/
   ```

3. Copy various types, using filesystem date if EXIF is missing:
   ```bash
   uv run op.py -c -x no -j gif,png,jpg,mov,mp4 Z:\photosync target/
   ```

4. Dry run — simulate moving files without changes:
   ```bash
   uv run op.py -m -d -j jpg Z:\photosync target/
   ```

5. Process only files **without** EXIF data (using filesystem date):
   ```bash
   uv run op.py -c -x fs -j jpg Z:\photosync target/
   ```

6. Move PNG and JPEG files with verbose logging:
   ```bash
   uv run op.py -m -v -j png,jpeg Z:\photosync target/
   ```

## Comprehensive Duplicate Detection

7. Content-based detection (skip identical, rename different):
   ```bash
   uv run op.py -c -D content -j jpg Z:\photosync target/
   ```
   *Compares SHA-256 hashes to detect truly identical files regardless of filename.*

8. Content-based with custom keyword:
   ```bash
   uv run op.py -c -D content -K version -j jpg Z:\photosync target/
   ```
   *Different content with same filename → `photo_version.jpg`.*

## Interactive Mode

9. Prompt user for each conflict:
   ```bash
   uv run op.py -m -D interactive -j jpg Z:\photosync target/
   ```

10. Interactive with verbose context:
    ```bash
    uv run op.py -m -D interactive -v -j jpg,png,heic Z:\photosync target/
    ```

## Renaming Duplicates

11. Always rename duplicates:
    ```bash
    uv run op.py -c -D rename -j jpg Z:\photosync target/
    ```
    *Generates: `photo.jpg` → `photo_duplicate.jpg` → `photo_duplicate_001.jpg`.*

12. Rename with custom keyword:
    ```bash
    uv run op.py -c -D rename -K copy -j jpg Z:\photosync target/
    ```

## Redirect Duplicates

13. Redirect to separate directory:
    ```bash
    uv run op.py -c -D redirect -j jpg Z:\photosync target/
    ```
    *Creates `target/Duplicates/YYYY_MM_DD/filename_duplicate.jpg`.*

14. Custom directory and keyword:
    ```bash
    uv run op.py -c -D redirect -R MyDuplicates -K copy -j jpg Z:\photosync target/
    ```

15. Absolute path:
    ```bash
    uv run op.py -c -D redirect -R /backup/duplicates -j jpg Z:\photosync target/
    ```

16. Dry run preview of redirect:
    ```bash
    uv run op.py -c -d -D redirect -R TestDupes -j jpg Z:\photosync target/
    ```

## Overwrite Mode

17. Overwrite all duplicates (data-loss warning):
    ```bash
    uv run op.py -m -D overwrite -j jpg Z:\photosync target/
    ```

18. Overwrite with verbose logging for an audit trail:
    ```bash
    uv run op.py -c -v -D overwrite -j jpg,png Z:\photosync target/
    ```

## Cache-Only Mode (v2.2.0+)

Use `-O` to refresh the hash cache without copying. The next real copy job starts with a warm cache. See [performance.md](performance.md#scheduled-cache-refresh) for cron / Task Scheduler examples.

19. Refresh cache for a backup tree:
    ```bash
    uv run op.py -O -B /backups/photos
    ```

20. Custom cache location:
    ```bash
    uv run op.py -O -C /fast_ssd/cache /backups/photos
    ```

## Performance Optimization

21. Disable comprehensive checking for huge target trees:
    ```bash
    uv run op.py -c -N -j jpg Z:\photosync target/
    ```

22. Fastest mode — disable comprehensive + rename:
    ```bash
    uv run op.py -c -N -D rename -j jpg Z:\photosync target/
    ```

23. Performance mode with redirect:
    ```bash
    uv run op.py -c -N -D redirect -R FastDupes -j jpg Z:\photosync target/
    ```

## Advanced Combinations

24. Content detection with verbose logging:
    ```bash
    uv run op.py -m -v -D content -j png,jpeg Z:\photosync target/
    ```

25. Files without EXIF, redirect duplicates:
    ```bash
    uv run op.py -c -x fs -D redirect -R DuplicatesNoExif -j jpg Z:\photosync target/
    ```

26. Multi-format with custom keyword:
    ```bash
    uv run op.py -c -x no -D content -K backup -j jpg,png,gif,heic,mov,mp4 Z:\photosync target/
    ```

27. Maximum safety (comprehensive + interactive):
    ```bash
    uv run op.py -c -D interactive -v -j jpg,png,heic,mov Z:\photosync target/
    ```

## Real-World Scenarios

28. Mobile import with comprehensive dedup:
    ```bash
    uv run op.py -c -x no -D content -j jpg,png,heic,mov /sdcard/DCIM target/photos/
    ```

29. Archive consolidation with redirect:
    ```bash
    uv run op.py -c -D redirect -R Archive/Duplicates -j jpg,png,gif,tiff old_archive/ consolidated/
    ```

30. Large library, performance-optimized:
    ```bash
    uv run op.py -c -N -D rename -K alt -j jpg,png,heic source/ target/
    ```

31. Cautious migration with dry-run + interactive:
    ```bash
    uv run op.py -d -D interactive -v -j jpg,png,heic,mov source/ target/
    ```

## Short flag reference

- `-m` move • `-c` copy • `-d` dry run • `-v` verbose
- `-j` extensions • `-x` EXIF handling
- `-D` duplicate handling • `-N` disable comprehensive check
- `-R` redirect directory • `-K` duplicate keyword
- `-C` cache directory • `-B` benchmark timing
- `-O` cache-only mode (v2.2.0+)

See [usage.md](usage.md) for the full flag table.

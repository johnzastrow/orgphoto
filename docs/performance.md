# Performance

This page covers cache tuning, when to disable comprehensive checking, and how to schedule cache refresh as a maintenance job for very large libraries.

---

## How the persistent hash cache works (v2.1.0+)

orgphoto stores SHA-256 hashes for every file in the target tree in a SQLite database (`.orgphoto_cache.db`, in the target dir by default). Each row records:

```
(file_path, file_hash, file_size, file_mtime)
```

On every subsequent run, orgphoto:
1. Walks the target tree.
2. For each file, compares its current `(size, mtime)` to the cached row.
3. If both match → reuses the cached hash (no I/O for the file content).
4. If either differs → rehashes the file and updates the row.
5. After the walk, removes rows for files that no longer exist on disk.

Result: a 200,000-file backup tree where 99.9% of files haven't changed since the previous run costs only one `stat()` call per file — seconds, not hours.

---

## Performance characteristics

### Cache build time

| Target Files | First run (full hash) | Subsequent runs (cached) | Memory |
|--------------|----------------------|--------------------------|--------|
| 1,000        | 2-5 seconds          | < 0.5 seconds            | ~300 KB |
| 10,000       | 20-60 seconds        | < 1 second               | ~3 MB |
| 50,000       | 2-5 minutes          | 1-3 seconds              | ~15 MB |
| 100,000      | 5-15 minutes         | 3-8 seconds              | ~30 MB |
| 200,000      | 10-30 minutes        | 5-15 seconds             | ~60 MB |

Numbers vary with storage type (SSD vs HDD vs network share) and CPU. Use `-B` to measure your actual values.

### Sample `-B` output

```
$ uv run op.py -c -B -j jpg source/ target/
Building hash cache of target directory...
  Hash cache ready: 15432 files (15431 cached, 1 hashed) in 0.8s

--- Hash Cache Benchmark ---
Total files indexed : 15432
Reused from cache   : 15431
Freshly hashed      : 1
Stale entries purged: 0
Elapsed time        : 0.823s
Cache hit rate      : 100.0%
----------------------------
```

### Measured throughput (real-world)

Datapoints from actual `-O -B` runs to help calibrate the estimates table:

**NVMe SSD, 2,623-file library** (`C:\DupesfromOP`, mixed images, Windows):

```
# First run — full hash
> op -O -B C:\DupesfromOP
  Hash cache ready: 2623 files (0 cached, 2623 hashed) in 51.5s
  → ~51 files/sec (cold hash)

# Second run — warm cache
> op -O -B C:\DupesfromOP
  Hash cache ready: 2623 files (2622 cached, 1 hashed) in 0.4s
  Cache hit rate      : 100.0%
  → ~6,400 files/sec (stat-only, no content reads)
```

**Spinning HDD, 166k-file library** (`E:\Pictures`):

```
# First run — full cold hash
> op -O -B E:\Pictures
Building hash cache of target directory...
  Hash cache ready: 166285 files (0 cached, 166285 hashed) in 14365.1s
  Elapsed time        : 14365.141s
  → ~11.6 files/sec averaged across the full run (~4 hours total)

# Second run — warm cache (1 new file added since cold build)
> op -O -B E:\Pictures
Building hash cache of target directory...
  Hash cache ready: 166286 files (166284 cached, 2 hashed) in 28.9s
  Cache hit rate      : 100.0%
  → ~5,750 files/sec (stat-only walk)
```

Takeaways:
- **HDD is ~4-5× slower than NVMe for cold hashing** (~12 vs ~51 files/sec on the test boxes above). A 166k-file first build took ~4 hours on HDD; an equivalent NVMe build would run closer to ~1 hour.
- **Early-scan throughput overstates the full-run average.** A mid-scan checkpoint on this same HDD showed ~22 files/sec at 6000 files, but the full run averaged ~11.6 files/sec — large media files later in the tree (and seek pressure on a heavily-populated HDD) drag the steady-state rate down. Plan from the full-run number, not the early progress line.
- **Warm-cache walks are ~495× faster than cold builds on HDD** (~5,750 vs ~11.6 files/sec), and ~125× faster on NVMe. Once the cache is hot, throughput is dominated by directory traversal and `stat()` rather than reading file contents, so even huge HDD trees refresh in ~30 seconds — nearly closing the gap with NVMe (~6,400 files/sec warm).
- On warm-cache runs you may see a small number of `freshly hashed` files — those are real files whose mtime drifted since the last run (e.g., a fresh import), not the cache DB itself (which is excluded from the walk).

### Storage cost

- `.orgphoto_cache.db`: ~200-400 bytes per file (relative path + hash + size + mtime). 200k files ≈ 40-80 MB DB.
- In-memory: ~200-300 bytes per file for the hash lookup map.

---

## Crash safety (v2.2.1+)

The cache build commits to SQLite every 1000 freshly-hashed files (`TargetHashCache._COMMIT_BATCH_SIZE`). If a multi-hour build is interrupted — Ctrl-C, power loss, OOM kill — only the last partial batch is lost. The next run picks up exactly where the previous one died via the existing mtime+size cache-hit logic.

No special "resume" flag needed; just re-run the same command.

---

## When to use `-C` (custom cache directory)

By default, `.orgphoto_cache.db` lives in the target directory. Move it elsewhere with `-C DIR` when:

- Target is on a slow drive (HDD, NAS, network share) and you have a fast local SSD.
- Target is read-only or you don't want to pollute it with metadata.
- You want to share one cache across multiple invocations targeting the same tree from different working directories.

```bash
uv run op.py -c -C /fast_ssd/cache -j jpg /slow_hdd/photos/ target/
```

Caveat: the cache is keyed by relative POSIX path under the target, so moving the cache **between targets** is meaningless — it'll just rebuild.

---

## When to use `-N` (disable comprehensive checking)

`-N` / `--no-comprehensive-check` skips the entire hash-cache build. orgphoto then only detects duplicates by filename. Use when:

- Target has > 50,000 files **and** you don't need content-based dedup (e.g., importing into an already-deduplicated archive).
- Target is on a network share where reading every file is impractical and no local cache is feasible.
- You're optimizing for a one-shot batch with `-D rename` or `-D redirect`, where content equality doesn't matter.

```bash
# Maximum-speed bulk import; only filename conflicts caught
uv run op.py -c -N -D rename -j jpg source/ target/
```

`-N` skips creating the `.orgphoto_cache.db` entirely; it does NOT respect or invalidate an existing one — that DB is simply ignored for that run.

---

## Scheduled cache refresh (v2.2.0+)

For very large backup trees, you can split the cache build out of the copy job entirely. Run `-O` / `--cache-only` on a schedule so that real copy jobs always find a warm cache.

```bash
uv run op.py -O -B /backups/photos
```

The output reports the same stats as `-B` mode. No copy or move work happens — orgphoto just walks the target, refreshes the SQLite DB, and exits.

### Linux cron

```cron
# Nightly cache refresh at 02:00
0 2 * * * cd /opt/orgphoto && uv run op.py --cache-only /backups/photos >> /var/log/orgphoto-cache.log 2>&1
```

### Windows Task Scheduler

```
Program/script:  op.exe
Arguments:       --cache-only D:\Backups\Photos
Start in:        C:\Tools\orgphoto
```

### Combining with `-C`

```bash
uv run op.py -O -C /fast_ssd/cache /backups/photos
```

Cache DB lives on the SSD; photos stay on the HDD. The refresh job still has to stat every file on the HDD, but most reads hit the cache after the first run.

### Flag interactions

`-O` is **incompatible** with `-m`/`-c`/`-d`/`-N` — they all imply doing copy work, which `-O` explicitly skips.

`-O` honors `-C`, `-B`, `-v` exactly like a normal run.

If you pass both `SOURCE_DIR` and `DEST_DIR` to `-O`, `DEST_DIR` wins as the target and `SOURCE_DIR` is ignored with a stderr warning. This lets a cron entry reuse the same positional layout as a copy job.

---

## Mode performance comparison

| Mode | Requires comprehensive | Speed | Memory | Safety |
|------|----------------------|-------|--------|--------|
| `skip` | Yes (default) | Medium | High | Maximum |
| `content` | Yes (recommended) | Medium | High | Maximum |
| `interactive` | Yes (optional) | Slow* | High | Maximum |
| `rename` | No (optional) | Fast | Low | High |
| `redirect` | No (optional) | Fast | Low | High |
| `overwrite` | No (optional) | Fastest | Low | Minimal |

*interactive speed depends on user response time

---

## Real-world tips

1. **Initial import**: first run builds the hash cache (slower); all subsequent runs reuse it (fast).
2. **Regular sync**: persistent cache means comprehensive checking is fast even for frequent runs against the same target.
3. **Archive consolidation**: use `-D content` for merging archives — preserves unique content while collapsing duplicates.
4. **Mobile import**: stick with defaults for safety.
5. **Bulk processing**: `-N -D rename` is the fastest combination if you don't need dedup.
6. **Migration projects**: `-D interactive` for full control.
7. **Slow target drive, fast workstation**: `-C /fast_ssd/cache` puts the DB where I/O is cheap.
8. **Verify speedup**: use `-B` to see the cache hit rate. Should approach 100% after the first run.
9. **Very large libraries (100k+ files)**: schedule `op.py -O TARGET` nightly. Copy jobs then start with a fully-warm cache and complete in seconds plus actual copy time.

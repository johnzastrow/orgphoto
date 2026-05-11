# Supported File Formats

orgphoto uses two libraries for metadata extraction:

| Library | Role | When |
|---------|------|------|
| **exifread** | Fast EXIF reader (header-only, 5-50× faster than hachoir) | Default for all image/RAW formats listed below |
| **hachoir**  | Full file parser | Fallback for video/audio, or whenever exifread fails or `--no-fast-exif` is set |

If a file's extension matches the exifread list, orgphoto tries exifread first and falls back to hachoir on failure. Anything else routes straight to hachoir.

---

## Routed through exifread *(fast path)*

| Extension | Format |
|-----------|--------|
| `.jpg`, `.jpeg` | JPEG |
| `.tif`, `.tiff` | TIFF |
| `.png` | Portable Network Graphics |
| `.webp` | WebP |
| `.heic`, `.heif` | HEIF / iPhone photos *(hachoir does **not** support these)* |
| `.cr2`, `.cr3` | Canon RAW *(hachoir does **not** support these)* |
| `.nef` | Nikon RAW *(hachoir does **not** support these)* |
| `.arw` | Sony RAW |
| `.dng` | Adobe Digital Negative |
| `.orf` | Olympus RAW |
| `.rw2` | Panasonic RAW |
| `.raf` | Fujifilm RAW |
| `.pef` | Pentax RAW |
| `.srw` | Samsung RAW |

To force hachoir for these too, pass `--no-fast-exif`.

---

## Routed through hachoir

[hachoir 3.3.0 supports 33 formats](https://hachoir.readthedocs.io/en/latest/metadata.html#supported-file-formats):

### Archive
bzip2, cab, gzip, mar, tar, zip

### Audio
aiff, mpeg_audio (MP3), real_audio (.ra), sun_next_snd

### Container
matroska, ogg, real_media (.rm), riff

### Image
bmp, gif, ico, jpeg, pcx, png, psd, targa (TGA), tiff, wmf, xcf

### Misc
ole2 (MS Office), pcf (X11 font), torrent, ttf (TrueType)

### Program
exe (MS Windows PE)

### Video
asf (WMV/WMA), flv, mov (QuickTime), mpeg_ts (.ts), mpeg_video, mp4

---

## How orgphoto picks a date

For each file:

1. Try the fast/full EXIF reader for the extension (above).
2. If a `DateTimeOriginal` / `DateTime` / equivalent EXIF tag is found → use it.
3. Else:
   - `-x yes` (default): skip the file.
   - `-x no`: fall back to the filesystem modification date.
   - `-x fs`: only process files that **lack** EXIF, using filesystem date.

See [usage.md](usage.md) for the full `-x` semantics.

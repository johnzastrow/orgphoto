# Installation

orgphoto is a single Python script (`op.py`) plus two runtime dependencies (`hachoir`, `exifread`). Python **3.13 or newer** is required.

## Option 1 — uv *(recommended)*

`uv` handles dependency resolution and virtual environments automatically:

```bash
# Install uv: https://docs.astral.sh/uv/getting-started/installation/

git clone https://github.com/johnzastrow/orgphoto.git
cd orgphoto
uv sync                 # one-time setup; reads pyproject.toml + uv.lock
uv run op.py --version  # confirm it works
```

From then on, every invocation is just:

```bash
uv run op.py [options] SOURCE_DIR DEST_DIR
```

## Option 2 — pip + venv

```bash
git clone https://github.com/johnzastrow/orgphoto.git
cd orgphoto
python -m venv .venv
source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install hachoir exifread
python op.py --version
```

## Option 3 — prebuilt Windows .exe

Grab the latest `op.exe` from the [GitHub Releases page](https://github.com/johnzastrow/orgphoto/releases). No Python install required.

```bat
op.exe --version
op.exe [options] SOURCE_DIR DEST_DIR
```

Every push to `main` also publishes a fresh `op.exe` as a workflow artifact (kept 30 days). See [building.md](building.md) for details on the CI build.

## Verifying the install

A quick sanity check that everything is wired up:

```bash
uv run op.py --version       # should print "op.py 2.2.x"
uv run op.py --examples      # built-in example list
uv run op.py --help          # full flag reference
```

## Requirements summary

| Component | Version | Notes |
|-----------|---------|-------|
| Python    | 3.13+   | pinned in `.python-version` and `pyproject.toml` |
| hachoir   | 3.3.0+  | metadata extraction for video/audio/misc |
| exifread  | 3.5.1+  | fast EXIF for JPEG/TIFF/HEIC/RAW |
| ruff      | 0.15+   | dev-only — linter/formatter |
| pytest    | 9.0+    | dev-only — test runner |
| pyinstaller | 6.20+ | dev-only — Windows `.exe` build |

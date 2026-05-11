# Building the Windows .exe

orgphoto ships a single-file Windows executable built with PyInstaller. Two paths:

## CI: GitHub Actions *(recommended — zero local setup)*

`.github/workflows/build.yml` produces `op.exe` automatically:

| Trigger | What happens |
|---------|--------------|
| Push to `main` | Tests run on Linux + Windows; `op.exe` built and uploaded as artifact (30-day retention). |
| PR to `main` | Same as push, on the PR branch. |
| Tag matching `v*` | Same as push, **plus** a GitHub Release is created/updated with `op.exe` attached and auto-generated release notes. |
| Manual via "Run workflow" | Same as push. |

### Grabbing the artifact

Via the GitHub UI: **Actions → latest "Build" run → Artifacts → `op-windows-<sha>`**.

Via the `gh` CLI:

```bash
# Latest commit on the current branch
gh run download --name "op-windows-$(git rev-parse HEAD)" --dir .
```

### Tagging a release

```bash
git tag v2.2.3 -m "release notes here"
git push origin v2.2.3
# Workflow runs; release appears at:
# https://github.com/johnzastrow/orgphoto/releases/tag/v2.2.3
```

The release ships with `op.exe` attached and auto-generated notes from commits since the previous tag. Edit the notes manually if you want richer copy.

---

## Local build (Windows host required)

PyInstaller does not cross-compile. To build the `.exe` locally you need a Windows machine (or a Windows VM).

```bat
git clone https://github.com/johnzastrow/orgphoto.git
cd orgphoto
uv sync
uv run pyinstaller --noconfirm --onefile --console ^
  --collect-all hachoir --collect-all exifread ^
  --icon "doc/favicon.ico" "op.py"
```

Output: `dist\op.exe`.

### Why `uv run pyinstaller`?

- **Dependency resolution**: `uv run` executes PyInstaller inside the project's virtual environment where `hachoir` and `exifread` are installed.
- **Module discovery**: `--collect-all hachoir` and `--collect-all exifread` instruct PyInstaller to bundle every submodule and data file from those packages — necessary because they use dynamic imports.
- **Reliability**: avoids `ModuleNotFoundError` at runtime that bare `pyinstaller op.py` would produce.

### Alternative: use the bundled spec file

`op.spec` records the exact invocation used by CI. If you don't want to remember the flags:

```bat
uv run pyinstaller op.spec
```

---

## Smoke test the build

After either CI or local build, verify the binary on Windows:

```bat
dist\op.exe --version
dist\op.exe --help
dist\op.exe -O -B C:\some\target\folder
```

The CI workflow runs the first two automatically; if either fails, the workflow fails.

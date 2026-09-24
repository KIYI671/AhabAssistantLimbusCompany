## Build Guide

## Configuring the python environment

Dependencies on python version 3.12

See [requirements.txt](/requirements.txt) for python library dependencies.

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller
```

## One-shot packaging (recommended, this is what CI uses)

```bash
uv run python ./scripts/build.py --version Vx.x.x
```

The script produces the release archive for the current platform:

- Windows: `dist/AALC_<version>.7z`, containing `AALC/` (including `AALC Updater.exe`)
- macOS: `dist/AALC_<version>_macos_<arch>.zip`, containing `AALC.app` (<arch> is `arm64` or `x86_64`)

## Build executables

### Windows

```bash
pyinstaller main.spec
```

### macOS

PyInstaller cannot cross-compile: the macOS build has to run on macOS.

```bash
pyinstaller main_mac.spec
```

After `dist/AALC.app` is produced, the remaining packaging steps are the ones `scripts/build.py` performs:

1. Copy `README.md`, `LICENSE` and `assets/` into `AALC.app/Contents/MacOS/` (that directory is the runtime working directory), compile `i18n/*.qm` with `pyside6-lrelease`, and write the version into `assets/config/version.txt`.
2. Re-sign the bundle: adding files to the bundle invalidates the ad-hoc signature that PyInstaller writes, and the Accessibility / Screen Recording grants are recorded per signature:
   `codesign --force --deep --sign - dist/AALC.app`
3. Archive with `ditto` (`zip` breaks the symlinks inside a `.app`):
   `ditto -c -k --sequesterRsrc --keepParent AALC.app AALC_<version>_macos_$(uname -m).zip`

The macOS build is unsigned and not notarized, so Gatekeeper blocks the first launch; users run `xattr -cr /Applications/AALC.app` once, as described in the README.

The packaged app keeps its runtime data in `~/Library/Application Support/AALC` (see `utils/app_data_dir.py`): the bundle only holds read-only resources, while configuration, logs and image resources live in the data directory. Replacing `AALC.app` to upgrade therefore keeps user settings, and the app never writes inside the bundle (that would invalidate the signature seal and make the system permissions expire).

## Add other subsidiary documents

```bash
mkdir dist_release
mv dist/* dist_release/
cp -r 3rdparty dist_release/AALC/
cp -r assets dist_release/AALC/
cp LICENSE dist_release/AALC/
cp README.md dist_release/AALC/
```

## Build Guide

## Configuring the python environment

Dependencies on python version 3.12

See [requirements.txt](/requirements.txt) for python library dependencies.

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller
```

## Build executables

```bash
python scripts/build.py --version 1.0.9
```

By default, the build creates a runnable `dist/AALC` directory with the application, updater, libraries, assets, and translations, without compressing a release archive. Run `dist/AALC/AALC` on Linux or `dist/AALC/AALC.exe` on Windows. Keep the entire `dist/AALC` directory when running or copying the application.

Use `--version` to set the build version; it defaults to `dev` when omitted.

GitHub Actions builds also create a release archive by default to support the existing release workflow.

## Create a release archive

```bash
python scripts/build.py --version 1.0.9 --package
```

With `--package`, the completed build is also compressed into `dist/AALC_<version>.7z` on Windows or `dist/AALC_<version>_linux.7z` on Linux. If neither `7z` nor `7zz` is available, the script creates a `.tar.gz` archive instead.

## Build Guide

## Configuring the python environment

Dependencies on python version 3.12.1

See [requirements.txt](requirements.txt) for python library dependencies.

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller
```

## Build executables

```bash
pyinstaller main.spec
```

## Add other subsidiary documents

```bash
mkdir dist_release
mv dist/* dist_release/
cp -r 3rdparty dist_release/AALC/
cp -r pic dist_release/AALC/
cp config.yaml dist_release/AALC/
cp black_list_keyword.yaml dist_release/AALC/
cp LICENSE dist_release/AALC/
cp README.md dist_release/AALC/
```

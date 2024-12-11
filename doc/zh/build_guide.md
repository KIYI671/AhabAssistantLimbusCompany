# 构建指南

## 配置python环境

依赖python3.12.1版本

python库依赖见[requirements.txt](requirements.txt)

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller
```

## 构建可执行文件

```bash
pyinstaller main.spec
```

## 添加其他附属文件

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
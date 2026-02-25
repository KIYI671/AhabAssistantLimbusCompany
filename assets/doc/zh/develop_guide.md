# 开发指南

## 环境配置

1. **Python 版本**：项目要求 Python 3.12
2. **windows 环境**：目前仅支持在windows环境下开发

### 使用 uv（推荐）

```bash
uv venv --python=3.12
# After activate the env
uv sync
```

### 使用 Conda

```bash
# 创建 Python 3.12 虚拟环境
conda create -n aalc python=3.12
conda activate aalc

# 升级 pip 并安装依赖
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## 启动开发服务器

```bash
# 默认：启用热重载（自动重启 + Ctrl+R）
python main_dev.py

# 仅手动重载：禁用自动热重载，但保留 Ctrl+R
python main_dev.py --no-reload
```

## 开发特性

- **热重载**：
  - 默认：代码修改后自动重新加载
  - `--no-reload`：只在按下 `Ctrl+R` 时才重启
- **快捷键**：
  - `Ctrl+R`：手动触发重载
  - `Ctrl+C`：退出程序
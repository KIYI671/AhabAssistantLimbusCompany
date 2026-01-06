# 开发指南

## 环境配置

1. **Python 版本**：项目要求 Python 3.12
2. **windows 环境**：目前仅支持在windows环境下开发

### 使用 uv（推荐）

```bash
# 等待补充...
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
python main_dev.py
```

## 开发特性

- **热重载**：代码修改后自动重新加载
- **快捷键**：
  - `Ctrl+R`：手动触发重载
  - `Ctrl+C`：退出程序
import subprocess
import sys
from pathlib import Path

# uv export --no-hashes --no-annotate --no-dev --format requirements-txt | Where-Object { -not (($_ -match "darwin" -or $_ -match "linux") -and $_ -match "sys_platform") } > requirements.txt


def main():
    cmd = [
        "uv",
        "export",
        "--no-hashes",  # 不包含package哈希
        "--no-annotate",  # 不包含这个包是由谁引入的注释
        "--no-dev",  # 不包含开发依赖
        "--format",
        "requirements-txt",
    ]

    result = subprocess.run(cmd, text=True, capture_output=True)
    if result.returncode != 0:
        print("uv export failed:", file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        sys.exit(result.returncode)

    filtered = []
    for line in result.stdout.splitlines():
        # 删除 macOS/Linux 独占的依赖（形如 sys_platform == 'linux'/'darwin'）
        # 保留跨平台环境标记（如 sys_platform != 'win32'）
        marker = line.split(";", 1)[1] if ";" in line else ""
        is_platform_exclusive = "sys_platform ==" in marker and ("linux" in marker or "darwin" in marker)
        if not is_platform_exclusive:
            filtered.append(line)

    out_path = Path("requirements.txt")
    out_path.write_text("\n".join(filtered) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

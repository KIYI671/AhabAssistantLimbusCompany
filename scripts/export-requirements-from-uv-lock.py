import subprocess
import sys
from pathlib import Path


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

    # 项目支持 Windows/Linux，保留 Linux 依赖及平台标记，排除 macOS 独占包。
    lines = [line for line in result.stdout.splitlines() if "sys_platform == 'darwin'" not in line.split(";", 1)[-1]]
    out_path = Path("requirements.txt")
    out_path.write_bytes(("\r\n".join(lines) + "\r\n").encode("utf-8"))


if __name__ == "__main__":
    main()

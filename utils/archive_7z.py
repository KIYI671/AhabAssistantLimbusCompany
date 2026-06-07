"""7z 资源包构建与解压工具。"""

from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import sys

# 优先复用项目内置的 7za.exe，避免运行环境额外依赖系统安装的 7-Zip。
SEVEN_ZIP_EXECUTABLE_RELATIVE_PATH = Path("assets/binary/7za.exe")
# 基于 utils 目录反推项目根目录，便于在工作目录变化时稳定定位内置工具。
PROJECT_ROOT = Path(__file__).resolve().parents[1]
# 当内置工具不存在时，按现有 scripts/build.py 的思路回退到系统命令。
SYSTEM_SEVEN_ZIP_COMMAND_CANDIDATES = ("7z", "7za")


def _resolve_7z_executable() -> str:
    """解析当前环境可用的 7z 可执行命令。

    返回:
        可直接传给 subprocess 的 7z 命令或绝对路径字符串。
    """
    candidate_paths: list[Path] = []

    # 第一步：打包版本优先查找 exe 旁边的内置 7za.exe。
    if getattr(sys, "frozen", False):
        candidate_paths.append(Path(sys.executable).resolve().parent / SEVEN_ZIP_EXECUTABLE_RELATIVE_PATH)

    # 第二步：源码运行时回退到仓库内的 assets/binary/7za.exe。
    candidate_paths.append(PROJECT_ROOT / SEVEN_ZIP_EXECUTABLE_RELATIVE_PATH)

    for candidate_path in candidate_paths:
        resolved_path = candidate_path.resolve()
        if resolved_path.is_file():
            return str(resolved_path)

    # 第三步：若项目内置工具不存在，则回退到系统 PATH 中的 7z/7za 命令。
    for command_name in SYSTEM_SEVEN_ZIP_COMMAND_CANDIDATES:
        executable_path = shutil.which(command_name)
        if executable_path:
            return executable_path

    candidate_text = "；".join(str(path.resolve()) for path in candidate_paths)
    raise FileNotFoundError(
        "未找到可用的 7z 工具，请检查项目内置 7za.exe 或系统 PATH。\n"
        f"已检查内置路径: {candidate_text}\n"
        f"已尝试系统命令: {', '.join(SYSTEM_SEVEN_ZIP_COMMAND_CANDIDATES)}"
    )


def _run_7z_command(arguments: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    """执行 7z 命令，并在失败时抛出带上下文的中文错误。

    参数:
        arguments: 传给 7z 的命令行参数列表。
        cwd: 可选的命令工作目录。

    返回:
        7z 命令执行完成后的结果对象。
    """
    # 第一步：解析可执行命令，并按 scripts/build.py 的方式直接发起 7z 调用。
    command = [_resolve_7z_executable(), *arguments]
    try:
        # 第二步：统一捕获输出，便于失败时回传完整上下文。
        return subprocess.run(
            command,
            cwd=str(cwd) if cwd is not None else None,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        command_text = " ".join(command)
        raise RuntimeError(
            "7z 命令执行失败。\n"
            f"命令: {command_text}\n"
            f"退出码: {exc.returncode}\n"
            f"标准输出:\n{exc.stdout}\n"
            f"错误输出:\n{exc.stderr}"
        ) from exc


def create_7z_archive(source_dir: Path, output_archive_path: Path) -> Path:
    """使用 7z 将资源目录内容打包为 7z 文件。

    参数:
        source_dir: 待打包的资源目录。
        output_archive_path: 生成的 7z 包输出路径。

    返回:
        生成后的 7z 包路径。
    """
    # 第一步：校验输入目录，避免对不存在目录或空目录进行打包。
    if not source_dir.exists():
        raise FileNotFoundError(f"源资源目录不存在: {source_dir}")
    if not source_dir.is_dir():
        raise NotADirectoryError(f"源资源路径不是目录: {source_dir}")
    if not any(path.is_file() for path in source_dir.rglob("*")):
        raise ValueError(f"源资源目录中没有可打包文件: {source_dir}")

    # 第二步：准备输出目录，并清理同名旧包，防止旧构建产物残留。
    output_archive_path.parent.mkdir(parents=True, exist_ok=True)
    if output_archive_path.exists():
        output_archive_path.unlink()

    # 第三步：使用当前目录下的 .\* 作为输入，保证包内路径从资源目录根开始计算。
    _run_7z_command(["a", "-t7z", str(output_archive_path.resolve()), ".\\*"], cwd=source_dir)
    return output_archive_path


def _list_7z_members(archive_path: Path) -> list[Path]:
    """列出 7z 包中的成员路径。

    参数:
        archive_path: 待检查的 7z 资源包路径。

    返回:
        资源包内所有成员的路径列表。
    """
    if not archive_path.is_file():
        raise FileNotFoundError(f"待检查的 7z 资源包不存在: {archive_path}")

    # 第一步：通过 7z 的结构化列表模式获取全部成员信息。
    completed = _run_7z_command(["l", "-slt", str(archive_path.resolve())])
    member_paths: list[Path] = []
    in_member_section = False

    # 第二步：仅提取每个成员的 Path 字段，供后续路径安全校验使用。
    for raw_line in completed.stdout.splitlines():
        line = raw_line.strip()
        if line == "----------":
            in_member_section = True
            continue
        if not in_member_section or not line.startswith("Path = "):
            continue
        member_paths.append(Path(line.removeprefix("Path = ")))

    return member_paths


def extract_7z_archive(archive_path: Path, extract_dir: Path) -> Path:
    """在校验成员路径后，将 7z 资源包安全解压到目标目录。

    参数:
        archive_path: 待解压的 7z 资源包路径。
        extract_dir: 解压输出目录。

    返回:
        解压完成后的输出目录路径。
    """
    # 第一步：重建临时解压目录，确保本次解压不受旧文件残留影响。
    if extract_dir.exists():
        shutil.rmtree(extract_dir)
    extract_dir.mkdir(parents=True, exist_ok=True)

    # 第二步：先检查包内成员路径，阻止绝对路径和 .. 穿越写出。
    member_paths = _list_7z_members(archive_path)
    for member_path in member_paths:
        if member_path.is_absolute() or ".." in member_path.parts:
            raise ValueError(f"资源包包含非法路径: {member_path}")

    # 第三步：执行覆盖式解压，保证同步时始终拿到完整的新包内容。
    _run_7z_command(["x", str(archive_path.resolve()), f"-o{extract_dir.resolve()}", "-aoa", "-y"])
    return extract_dir

from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

import psutil

from module.logger import log
from module.platform_compat import IS_WINDOWS
from utils.adb_endpoint import normalize_adb_host

if IS_WINDOWS:
    import winreg

BLUESTACKS_SIMULATOR_TYPE = 1
_LOCAL_ADB_HOSTS = {"127.0.0.1", "::1", "localhost"}
_REGISTRY_PATH = r"SOFTWARE\BlueStacks_nxt"
_INSTANCE_SETTING = re.compile(r'^bst\.instance\.([^.]+)\.(display_name|status\.adb_port)="(.*)"$')
_ADB_SETTING = re.compile(r'^bst\.enable_adb_access="([01])"$')


class BlueStacksError(RuntimeError):
    pass


@dataclass(frozen=True)
class BlueStacksInstance:
    name: str
    display_name: str
    adb_port: int


def is_local_adb_host(host: str) -> bool:
    return normalize_adb_host(host) in _LOCAL_ADB_HOSTS


def parse_bluestacks_config(text: str) -> tuple[bool, list[BlueStacksInstance]]:
    adb_enabled = False
    values: dict[str, dict[str, str]] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if match := _ADB_SETTING.fullmatch(line):
            adb_enabled = match.group(1) == "1"
            continue
        if match := _INSTANCE_SETTING.fullmatch(line):
            instance_name, setting_name, value = match.groups()
            values.setdefault(instance_name, {})[setting_name] = value

    instances = []
    for instance_name, settings in values.items():
        port_text = settings.get("status.adb_port", "")
        try:
            adb_port = int(port_text)
        except ValueError:
            continue
        if not 1 <= adb_port <= 65535:
            continue
        instances.append(
            BlueStacksInstance(
                name=instance_name,
                display_name=settings.get("display_name", instance_name),
                adb_port=adb_port,
            )
        )
    return adb_enabled, instances


def select_bluestacks_instance(
    instances: list[BlueStacksInstance],
    requested_name: str = "",
    requested_port: int = 0,
) -> BlueStacksInstance:
    if not instances:
        raise BlueStacksError("未在 bluestacks.conf 中找到可用的蓝叠实例或 ADB 端口")

    normalized_name = str(requested_name).strip().casefold()
    if normalized_name:
        matches = [
            instance
            for instance in instances
            if normalized_name in {instance.name.casefold(), instance.display_name.casefold()}
        ]
        if not matches:
            available = ", ".join(instance.name for instance in instances)
            raise BlueStacksError(f"未找到蓝叠实例 {requested_name!r}，可用实例: {available}")
        selected = matches[0]
        if requested_port and int(requested_port) != selected.adb_port:
            log.warning(
                f"蓝叠实例 {selected.name} 的实际 ADB 端口为 {selected.adb_port}，"
                f"将忽略设置中的端口 {requested_port}"
            )
        return selected

    if requested_port:
        for instance in instances:
            if instance.adb_port == int(requested_port):
                return instance
        available = ", ".join(f"{item.name}:{item.adb_port}" for item in instances)
        raise BlueStacksError(f"没有蓝叠实例使用 ADB 端口 {requested_port}，可用实例: {available}")

    if len(instances) == 1:
        return instances[0]

    available = ", ".join(f"{item.name}:{item.adb_port}" for item in instances)
    raise BlueStacksError(f"检测到多个蓝叠实例，请填写实例名或 ADB 端口: {available}")


class BlueStacksLauncher:
    def __init__(self, executable: Path, config_path: Path, adb_enabled: bool, instances: list[BlueStacksInstance]):
        self.executable = executable
        self.config_path = config_path
        self.adb_enabled = adb_enabled
        self.instances = instances

    @classmethod
    def discover(cls) -> "BlueStacksLauncher":
        if not IS_WINDOWS:
            raise BlueStacksError("BlueStacks 模拟器仅支持 Windows；Linux 下请改用远程 ADB 连接（如 Waydroid）")
        install_dir = ""
        user_data_dir = ""
        registry_access_modes = (winreg.KEY_READ | winreg.KEY_WOW64_64KEY, winreg.KEY_READ)
        for access in registry_access_modes:
            try:
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, _REGISTRY_PATH, 0, access) as key:
                    install_dir = str(winreg.QueryValueEx(key, "InstallDir")[0])
                    user_data_dir = str(winreg.QueryValueEx(key, "UserDefinedDir")[0])
                break
            except OSError:
                continue

        executable_candidates = []
        if install_dir:
            executable_candidates.append(Path(install_dir) / "HD-Player.exe")
        program_files = os.environ.get("ProgramFiles")
        if program_files:
            executable_candidates.append(Path(program_files) / "BlueStacks_nxt" / "HD-Player.exe")
        executable = next((path for path in executable_candidates if path.is_file()), None)
        if executable is None:
            raise BlueStacksError("未找到 BlueStacks 5 的 HD-Player.exe，请确认已安装蓝叠 5")

        config_candidates = []
        if user_data_dir:
            config_candidates.append(Path(user_data_dir) / "bluestacks.conf")
        program_data = os.environ.get("ProgramData")
        if program_data:
            config_candidates.append(Path(program_data) / "BlueStacks_nxt" / "bluestacks.conf")
        config_path = next((path for path in config_candidates if path.is_file()), None)
        if config_path is None:
            raise BlueStacksError("未找到 BlueStacks 5 的 bluestacks.conf")

        config_text = config_path.read_text(encoding="utf-8")
        adb_enabled, instances = parse_bluestacks_config(config_text)
        return cls(executable, config_path, adb_enabled, instances)

    def resolve_instance(self, requested_name: str = "", requested_port: int = 0) -> BlueStacksInstance:
        if not self.adb_enabled:
            raise BlueStacksError("蓝叠 ADB 已关闭，请在蓝叠设置的高级选项中启用 Android 调试桥（ADB）")
        return select_bluestacks_instance(self.instances, requested_name, requested_port)

    def launch(self, instance: BlueStacksInstance, stale_process_timeout: float = 20.0) -> bool:
        existing_processes = self._find_instance_processes(instance)
        if existing_processes:
            log.warning(
                f"检测到 BlueStacks 5 实例 {instance.name} 的残留进程，"
                f"等待其退出后再启动（最多 {stale_process_timeout:g} 秒）"
            )
            _, alive = psutil.wait_procs(existing_processes, timeout=max(0.0, stale_process_timeout))
            if alive:
                pids = ", ".join(str(process.pid) for process in alive)
                log.info(
                    f"BlueStacks 5 实例 {instance.name} 仍在运行（PID: {pids}），"
                    "跳过重复启动并继续等待 ADB"
                )
                return False
            log.info(f"BlueStacks 5 实例 {instance.name} 的旧进程已退出，准备重新启动")

        log.info(
            f"正在启动 BlueStacks 5 实例 {instance.name} "
            f"({instance.display_name})，ADB 端口 {instance.adb_port}"
        )
        creation_flags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        subprocess.Popen(
            [str(self.executable), "--instance", instance.name],
            cwd=str(self.executable.parent),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
            creationflags=creation_flags,
        )
        return True

    @staticmethod
    def _find_instance_processes(instance: BlueStacksInstance) -> list[psutil.Process]:
        matches = []
        for process in psutil.process_iter(["name", "cmdline"]):
            try:
                name = str(process.info.get("name") or "").casefold()
                command = [str(value) for value in (process.info.get("cmdline") or [])]
            except (psutil.AccessDenied, psutil.NoSuchProcess, psutil.ZombieProcess):
                continue
            if name != "hd-player.exe":
                continue
            for index, argument in enumerate(command[:-1]):
                if argument.casefold() == "--instance" and command[index + 1].casefold() == instance.name.casefold():
                    matches.append(process)
                    break
        return matches

    def close(self, instance: BlueStacksInstance, timeout: float = 15.0) -> None:
        """Gracefully close one BlueStacks instance, with a forced fallback."""
        processes = self._find_instance_processes(instance)
        if not processes:
            log.info(f"BlueStacks 5 实例 {instance.name} 已经关闭")
            return

        log.info(f"正在关闭 BlueStacks 5 实例 {instance.name}")
        for process in processes:
            try:
                subprocess.run(
                    ["taskkill", "/PID", str(process.pid), "/T"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    check=False,
                )
            except (OSError, subprocess.SubprocessError) as exc:
                log.debug(f"请求蓝叠实例 {instance.name} 正常退出失败: {exc}")

        _, alive = psutil.wait_procs(processes, timeout=max(1.0, timeout))
        for process in alive:
            try:
                subprocess.run(
                    ["taskkill", "/F", "/PID", str(process.pid), "/T"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    check=False,
                )
            except (OSError, subprocess.SubprocessError) as exc:
                log.debug(f"强制关闭蓝叠实例 {instance.name} 失败: {exc}")

        if alive:
            _, alive = psutil.wait_procs(alive, timeout=5)
        if alive:
            pids = ", ".join(str(process.pid) for process in alive)
            raise BlueStacksError(f"无法关闭 BlueStacks 5 实例 {instance.name}，仍在运行的进程: {pids}")
        log.info(f"BlueStacks 5 实例 {instance.name} 已关闭")

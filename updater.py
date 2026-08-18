import json
import os
import shutil
import subprocess
import sys
from pathlib import Path, PurePosixPath

import psutil


class UpdateManifestError(ValueError):
    """更新清单包含不能安全应用的内容。"""


class Updater:
    """应用程序更新器，负责检查、下载、解压和安装最新版本的应用程序。"""

    def __init__(self, file_name=None):
        self.process_names = ["AALC.exe"]
        self.updater_name = "AALC Updater.exe"
        self.apply_updater_name = "AALC Updater.apply.exe"

        self.temp_path = os.path.abspath("./update_temp")
        os.makedirs(self.temp_path, exist_ok=True)

        self.file_name = file_name

        self.cover_folder_path = os.path.abspath("./")

        self.exe_path = os.path.abspath("./assets/binary/7za.exe")
        self.delete_folder_path = os.path.abspath("./assets/images")
        self.changes_file_path = os.path.abspath("./update_temp/changes.json")

        if self.file_name is None:
            self.download_file_path = None
            self.extract_folder_path = self.temp_path
        else:
            self.download_file_path = os.path.join(self.temp_path, self.file_name)
            self.extract_folder_path = os.path.join(self.temp_path, self.file_name.rsplit(".", 1)[0])

        self._incremental_update_plan = None

    def extract_file(self):
        """解压下载的文件。"""
        print("开始解压...")
        while True:
            try:
                self._reset_extraction_workspace()
                if os.path.exists(self.exe_path):
                    subprocess.run(
                        [
                            self.exe_path,
                            "x",
                            self.download_file_path,
                            f"-o{self.temp_path}",
                            "-aoa",
                        ],
                        check=True,
                    )
                else:
                    shutil.unpack_archive(self.download_file_path, self.temp_path)
                print("解压完成")
                return True
            except Exception:
                input("解压失败，按回车键重新解压. . .多次失败请手动下载更新")
                return False

    def _reset_extraction_workspace(self):
        """清理本次解压目标，避免复用上一次更新残留的载荷或清单。"""
        if not self.download_file_path:
            return

        if self.extract_folder_path and os.path.isdir(self.extract_folder_path):
            shutil.rmtree(self.extract_folder_path)
        if self.changes_file_path and os.path.exists(self.changes_file_path):
            os.remove(self.changes_file_path)

    def cover_folder(self):
        """覆盖安装最新版本的文件。"""
        if os.path.exists(self.changes_file_path):
            self._apply_incremental_update()
        else:
            try:
                shutil.rmtree(self.delete_folder_path)
            except FileNotFoundError:
                print("待删除目录不存在，跳过")
            except Exception as e:
                print(f"删除旧资源文件失败: {e}")
            print("开始覆盖安装...")
            while True:
                try:
                    shutil.copytree(self.extract_folder_path, self.cover_folder_path, dirs_exist_ok=True)
                    print("覆盖安装完成")
                    break
                except Exception as e:
                    print(f"覆盖安装失败: {e}")
                    input("按回车键重试. . . \n Press any key to continue")

    def _apply_incremental_update(self):
        """根据 changes.json 执行增量更新。"""
        changes = self._incremental_update_plan or self._load_incremental_update_plan()

        print("检测到增量更新清单，执行增量更新...")

        for dir_path, full_path in changes["deleted_dir"]:
            try:
                shutil.rmtree(full_path)
                print(f"删除目录: {dir_path}")
            except FileNotFoundError:
                print(f"删除目录不存在: {dir_path}")

        for file_path, full_path in changes["deleted"]:
            try:
                os.remove(full_path)
                print(f"删除文件: {file_path}")
            except FileNotFoundError:
                print(f"删除文件不存在: {file_path}")

        for dir_path, full_path in changes["added_dir"]:
            os.makedirs(full_path, exist_ok=True)
            print(f"创建目录: {dir_path}")

        for file_path, src, dst in changes["added"]:
            try:
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(src, dst)
                print(f"新增文件: {file_path}")
            except FileNotFoundError:
                print(f"源文件不存在: {file_path}")

        for file_path, src, dst in changes["modified"]:
            try:
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(src, dst)
                print(f"更新文件: {file_path}")
            except FileNotFoundError:
                print(f"源文件不存在: {file_path}")

        print("增量更新完成")

    def _normalize_manifest_path(self, relative_path):
        """兼容带归档根目录前缀与普通相对路径的增量清单。"""
        if not isinstance(relative_path, str) or not relative_path or "\0" in relative_path:
            raise UpdateManifestError("更新清单包含空路径或非字符串路径")

        portable_path = relative_path.replace("\\", "/")
        if portable_path.startswith("/") or (len(portable_path) >= 2 and portable_path[1] == ":"):
            raise UpdateManifestError(f"更新清单包含绝对路径: {relative_path}")

        raw_parts = PurePosixPath(portable_path).parts
        if any(part == ".." or ":" in part for part in raw_parts):
            raise UpdateManifestError(f"更新清单包含非法相对路径: {relative_path}")

        parts = [part for part in raw_parts if part not in ("", ".")]
        if not parts:
            raise UpdateManifestError("更新清单包含空路径")

        archive_root_name = os.path.basename(os.path.normpath(self.extract_folder_path))
        if os.path.normcase(parts[0]) == os.path.normcase(archive_root_name):
            parts = parts[1:]

        if not parts:
            raise UpdateManifestError("更新清单不能指向归档根目录")

        return os.path.join(*parts)

    @staticmethod
    def _resolve_path_within_root(root_path, relative_path):
        """解析路径并拒绝经父目录或链接离开可信根目录的情况。"""
        try:
            root = Path(root_path).resolve()
            candidate = (root / relative_path).resolve()
        except OSError as exc:
            raise UpdateManifestError(f"无法解析更新清单路径: {relative_path}") from exc
        try:
            candidate.relative_to(root)
        except ValueError as exc:
            raise UpdateManifestError(f"更新清单路径逃离可信根目录: {relative_path}") from exc
        return os.fspath(candidate)

    def _load_incremental_update_plan(self):
        try:
            with open(self.changes_file_path, "r", encoding="utf-8") as f:
                raw_changes = json.load(f)
        except (OSError, json.JSONDecodeError) as exc:
            raise UpdateManifestError("无法读取更新清单") from exc

        if not isinstance(raw_changes, dict):
            raise UpdateManifestError("更新清单必须是对象")

        plan = {"deleted_dir": [], "deleted": [], "added_dir": [], "added": [], "modified": []}
        for operation, entries in raw_changes.items():
            if operation not in plan:
                raise UpdateManifestError(f"更新清单包含未知操作: {operation}")
            if not isinstance(entries, list):
                raise UpdateManifestError(f"更新清单操作 {operation} 必须是路径列表")

            for original_path in entries:
                normalized_path = self._normalize_manifest_path(original_path)
                target_path = self._resolve_path_within_root(self.cover_folder_path, normalized_path)
                if operation in {"added", "modified"}:
                    source_path = self._resolve_path_within_root(self.extract_folder_path, normalized_path)
                    plan[operation].append((original_path, source_path, target_path))
                else:
                    plan[operation].append((original_path, target_path))

        return plan

    def validate_update_payload(self):
        """在终止应用进程前验证增量更新清单及其所有目标路径。"""
        self._incremental_update_plan = None
        if not os.path.exists(self.changes_file_path):
            return
        self._incremental_update_plan = self._load_incremental_update_plan()

    def _get_extracted_updater_path(self):
        return os.path.join(self.extract_folder_path, self.updater_name)

    def _get_staged_updater_path(self):
        return os.path.join(self.temp_path, self.apply_updater_name)

    def _prepare_update_payload(self, apply_mode):
        while True:
            if self.extract_file():
                return

    def _handoff_to_new_updater(self, current_executable=None):
        if not self.file_name:
            return False

        extracted_updater_path = self._get_extracted_updater_path()
        if not os.path.exists(extracted_updater_path):
            return False

        current_executable_path = os.path.abspath(current_executable or sys.argv[0])
        staged_updater_path = self._get_staged_updater_path()

        try:
            if os.path.abspath(extracted_updater_path) == current_executable_path:
                return False

            shutil.copy2(extracted_updater_path, staged_updater_path)
            subprocess.Popen(
                [staged_updater_path, "--apply-update", self.file_name],
                creationflags=subprocess.DETACHED_PROCESS,
                cwd=self.cover_folder_path,
            )
            print("已切换到新版本更新器继续更新...")
            return True
        except Exception as e:
            print(f"切换到新版本更新器失败，将继续使用当前更新器: {e}")
            return False

    def terminate_processes(self):
        """终止相关进程以准备更新。"""
        print("开始终止进程...")
        install_root = os.path.normcase(os.path.abspath(self.cover_folder_path)) + os.sep
        for proc in psutil.process_iter(attrs=["pid", "name"]):
            if proc.pid == os.getpid():
                continue  # 更新器自身位于 update_temp（安装根目录内），不能杀自己
            try:
                exe_path = proc.exe()
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                continue
            # 覆盖 AALC 及安装目录内的附属进程（如 adb 服务），否则其可执行文件会被占用无法覆盖
            is_install_binary = os.path.normcase(exe_path).startswith(install_root)
            if proc.info["name"] in self.process_names or any(name in proc.info["name"] for name in self.process_names) or is_install_binary:
                try:
                    proc.terminate()
                    try:
                        proc.wait(timeout=10)  # 等待最多10秒
                    except psutil.TimeoutExpired:
                        proc.kill()  # 超时强制终止
                        proc.wait(timeout=5)  # 再次等待
                except psutil.AccessDenied:
                    print(f"无权限终止进程 PID: {proc.info['pid']}")
                except psutil.NoSuchProcess:
                    print(f"进程 PID: {proc.info['pid']} 已退出")
        print("终止进程完成")

    def cleanup(self):
        """清理下载和解压的临时文件。"""
        print("开始清理...")
        self._cleanup_file(self.download_file_path, "下载文件")
        self._cleanup_tree(self.extract_folder_path, "提取目录")
        self._cleanup_file(self.changes_file_path, "变更清单文件")
        print("清理完成")

    @staticmethod
    def _cleanup_file(path, label):
        if not path:
            return
        try:
            os.remove(path)
        except FileNotFoundError:
            print(f"{label}不存在，跳过")
        except Exception as e:
            print(f"清理{label}失败: {e}")

    @staticmethod
    def _cleanup_tree(path, label):
        if not path:
            return
        try:
            shutil.rmtree(path)
        except FileNotFoundError:
            print(f"{label}不存在，跳过")
        except Exception as e:
            print(f"清理{label}失败: {e}")

    def run(self, apply_mode=False):
        """运行更新流程。"""
        self._prepare_update_payload(apply_mode)
        try:
            self.validate_update_payload()
        except UpdateManifestError as exc:
            print(f"更新清单无效，已取消更新: {exc}")
            return False
        if not apply_mode and self._handoff_to_new_updater():
            return
        self.terminate_processes()
        self.cover_folder()
        self.cleanup()
        input("已完成更新，按回车键退出并打开软件\nThe update is complete, press enter to exit and open the software")
        if os.system(f'cmd /c start "" "{os.path.abspath("./AALC.exe")}"'):
            subprocess.Popen(os.path.abspath("./AALC.exe"))


def check_temp_dir_and_run():
    """检查临时目录并运行更新程序。"""
    if not getattr(sys, "frozen", False):
        print("更新程序只支持打包成exe后运行")
        sys.exit(1)

    temp_path = os.path.abspath("./update_temp")
    file_path = sys.argv[0]
    destination_path = os.path.join(temp_path, os.path.basename(file_path))

    if file_path != destination_path:
        if os.path.exists("./Update.exe"):
            os.remove("./Update.exe")
        os.makedirs(temp_path, exist_ok=True)
        shutil.copy(file_path, destination_path)
        args = [destination_path] + sys.argv[1:]
        subprocess.Popen(args, creationflags=subprocess.DETACHED_PROCESS)
        sys.exit(0)

    apply_mode = len(sys.argv) >= 3 and sys.argv[1] == "--apply-update"
    if apply_mode:
        file_name = sys.argv[2]
    else:
        file_name = sys.argv[1] if len(sys.argv) == 2 else None

    updater = Updater(file_name)
    updater.run(apply_mode=apply_mode)


if __name__ == "__main__":
    check_temp_dir_and_run()

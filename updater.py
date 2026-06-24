import json
import os
import shutil
import subprocess
import sys
from pathlib import PurePosixPath

import psutil


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

    def extract_file(self):
        """解压下载的文件。"""
        print("开始解压...")
        while True:
            try:
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

    def cover_folder(self):
        """覆盖安装最新版本的文件。"""
        if os.path.exists(self.changes_file_path):
            self._apply_incremental_update()
        else:
            try:
                shutil.rmtree(self.delete_folder_path)
            except FileNotFoundError:
                pass
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
        with open(self.changes_file_path, "r", encoding="utf-8") as f:
            changes = json.load(f)

        print("检测到增量更新清单，执行增量更新...")

        for dir_path in changes.get("deleted_dir", []):
            normalized_path = self._normalize_manifest_path(dir_path)
            if not normalized_path:
                continue
            full_path = os.path.join(self.cover_folder_path, normalized_path)
            try:
                shutil.rmtree(full_path)
                print(f"删除目录: {dir_path}")
            except FileNotFoundError:
                pass

        for file_path in changes.get("deleted", []):
            normalized_path = self._normalize_manifest_path(file_path)
            if not normalized_path:
                continue
            full_path = os.path.join(self.cover_folder_path, normalized_path)
            try:
                os.remove(full_path)
                print(f"删除文件: {file_path}")
            except FileNotFoundError:
                pass

        for dir_path in changes.get("added_dir", []):
            normalized_path = self._normalize_manifest_path(dir_path)
            if not normalized_path:
                continue
            full_path = os.path.join(self.cover_folder_path, normalized_path)
            os.makedirs(full_path, exist_ok=True)
            print(f"创建目录: {dir_path}")

        for file_path in changes.get("added", []):
            normalized_path = self._normalize_manifest_path(file_path)
            if not normalized_path:
                continue
            src = os.path.join(self.extract_folder_path, normalized_path)
            dst = os.path.join(self.cover_folder_path, normalized_path)
            try:
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(src, dst)
                print(f"新增文件: {file_path}")
            except FileNotFoundError:
                pass

        for file_path in changes.get("modified", []):
            normalized_path = self._normalize_manifest_path(file_path)
            if not normalized_path:
                continue
            src = os.path.join(self.extract_folder_path, normalized_path)
            dst = os.path.join(self.cover_folder_path, normalized_path)
            try:
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(src, dst)
                print(f"更新文件: {file_path}")
            except FileNotFoundError:
                pass

        print("增量更新完成")

    def _normalize_manifest_path(self, relative_path):
        """兼容带归档根目录前缀与普通相对路径的增量清单。"""
        parts = [part for part in PurePosixPath(relative_path.replace("\\", "/")).parts if part not in ("", ".")]
        if not parts:
            return None

        archive_root_name = os.path.basename(os.path.normpath(self.extract_folder_path))
        if parts[0] == archive_root_name:
            parts = parts[1:]

        if not parts:
            return None

        return os.path.join(*parts)

    def _get_extracted_updater_path(self):
        return os.path.join(self.extract_folder_path, self.updater_name)

    def _get_staged_updater_path(self):
        return os.path.join(self.temp_path, self.apply_updater_name)

    def _prepare_update_payload(self, apply_mode):
        if apply_mode and os.path.isdir(self.extract_folder_path):
            print("检测到已解压的更新包，使用新更新器继续更新...")
            return

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
        for proc in psutil.process_iter(attrs=["pid", "name"]):
            if proc.info["name"] in self.process_names or any(name in proc.info["name"] for name in self.process_names):
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
        try:
            os.remove(self.download_file_path)
        except FileNotFoundError:
            pass
        try:
            shutil.rmtree(self.extract_folder_path)
        except FileNotFoundError:
            pass
        try:
            os.remove(self.changes_file_path)
        except FileNotFoundError:
            pass
        print("清理完成")

    def run(self, apply_mode=False):
        """运行更新流程。"""
        self._prepare_update_payload(apply_mode)
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

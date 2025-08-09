import os
import shutil
import subprocess
import sys

import psutil


class Updater:
    """应用程序更新器，负责检查、下载、解压和安装最新版本的应用程序。"""

    def __init__(self, file_name=None):
        self.process_names = ["AALC.exe"]

        self.temp_path = os.path.abspath("./update_temp")
        os.makedirs(self.temp_path, exist_ok=True)

        self.file_name = file_name

        self.cover_folder_path = os.path.abspath("./")

        self.exe_path = os.path.abspath("./assets/binary/7za.exe")
        self.delete_folder_path = os.path.abspath("./assets/images")

        self.download_file_path = os.path.join(self.temp_path, self.file_name)
        self.extract_folder_path = os.path.join(self.temp_path, self.file_name.rsplit(".", 1)[0])

    def extract_file(self):
        """解压下载的文件。"""
        print("开始解压...")
        while True:
            try:
                if os.path.exists(self.exe_path):
                    subprocess.run([self.exe_path, "x", self.download_file_path, f"-o{self.temp_path}", "-aoa"],
                                   check=True)
                else:
                    shutil.unpack_archive(self.download_file_path, self.temp_path)
                print("解压完成")
                return True
            except Exception as e:
                input("解压失败，按回车键重新解压. . .多次失败请手动下载更新")
                return False

    def cover_folder(self):
        """覆盖安装最新版本的文件。"""
        print("开始覆盖安装...")
        while True:
            try:
                if os.path.exists(self.delete_folder_path):
                    shutil.rmtree(self.delete_folder_path)
                shutil.copytree(self.extract_folder_path, self.cover_folder_path, dirs_exist_ok=True)
                print("覆盖安装完成")
                break
            except Exception as e:
                print(f"覆盖失败: {e}")
                input("按回车键重试. . .")

    def terminate_processes(self):
        """终止相关进程以准备更新。"""
        print("开始终止进程...")
        for proc in psutil.process_iter(attrs=['pid', 'name']):
            if proc.info['name'] in self.process_names or any(name in proc.info['name'] for name in self.process_names):
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
            shutil.rmtree(self.extract_folder_path)
            print("清理完成")
        except Exception as e:
            print(f"清理失败: {e}")

    def run(self):
        """运行更新流程。"""
        while True:
            if self.extract_file():
                break
        self.terminate_processes()
        self.cover_folder()
        self.cleanup()
        input("已完成更新，按回车键退出并打开软件\nThe update is complete, press enter to exit and open the software")
        if os.system(f'cmd /c start "" "{os.path.abspath("./AALC.exe")}"'):
            subprocess.Popen(os.path.abspath("./AALC.exe"))


def check_temp_dir_and_run():
    """检查临时目录并运行更新程序。"""
    if not getattr(sys, 'frozen', False):
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

    file_name = sys.argv[1] if len(sys.argv) == 2 else None

    updater = Updater(file_name)
    updater.run()


if __name__ == '__main__':
    check_temp_dir_and_run()

import os  # 导入os模块以便操作文件路径
import re
import shutil
import subprocess
from enum import Enum
from threading import Thread

import requests  # 导入requests模块，用于发送HTTP请求
from PySide6.QtCore import QThread, Signal, Qt, QT_TRANSLATE_NOOP
from markdown_it import MarkdownIt
from packaging.version import parse
from qfluentwidgets import InfoBarPosition

from app import mediator
from app.card.messagebox_custom import MessageBoxUpdate, BaseInfoBar
from module.config import cfg
from module.decorator.decorator import begin_and_finish_time_log
from module.logger import log
from utils.utils import decrypt_string

md_renderer = MarkdownIt("gfm-like", {"html": True})


class UpdateStatus(Enum):
    """
    定义更新状态的枚举类

    该枚举类用于表示更新操作的三种可能结果状态：
    - SUCCESS 表示更新操作成功
    - UPDATE_AVAILABLE 表示有可用的更新
    - FAILURE 表示更新操作失败
    """
    SUCCESS = 1
    UPDATE_AVAILABLE = 2
    FAILURE = 0


class UpdateThread(QThread):
    """
    更新线程类，用于在后台检查和处理软件更新。
    该类继承自 QThread，使用 Qt 的信号机制来通知 GUI 线程更新状态。
    """
    # 定义更新信号，用于通知主线程更新状态
    updateSignal = Signal(UpdateStatus)

    def __init__(self, timeout, flag):
        """
        初始化更新线程。

        参数:
        timeout -- 超时时间（秒）
        flag -- 标志位，用于控制是否执行检查更新
        """
        super().__init__()
        self.timeout = timeout  # 超时时间
        self.flag = flag  # 标志位，用于控制是否执行检查更新
        self.error_msg = ''  # 错误信息

        self.user = "KIYI671"
        self.repo = "AhabAssistantLimbusCompany"
        self.new_version = ''

    def run(self) -> None:
        """
        更新线程的主逻辑。
        检查是否有新版本，如果有，则发送更新可用信号；否则发送成功信号。
        """
        # 开发模式下跳过更新检查
        if os.environ.get('AALC_DEV_MODE') == '1':
            return
        try:
            # 如果标志位为 False 且配置中的检查更新标志也为 False，则直接返回
            if self.flag and not cfg.get_value("check_update"):
                return

            # 获取最新发布版本的信息
            data = self.check_update_info_mirrorchyan()
            version = data['version_name']
            content = self.remove_images_from_markdown(data['release_note'])
            content = re.sub(r"\r\n\r\n\[.*?Mirror酱.*?CDK.*?下载\]\(https?://.*?mirrorchyan\.com[^\)]*\)", "",
                             content, flags=re.IGNORECASE)
            if cfg.update_source == "GitHub":
                content = content + "\n\n若下载速度较慢，可尝试使用 Mirror酱（设置 → 关于 → 更新源） 高速下载"

            # 比较当前版本和最新版本，如果最新版本更高，则准备更新
            if parse(version.lstrip('Vv')) > parse(cfg.version.lstrip('Vv')):
                self.title = self.tr("发现新版本：{Old_version} ——> {New_version}\n更新日志:").format(
                    Old_version=cfg.version, New_version=version)
                self.content = "<style>a {color: #586f50; font-weight: bold;}</style>" + md_renderer.render(content)
                self.updateSignal.emit(UpdateStatus.UPDATE_AVAILABLE)
            else:
                # 如果没有新版本，则发送成功信号
                self.updateSignal.emit(UpdateStatus.SUCCESS)
        except Exception as e:
            # 记录失败日志，尝试使用GitHub源检查更新
            log.error(f"从Mirror酱源检查更新失败:{e},尝试使用GitHub源检查更新")
            try:
                data = self.check_update_info_github()
                version = data['tag_name']
                content = self.remove_images_from_markdown(data['body'])
                content = re.sub(r"\r\n\r\n\[.*?Mirror酱.*?CDK.*?下载\]\(https?://.*?mirrorchyan\.com[^\)]*\)", "",
                                 content, flags=re.IGNORECASE)
                assets_url = self.get_download_url_from_assets(data['assets'])

                if cfg.update_source == "GitHub":
                    content = content + "\n\n若下载速度较慢，可尝试使用 Mirror酱（设置 → 关于 → 更新源） 高速下载"

                # 如果没有可用的下载 URL，则发送成功信号并返回
                if assets_url is None:
                    self.updateSignal.emit(UpdateStatus.SUCCESS)
                    return

                # 比较当前版本和最新版本，如果最新版本更高，则准备更新
                if parse(version.lstrip('Vv')) > parse(cfg.version.lstrip('Vv')):
                    self.title = self.tr("发现新版本：{Old_version} ——> {New_version}\n更新日志:").format(
                        Old_version=cfg.version, New_version=version)
                    self.content = "<style>a {color: #586f50; font-weight: bold;}</style>" + md_renderer.render(content)
                    self.updateSignal.emit(UpdateStatus.UPDATE_AVAILABLE)
                else:
                    # 如果没有新版本，则发送成功信号
                    self.updateSignal.emit(UpdateStatus.SUCCESS)
            except Exception as e:
                # 异常处理，发送失败信号
                log.error(f"Mirror酱源与GitHub源均检查更新失败:{e}")
                self.updateSignal.emit(UpdateStatus.FAILURE)

    def check_update_info_github(self):
        """
        从 GitHub 获取最新发布版本的信息。

        返回:
        最新发布版本的信息（JSON 格式）
        """
        if not cfg.update_prerelease_enable:
            response = requests.get(
                f"https://api.github.com/repos/{self.user}/{self.repo}/releases/latest",
                timeout=10,
                headers=cfg.useragent
            )
        else:
            response = requests.get(
                f"https://api.github.com/repos/{self.user}/{self.repo}/releases",
                timeout=10,
                headers=cfg.useragent
            )
        response.raise_for_status()
        # 根据配置决定是否包含预发布版本
        return response.json()[0] if cfg.update_prerelease_enable else response.json()

    def check_update_info_mirrorchyan(self, cdk=''):
        """
        从 mirror酱 获取最新发布版本的信息。

        参数:
        cdk -- Mirror酱 CDK

        返回:
        最新发布版本的信息（JSON 格式）
        """
        if not cfg.update_prerelease_enable:
            response = requests.get(
                f"https://mirrorchyan.com/api/resources/AALC/latest?current_version={cfg.version}&user_agent={self.repo}&cdk={cdk}",
                timeout=10,
                headers=cfg.useragent
            )
        else:
            response = requests.get(
                f"https://mirrorchyan.com/api/resources/AALC/latest?current_version={cfg.version}&user_agent={self.repo}&channel=beta&cdk={cdk}",
                timeout=10,
                headers=cfg.useragent
            )
        response.raise_for_status()
        if cdk == '':
            # 返回获取的最新发布版本信息
            return response.json()["data"]
        else:
            return response

    def remove_images_from_markdown(self, markdown_content):
        """
        从 Markdown 内容中移除图片。

        参数:
        markdown_content -- Markdown 格式的文本

        返回:
        移除图片后的 Markdown 文本
        """
        img_pattern = re.compile(r'!\[.*?\]\(.*?\)')
        return img_pattern.sub('', markdown_content)

    def get_download_url_from_assets(self, assets):
        """
        从资产列表中获取 .7z 文件的下载 URL。

        参数:
        assets -- 资产列表（JSON 格式）

        返回:
        .7z 文件的下载 URL，如果没有找到则返回 None
        """
        for asset in assets:
            if asset['name'].endswith('.7z'):
                return asset['browser_download_url']
        return None

    def get_assets_url(self):
        try:
            if cfg.update_source == "MirrorChyan":
                if cfg.mirrorchyan_cdk == "":
                    self.error_msg = "未设置 Mirror酱 CDK"
                    self.updateSignal.emit(UpdateStatus.FAILURE)
                    return None
                # 符合Mirror酱条件
                cdk = decrypt_string(cfg.mirrorchyan_cdk)
                response = self.check_update_info_mirrorchyan(cdk)
                if response.status_code == 200:
                    mirrorchyan_data = response.json()
                    if mirrorchyan_data["code"] == 0 and mirrorchyan_data["msg"] == "success":
                        url = mirrorchyan_data["data"]["url"]
                        return url
                else:
                    try:
                        mirrorchyan_data = response.json()
                        self.code = mirrorchyan_data["code"]
                        self.error_msg = mirrorchyan_data["msg"]

                        cdk_error_messages = {
                            7001: "Mirror酱 CDK 已过期",
                            7002: "Mirror酱 CDK 错误",
                            7003: "Mirror酱 CDK 今日下载次数已达上限",
                            7004: "Mirror酱 CDK 类型和待下载的资源不匹配",
                            7005: "Mirror酱 CDK 已被封禁"
                        }
                        if self.code in cdk_error_messages:
                            self.error_msg = cdk_error_messages[self.code]
                    except:
                        self.error_msg = "Mirror酱API请求失败"
                    self.updateSignal.emit(UpdateStatus.FAILURE)
                    return None
            else:
                if not cfg.update_prerelease_enable:
                    response = requests.get(
                        f"https://api.github.com/repos/{self.user}/{self.repo}/releases/latest",
                        timeout=10,
                        headers=cfg.useragent
                    )
                else:
                    response = requests.get(
                        f"https://api.github.com/repos/{self.user}/{self.repo}/releases",
                        timeout=10,
                        headers=cfg.useragent
                    )
                response.raise_for_status()
                data = response.json()[0] if cfg.update_prerelease_enable else response.json()

                assets_url = self.get_download_url_from_assets(data['assets'])

                # 如果没有可用的下载 URL，则发送成功信号并返回
                if assets_url is None:
                    self.updateSignal.emit(UpdateStatus.SUCCESS)
                    return
                return assets_url
        except Exception as e:
            # 异常处理，发送失败信号
            log.error(f"更新失败:{e}")
            self.updateSignal.emit(UpdateStatus.FAILURE)


@begin_and_finish_time_log(task_name="检查更新")
def check_update(self, timeout=5, flag=False):
    """检查更新功能函数。
    :param timeout: 超时时间，默认为5秒。
    :param flag: 更新检查的标志，默认为False。
    此函数主要用于启动一个更新线程，并监听更新状态。
    """

    def handler_update(status):
        """
        更新处理函数，根据不同的更新状态执行不同的操作。
        :param status: 更新状态。
        """
        if status == UpdateStatus.UPDATE_AVAILABLE:
            # 当有可用更新时，创建一个消息框对象并显示详细信息
            messages_box = MessageBoxUpdate(
                self.update_thread.title,
                self.update_thread.content,
                self.window()
            )
            if messages_box.exec():
                # 如果用户确认更新，则从指定的URL下载更新资源
                assets_url = self.update_thread.get_assets_url()
                if assets_url:
                    start_update_thread(assets_url)
        elif status == UpdateStatus.SUCCESS:
            # 显示当前为最新版本的信息
            bar = BaseInfoBar.success(
                title=QT_TRANSLATE_NOOP("BaseInfoBar", '当前是最新版本(＾∀＾●)'),
                content="",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=1000,
                parent=self
            )
        else:
            # 显示检查更新失败的信息
            bar = BaseInfoBar.warning(
                title=QT_TRANSLATE_NOOP("BaseInfoBar", '检测更新失败(╥╯﹏╰╥)'),
                content=self.update_thread.error_msg,
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=5000,
                parent=self
            )

    # 创建一个更新线程实例
    self.update_thread = UpdateThread(timeout, flag)
    # 将更新处理函数连接到更新线程的信号
    self.update_thread.updateSignal.connect(handler_update)
    # 启动更新线程
    self.update_thread.start()


def is_valid_url(url):
    """
    判断给定的URL是否有效。
    该函数通过解析URL的组成部分来验证其有效性。一个有效的URL应该包含方案（scheme）和网络位置（netloc）。
    参数:
    url (str): 待验证的URL。
    返回:
    bool: 如果URL有效则返回True，否则返回False。
    """
    from urllib.parse import urlparse
    try:
        # 解析URL
        result = urlparse(url)
        # 检查URL是否包含必要的组成部分
        return all([result.scheme, result.netloc])
    except:
        # 如果解析过程中出现异常，说明URL无效
        return False


def update(assets_url):
    """
    从给定的URL下载更新文件到本地。
    :param assets_url : 更新文件的URL。
    """
    # 检查URL是否有效
    if not is_valid_url(assets_url):
        log.error("更新失败：获取的URL无效 ")
        return

    # 提取文件名
    file_name = assets_url.split('/')[-1]
    if "7z" not in file_name:
        file_name = "AALC.zip"
    elif "AALC" in file_name:
        file_name = "AALC.7z"
    log.info(f"正在下载 {file_name} ...")

    try:
        # 发起HTTP请求获取文件
        response = requests.get(assets_url, stream=True, timeout=10)
        response.raise_for_status()  # 检查 HTTP 请求是否成功

        # 获取文件总大小
        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0

        # 创建保存临时文件的目录
        os.makedirs('update_temp', exist_ok=True)
        # 构建保存文件的完整路径
        file_path = os.path.join('update_temp', file_name)

        with requests.get(assets_url, stream=True) as r:
            with open(file_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=1024):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        progress = int(downloaded / total_size * 100)
                        mediator.update_progress.emit(progress)

        log.info(f"下载进度100%")

        if "OCR" in file_name:
            exe_path = os.path.abspath("./assets/binary/7za.exe")
            download_file_path = os.path.join("./update_temp", file_name)
            destination = os.path.abspath("./3rdparty")
            try:
                if os.path.exists(exe_path):
                    subprocess.run([exe_path, "x", download_file_path, f"-o{destination}", "-aoa"], check=True)
                else:
                    shutil.unpack_archive(download_file_path, destination)
                log.info("OCR解压完成，请重启AALC")
                return True
            except Exception as e:
                input("解压失败，按回车键重新解压. . .多次失败请手动下载更新")
                return False
        else:
            mediator.download_complete.emit(file_name)

    except requests.exceptions.RequestException as e:
        log.error(f"下载失败，请检查网络: {e}")
    except OSError as e:
        log.error(f"文件操作失败: {e}")
    finally:
        response.close()  # 确保关闭响应对象


def start_update_thread(assets_url):
    """
    在单独的线程中启动更新功能。
    :param assets_url: 更新文件的URL。
    """
    thread = Thread(target=update, args=(assets_url,))
    thread.start()
    return thread


def start_update(assert_name):
    source_file = os.path.abspath("./AALC Updater.exe")
    subprocess.Popen([source_file, assert_name], creationflags=subprocess.DETACHED_PROCESS)

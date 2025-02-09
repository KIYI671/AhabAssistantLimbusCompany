import os  # 导入os模块以便操作文件路径
import re
from enum import Enum

import markdown
import requests  # 导入requests模块，用于发送HTTP请求
from PyQt5.QtCore import QThread, pyqtSignal
from packaging.version import parse

from app.card.messagebox_custom import MessageBoxUpdate
from module.config import cfg
from module.decorator.decorator import begin_and_finish_time_log
from module.logger import log


class UpdateState(Enum):
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
    该类继承自 QThread，使用 PyQt5 的信号机制来通知 GUI 线程更新状态。
    """
    # 定义更新信号，用于通知主线程更新状态
    updateSignal = pyqtSignal(UpdateState)

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
        self.user = "KIYI671"
        self.repo = "AhabAssistantLimbusCompany"

    def run(self):
        """
        更新线程的主逻辑。
        检查是否有新版本，如果有，则发送更新可用信号；否则发送成功信号。
        """
        try:
            # 如果标志位为 False 且配置中的检查更新标志也为 False，则直接返回
            if self.flag and not cfg.check_update:
                return

            # 获取最新发布版本的信息
            data = self.fetch_latest_release_info()
            version = data['tag_name']
            content = self.remove_images_from_markdown(data['body'])
            assets_url = self.get_download_url_from_assets(data['assets'])

            # 如果没有可用的下载 URL，则发送成功信号并返回
            if assets_url is None:
                self.updateSignal.emit(UpdateState.SUCCESS)
                return

            # 比较当前版本和最新版本，如果最新版本更高，则准备更新
            if parse(version.lstrip('Vv')) > parse(cfg.version.lstrip('Vv')):
                self.title = f"发现新版本：{cfg.version}——> {version}\n更新日志:"
                self.content = "<style>a {color: #586f50; font-weight: bold;}</style>" + markdown.markdown(content)
                self.assets_url = assets_url
                self.updateSignal.emit(UpdateState.UPDATE_AVAILABLE)
            else:
                # 如果没有新版本，则发送成功信号
                self.updateSignal.emit(UpdateState.SUCCESS)
        except Exception as e:
            # 异常处理，发送失败信号
            log.ERROR(f"更新失败:{e}")
            self.updateSignal.emit(UpdateState.FAILURE)

    def fetch_latest_release_info(self):
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


@begin_and_finish_time_log(task_name="检查更新")
def check_update(self, timeout=5, flag=False):
    """检查更新功能函数。
    :param timeout: 超时时间，默认为5秒。
    :param flag: 更新检查的标志，默认为False。
    此函数主要用于启动一个更新线程，并监听更新状态。
    """

    def handler_update(state):
        """
        更新处理函数，根据不同的更新状态执行不同的操作。
        :param state: 更新状态。
        """
        if state == UpdateState.UPDATE_AVAILABLE:
            # 当有可用更新时，创建一个消息框对象并显示详细信息
            messages_box = MessageBoxUpdate(
                self.update_thread.title,
                self.update_thread.content,
                self.window()
            )
            if messages_box.exec_():
                # 如果用户确认更新，则从指定的URL下载更新资源
                assets_url = self.update_thread.assets_url
                update(assets_url)
            # assets_url = self.update_thread.assets_url
            # update(assets_url)
        elif state == UpdateState.SUCCESS:
            # 如果更新成功，记录日志信息
            log.INFO(f"当前是最新版本")
        elif state == UpdateState.FAILURE:
            # 如果更新失败，记录日志信息
            log.INFO(f"检查更新失败")

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
        log.ERROR("更新失败：获取的URL无效 ")
        return

    # 提取文件名
    file_name = assets_url.split('/')[-1]
    log.INFO(f"正在下载 {file_name} ...")

    try:
        # 发起HTTP请求获取文件
        response = requests.get(assets_url, stream=True, timeout=10)
        response.raise_for_status()  # 检查 HTTP 请求是否成功

        # 获取文件总大小
        total_size = int(response.headers.get('content-length', 0))
        block_size = 65536  # 设定每次读取的数据块大小
        downloaded = 0

        # 创建保存临时文件的目录
        os.makedirs('update_temp', exist_ok=True)
        # 构建保存文件的完整路径
        file_path = os.path.join('update_temp', file_name)

        # 保存文件到本地
        with open(file_path, 'wb') as f:
            last_logged_percent = -1  # 记录上次更新的进度百分比
            for data in response.iter_content(block_size):
                f.write(data)
                # 计算下载进度
                downloaded += len(data)
                percent = (downloaded / total_size) * 100 if total_size else 100

                # 只有当进度超过上次记录的进度加上5%时才更新日志
                if percent - last_logged_percent >= 5:
                    log.INFO(f"下载进度: {percent:.2f}%")
                    last_logged_percent = percent
        # TODO 不同语言展示不同信息 if cfg.language == 'en':
        log.INFO(f"下载完成,请手动解压 {file_path} 完成更新")
        log.INFO(f"Once the download is complete, please manually unzip {file_path} to complete the update")
    except requests.exceptions.RequestException as e:
        log.error(f"下载失败，请检查网络: {e}")
    except OSError as e:
        log.error(f"文件操作失败: {e}")
    finally:
        response.close()  # 确保关闭响应对象

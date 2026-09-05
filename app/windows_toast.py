import subprocess
import sys
import threading
from enum import Enum
from pathlib import Path
from typing import Callable

from module.platform_compat import IS_WINDOWS

if IS_WINDOWS:
    try:
        from windows_toasts import (
            InteractableWindowsToaster,
            Toast,
            ToastActivatedEventArgs,
            ToastAudio,
            ToastButton,
            ToastButtonColour,
            ToastDisplayImage,
            ToastDuration,
            ToastImage,
            ToastImagePosition,
            ToastInputSelectionBox,
            ToastInputTextBox,
            ToastSelection,
        )

        IMPORT_SUCCESS = True
    except ImportError:
        IMPORT_SUCCESS = False

try:
    from ..module.config import cfg
    from ..module.logger import log  # 正常导入方式
except ImportError:
    # 如果作为脚本直接运行，使用绝对路径
    import os

    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from module.config import cfg
    from module.logger import log

from PySide6.QtWidgets import QApplication

from app import mediator

APPID = "AALC_Notification"
"""Windows 注册表内的应用ID / Linux 通知应用名"""
APPNAME = "AALC"
"""显示的通知名称"""
ICONPATH = "assets/logo/my_icon.png"
"""图标路径"""


class TemplateToast(Enum):
    """通知模板"""

    NoneTemplate = 0
    TestTemplate = 1
    NormalTemplate = 2


# ---------------------------------------------------------------- Windows 实现
if IS_WINDOWS:
    import winreg

    def _register_hkey(appId: str = APPID, appName: str = APPNAME, iconPath: Path | None = None):
        """实际注册行为"""
        winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)
        keyPath = f"SOFTWARE\\Classes\\AppUserModelId\\{appId}"
        with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, keyPath) as masterKey:
            winreg.SetValueEx(masterKey, "DisplayName", 0, winreg.REG_SZ, appName)
            if iconPath:
                winreg.SetValueEx(masterKey, "IconUri", 0, winreg.REG_SZ, str(iconPath))

    def _register_toast(key_name: str = APPID, app_name: str = APPNAME, icon_path: str = ICONPATH) -> bool:
        """注册通知"""
        try:
            relative_path = icon_path

            absolute_path = Path(relative_path).resolve()

            _register_hkey(key_name, app_name, absolute_path)
            log.debug(f"成功注册 AALC Toast, 图标路径: {absolute_path}")
            return True

        except Exception as e:
            log.error(f"通过注册表注册通知时出错: {type(e)}: {e}")
            return False

    def unregister_toast(appId: str = APPID):
        """注销注册的通知"""
        _unregister_toast(appId)

    def _unregister_toast(appId: str):
        """实际注销行为"""
        keyPath = "SOFTWARE\\Classes\\AppUserModelId\\"
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, keyPath) as uperKey:
                winreg.DeleteKey(uperKey, appId)
        except Exception as e:
            log.error(f"通过注册表注销通知时出错: {type(e)}: {e}")

    def _normal_template_toast(title, msg, app_id, on_activated, **kwargs):
        """常用的模板通知"""
        toaster = InteractableWindowsToaster("AALC", app_id)
        toaster.clear_toasts()
        hero_image = ToastDisplayImage.fromPath(imagePath=ICONPATH, position=ToastImagePosition.Hero)

        def on_click(args: ToastActivatedEventArgs):
            log.debug(f"用户点击了通知，参数: {args.arguments}, 输入: {args.inputs}")
            if args.arguments == "close":
                mediator.kill_signal.emit()

        confirm_botton = ToastButton(content=QApplication.translate("WindowsToast", "知道了"), arguments="confirm")
        close_botton = ToastButton(
            content=QApplication.translate("WindowsToast", "关闭 AALC"),
            arguments="close",
            colour=ToastButtonColour.Red,
        )
        toast = Toast(
            text_fields=[title, msg] if isinstance(msg, str) else [title] + msg,
            duration=ToastDuration.Default,
            images=[hero_image],
            actions=[confirm_botton, close_botton],
        )

        toast.on_activated = on_activated if on_activated is not None else on_click
        toaster.show_toast(toast)

    def _test_template_toast(title, msg, app_id, on_activated):
        """测试用的模板通知
        展示了各种功能"""
        # 创建通知管理器
        toaster = InteractableWindowsToaster("AALC", app_id)
        # 清除之前的通知以刷新通知名称和图标
        toaster.clear_toasts()
        # 创建图标, *altText* 是无障碍阅读器使用的文本
        # 无位置参数为默认位置, 即通知内容中
        image1 = ToastDisplayImage.fromPath(imagePath=ICONPATH, altText="这是一个图标")
        # Hero 位置为通知上方的大图
        image2 = ToastDisplayImage.fromPath(imagePath=ICONPATH, position=ToastImagePosition.Hero)
        # AppLogo 位置为通知左侧的小图
        image3 = ToastDisplayImage.fromPath(imagePath=ICONPATH, position=ToastImagePosition.AppLogo)
        # 按钮的图标 压缩为16x16
        botton_image = ToastImage(ICONPATH)
        # 创建按钮, *tooltip* 是无障碍阅读器使用的文本
        # arguments 是用户点击按钮时传递的参数
        botton1 = ToastButton(
            content="都是你的错",
            arguments="action=botton1",
            image=botton_image,
            tooltip="点我点我",
        )
        # colour 定义按钮颜色 有默认, 绿色, 红色三种
        botton2 = ToastButton(
            content="以实玛丽",
            arguments="action=botton2",
            image=botton_image,
            colour=ToastButtonColour.Green,
        )
        botton3 = ToastButton(
            content="伊莎玛拉",
            arguments="action=botton3",
            image=botton_image,
            colour=ToastButtonColour.Red,
        )
        # inContextMenu 定义按钮是否放在右上角的菜单中, 对于旧版本的 Windows (8+), 该按钮会被放置在通知下方, 即正常按钮的位置
        hide_botton = ToastButton(
            content="亚哈",
            arguments="action=hide",
            inContextMenu=True,
            image=botton_image,
            colour=ToastButtonColour.Red,
        )
        # 构建通知
        toast = Toast(
            text_fields=[title],
            duration=ToastDuration.Default,
            images=[image1, image2, image3],
            actions=[botton1, botton2, botton3, hide_botton],
        )
        # 添加发送通知时的音频
        if cfg.resonate_with_Ahab:
            from random import randint

            toast.audio = ToastAudio(Path(r"assets\audio\This_is_all_your_fault_" + f"{randint(1, 4)}.mp3"))

        # 定义回调函数
        def on_click(args: ToastActivatedEventArgs):
            log.info(f"用户点击了通知，参数: {args.arguments}, 输入: {args.inputs}")

        # 设置回调函数
        if on_activated is not None:
            toast.on_activated = on_activated
        else:
            toast.on_activated = on_click

        if isinstance(msg, str):
            toast.text_fields.append(msg)
        else:
            toast.text_fields += msg

        # 发送通知
        toaster.show_toast(toast)

    def _send_template_toast(
        title: str = "AALC",
        msg: str | list[str] = "默认消息",
        app_name: str = APPNAME,
        app_id: str = APPID,
        icon_path: str = ICONPATH,
        template: TemplateToast = TemplateToast.NoneTemplate,
        on_activated: Callable | None = None,
        **kwargs,
    ) -> bool:
        """发送模板通知"""
        try:
            _register_toast(app_id, app_name, icon_path)
            if template is TemplateToast.TestTemplate:
                _test_template_toast(title, msg, app_id, on_activated)
            elif template is TemplateToast.NormalTemplate:
                _normal_template_toast(title, msg, app_id, on_activated, **kwargs)
            log.debug(f"发送模板通知成功: {template.name}")
            return True
        except Exception as e:
            log.error(f"发送模板通知失败: {type(e)}: {e}")
            return False


# ---------------------------------------------------------------- Linux 实现
else:

    def unregister_toast(appId: str = APPID):
        """注销注册的通知（Linux 无需注册，no-op）"""

    def _notify_send(
        title: str,
        body: str,
        icon_path: str = ICONPATH,
        actions: list[str] | None = None,
        wait: bool = False,
    ) -> str | None:
        """调用 notify-send 发送通知。

        Args:
            actions: 透传给 --action 的参数列表，形如 ["confirm=知道了", "close=关闭 AALC"]
        Returns:
            wait=True 时返回用户点击的 action key，否则返回 None
        """
        if subprocess.run(["bash", "-c", "command -v notify-send"], capture_output=True).returncode != 0:
            log.warning("未找到 notify-send，无法发送桌面通知")
            return None

        command = ["notify-send", "-a", APPNAME]
        if Path(icon_path).exists():
            command += ["-i", icon_path]
        if actions:
            for action in actions:
                command += ["--action", action]
        if wait:
            command.append("--wait")
        command += [title, body]

        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=300)  # noqa: S603
            if wait:
                return result.stdout.strip() or None
            return None
        except Exception as e:
            log.debug(f"发送通知失败: {e}")
            return None

    def _handle_notification_actions(action_key: str | None) -> None:
        """处理用户在通知上点击的按钮"""
        if not action_key:
            return
        log.debug(f"用户点击了通知按钮: {action_key}")
        if action_key == "close":
            mediator.kill_signal.emit()

    def _send_template_toast(
        title: str = "AALC",
        msg: str | list[str] = "默认消息",
        app_name: str = APPNAME,
        app_id: str = APPID,
        icon_path: str = ICONPATH,
        template: TemplateToast = TemplateToast.NoneTemplate,
        on_activated: Callable | None = None,
        **kwargs,
    ) -> bool:
        """发送模板通知（Linux: 通过 notify-send，交互按钮后台等待用户操作）"""
        body = msg if isinstance(msg, str) else "\n".join(msg)
        try:
            if template is TemplateToast.NoneTemplate:
                _notify_send(title, body, icon_path)
                return True

            # 交互式通知：--wait 会阻塞到用户关闭通知，放到后台线程执行
            def _show_interactive():
                action_key = _notify_send(
                    title,
                    body,
                    icon_path,
                    actions=[
                        f"confirm={QApplication.translate('WindowsToast', '知道了')}",
                        f"close={QApplication.translate('WindowsToast', '关闭 AALC')}",
                    ],
                    wait=True,
                )
                if on_activated is not None:
                    try:
                        on_activated(action_key)
                        return
                    except Exception as e:
                        log.debug(f"通知回调执行失败: {e}")
                _handle_notification_actions(action_key)

            threading.Thread(target=_show_interactive, daemon=True).start()
            log.debug(f"发送模板通知成功: {template.name}")
            return True
        except Exception as e:
            log.error(f"发送模板通知失败: {type(e)}: {e}")
            return False


def send_toast(
    title: str,
    msg: str | list[str],
    app_name: str = APPNAME,
    app_id: str = APPID,
    icon_path: str = ICONPATH,
    template: TemplateToast = TemplateToast.NoneTemplate,
    on_activated: Callable | None = None,
    **kwargs,
) -> bool:
    """发送系统通知（Windows Toast / Linux 桌面通知）
    Args:
        title (str): 通知标题
        msg (str | list[str]): 通知内容，支持多行 ( Windows 最多2行)
        app_name (str, optional): 应用名称.
        app_id (str, optional): 应用ID.
        icon_path (str, optional): 图标路径.
        template (TemplateToast, optional): 使用的模板.
        on_activated (Callable, optional): 用户点击通知时的回调函数.
        **kwargs: 其他参数，传递给模板函数.
    Returns:
        bool: 发送是否成功
    """
    if IS_WINDOWS and IMPORT_SUCCESS is False:
        return True
    if template is not TemplateToast.NoneTemplate:
        title = QApplication.translate("WindowsToast", title)
        if isinstance(msg, str):
            msg = QApplication.translate("WindowsToast", msg)
        else:
            for index, content in enumerate(msg):
                msg[index] = QApplication.translate("WindowsToast", content)

        return _send_template_toast(title, msg, app_name, app_id, icon_path, template, on_activated, **kwargs)

    if IS_WINDOWS:
        try:
            _register_toast(app_id, app_name, icon_path)

            return True
        except Exception as e:
            log.error(f"发送 Windows 通知失败: {type(e)}: {e}")

            return False
    else:
        try:
            _notify_send(title, msg if isinstance(msg, str) else "\n".join(msg), icon_path)
            return True
        except Exception as e:
            log.error(f"发送通知失败: {type(e)}: {e}")
            return False


if __name__ == "__main__":
    send_toast(
        "运行结束",
        ["第一行", "第二行", "第三行"],
        template=TemplateToast.TestTemplate,
    )

    # sleep(5)
    # unregister_toast(APPID)

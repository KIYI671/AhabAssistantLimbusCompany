from windows_toasts import (
    InteractableWindowsToaster,
    Toast,
    ToastInputTextBox,
    ToastInputSelectionBox,
    ToastSelection,
    ToastButton,
    ToastDuration,
    ToastDisplayImage,
    ToastImagePosition,
    ToastImage,
    ToastButtonColour,
    ToastActivatedEventArgs,
    ToastAudio,
)

try:
    from ..module.logger import log  # 正常导入方式
    from ..module.config import cfg
except ImportError:
    # 如果作为脚本直接运行，使用绝对路径
    import sys
    import os

    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from module.logger import log
    from module.config import cfg

from pathlib import Path
from enum import Enum
from app import mediator
from typing import Callable
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QT_TRANSLATE_NOOP
import winreg
import sys

APPID = "AALC_Notification"
APPNAME = "AALC"
ICONPATH = r"assets\logo\my_icon.png"


class TemplateToast(Enum):
    NoneTemplate = 0
    TestTemplate = 1
    NormalTemplate = 2


def _register_hkey(
    appId: str = APPID, appName: str = APPNAME, iconPath: Path | None = None
):
    winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)
    keyPath = f"SOFTWARE\\Classes\\AppUserModelId\\{appId}"
    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, keyPath) as masterKey:
        winreg.SetValueEx(masterKey, "DisplayName", 0, winreg.REG_SZ, appName)
        if iconPath:
            winreg.SetValueEx(masterKey, "IconUri", 0, winreg.REG_SZ, str(iconPath))


def _register_toast(
    key_name: str = APPID, app_name: str = APPNAME, icon_path: str = ICONPATH
) -> bool:
    try:
        # 打开注册表键

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
    keyPath = "SOFTWARE\\Classes\\AppUserModelId\\"
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, keyPath) as uperKey:
        winreg.DeleteKey(uperKey, appId)


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


def _normal_template_toast(title, msg, app_id, on_activated, **kwargs):
    toaster = InteractableWindowsToaster("AALC", app_id)
    toaster.clear_toasts()
    hero_image = ToastDisplayImage.fromPath(
        imagePath=ICONPATH, position=ToastImagePosition.Hero
    )

    def on_click(args: ToastActivatedEventArgs):
        log.debug(f"用户点击了通知，参数: {args.arguments}, 输入: {args.inputs}")
        if args.arguments == "close":
            mediator.kill_signal.emit()
    confirm_botton = ToastButton(
        content=QApplication.translate("WindowsToast", "知道了"), arguments="confirm"
    )
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
    toaster = InteractableWindowsToaster("AALC", app_id)
    toaster.clear_toasts()
    image1 = ToastDisplayImage.fromPath(imagePath=ICONPATH, altText="这是一个图标")
    image2 = ToastDisplayImage.fromPath(
        imagePath=ICONPATH, position=ToastImagePosition.Hero
    )

    image3 = ToastDisplayImage.fromPath(
        imagePath=ICONPATH, position=ToastImagePosition.AppLogo
    )
    botton_image = ToastImage(ICONPATH)
    botton1 = ToastButton(
        content="都是你的错",
        arguments="action=botton1",
        image=botton_image,
        tooltip="点我点我",
    )
    botton_image = ToastImage(ICONPATH)
    botton2 = ToastButton(
        content="以实玛丽",
        arguments="action=botton2",
        image=botton_image,
        colour=ToastButtonColour.Green,
    )
    botton_image = ToastImage(ICONPATH)
    botton3 = ToastButton(
        content="伊莎玛拉",
        arguments="action=botton3",
        image=botton_image,
        colour=ToastButtonColour.Red,
    )
    hide_botton = ToastButton(
        content="亚哈",
        arguments="action=hide",
        inContextMenu=True,
        image=botton_image,
        colour=ToastButtonColour.Red,
    )
    toast = Toast(
        text_fields=[title],
        duration=ToastDuration.Default,
        images=[image1, image2, image3],
        actions=[botton1, botton2, botton3, hide_botton],
    )
    if cfg.resonate_with_Ahab:
        from random import randint

        toast.audio = ToastAudio(
            Path(r"assets\audio\This_is_all_your_fault_" + f"{randint(1, 4)}.mp3")
        )

    def on_click(args: ToastActivatedEventArgs):
        log.info(f"用户点击了通知，参数: {args.arguments}, 输入: {args.inputs}")

    if on_activated is not None:
        toast.on_activated = on_activated
    else:
        toast.on_activated = on_click

    if isinstance(msg, str):
        toast.text_fields.append(msg)
    else:
        toast.text_fields += msg

    toaster.show_toast(toast)


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
    """发送 Windows 通知
    Args:
        title (str): 通知标题
        msg (str | list[str]): 通知内容，支持多行 ( Windows 最多2行)
        app_name (str, optional): 应用名称.
        app_id (str, optional): 应用ID.
        icon_path (str, optional): 图标路径.
        template (TemplateToast, optional): 使用的模板.
    Returns:
        bool: 发送是否成功
    """
    if template is not TemplateToast.NoneTemplate:
        title = QApplication.translate("WindowsToast", title)
        if isinstance(msg, str):
            msg = QApplication.translate("WindowsToast", msg)
        else:
            for index, content in enumerate(msg):
                msg[index] = QApplication.translate("WindowsToast", content)

        return _send_template_toast(
            title, msg, app_name, app_id, icon_path, template, on_activated, **kwargs
        )

    try:
        _register_toast(app_id, app_name, icon_path)

        return True
    except Exception as e:
        log.error(f"发送 Windows 通知失败: {type(e)}: {e}")

        return False


if __name__ == "__main__":
    send_toast(
        "运行结束",
        ["第一行", "第二行", "第三行"],
        template=TemplateToast.NormalTemplate,
    )
    from time import sleep

    sleep(5)
    # unregister_toast(APPID)

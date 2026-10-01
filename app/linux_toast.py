"""Linux 桌面通知，通过 notify-send 发送并处理通知按钮。"""

import shutil
import subprocess
import threading
from pathlib import Path

from PySide6.QtWidgets import QApplication

from app import mediator
from module.logger import log
from module.platform_compat import _external_process_environment


def send_linux_toast(title, msg, app_name, icon_path, template, on_activated) -> bool:
    from app.windows_toast import TemplateToast

    executable = shutil.which("notify-send")
    if executable is None:
        log.warning("未找到 notify-send，无法发送桌面通知")
        return False
    if template is not TemplateToast.NoneTemplate:
        title = QApplication.translate("WindowsToast", title)
        if isinstance(msg, str):
            msg = QApplication.translate("WindowsToast", msg)
        else:
            msg = [QApplication.translate("WindowsToast", line) for line in msg]
    command = [executable, "-a", app_name]
    if icon_path and Path(icon_path).is_file():
        command.extend(["-i", str(Path(icon_path).resolve())])
    interactive = template is TemplateToast.NormalTemplate
    if interactive:
        command.extend([
            "--action=confirm=" + QApplication.translate("WindowsToast", "知道了"),
            "--action=close=" + QApplication.translate("WindowsToast", "关闭 AALC"),
            "--wait",
        ])
    command.extend([title, msg if isinstance(msg, str) else "\n".join(msg)])

    def show() -> bool:
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=True,
                timeout=300,
                env=_external_process_environment(),
            )
            action = result.stdout.strip()
            if interactive and action:
                if on_activated is not None:
                    try:
                        on_activated(action)
                        return True
                    except Exception as error:
                        log.debug(f"通知回调执行失败: {error}")
                if action == "close":
                    mediator.kill_signal.emit()
            return True
        except Exception as error:
            log.error(f"发送 Linux 通知失败: {error}")
            return False

    if interactive:
        threading.Thread(target=show, daemon=True).start()
        return True
    return show()

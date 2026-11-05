"""Optional, removable mirror-run journal and its read-only viewer.

Importing this module performs no file access and does not import Qt. The
application calls ``record_result`` only after a mirror run has actually ended.
"""

import math
import os
import sys
import tempfile
import time
from collections import deque
from datetime import datetime
from pathlib import Path
from threading import RLock

ROOT = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
LOG_PATH = ROOT / "mirror_run_log.md"
LAST_ERROR = ""
_LOCK = RLock()
_MARKER = "<!-- AALC_MIRROR_RUN_LOG enabled={enabled} -->"
_RECORDED_ATTRIBUTE = "_mirror_run_log_recorded_start_time"
_MISSING = object()
_HEADER = (
    "\n# 镜牢长期日志\n\n"
    "| 结束时间 | 队伍 | 用时 | 层数 | 成功 | 原因 |\n"
    "| --- | --- | --- | --- | --- | --- |\n"
)
_REASON_NAMES = {
    "completed": "完成镜牢",
    "floor_limit": "达到刷牢层数",
    "run_finished": "镜牢流程结束",
    "observation_failed": "主题卡包观测失败，已退出并放弃奖励",
    "attempts_exhausted": "关卡尝试次数耗尽，已退出并放弃奖励",
    "battle_failures": "连续战败，原版流程退出重开",
    "insufficient_survivors": "幸存罪人不足，原版流程退出重开",
    "previous_settlement": "接续上一局结算",
    "unfinished_settlement": "镜牢未完成，已放弃奖励",
}


def _error(error):
    global LAST_ERROR
    LAST_ERROR = f"{type(error).__name__}: {error}"


def _enabled_unlocked():
    try:
        with LOG_PATH.open("r", encoding="utf-8-sig") as stream:
            return stream.readline().strip() == _MARKER.format(enabled=1)
    except FileNotFoundError:
        return False
    except Exception as error:
        _error(error)
        return False


def tool_available():
    """Deleting the external Python file disables cached/frozen hooks too."""
    try:
        return (ROOT / "mirror_run_log.py").is_file()
    except OSError:
        return False


def is_enabled():
    """Missing or unreadable Markdown means recording is disabled."""
    with _LOCK:
        return _enabled_unlocked()


def _replace_text(text):
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", newline="", dir=LOG_PATH.parent,
            prefix=".mirror_run_log-", suffix=".tmp", delete=False,
        ) as stream:
            temporary_path = Path(stream.name)
            stream.write(text)
        os.replace(temporary_path, LOG_PATH)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def set_enabled(enabled):
    """Persist the switch in the Markdown, retaining existing journal rows."""
    global LAST_ERROR
    with _LOCK:
        try:
            try:
                existing = LOG_PATH.read_text(encoding="utf-8-sig")
            except FileNotFoundError:
                if not enabled:
                    LAST_ERROR = ""
                    return True
                existing = _HEADER
            first, separator, remaining = existing.partition("\n")
            if first.strip() in {_MARKER.format(enabled=0), _MARKER.format(enabled=1)}:
                body = separator + remaining
            else:
                body = "\n" + existing
            _replace_text(_MARKER.format(enabled=int(bool(enabled))) + body)
            LAST_ERROR = ""
            return True
        except Exception as error:
            _error(error)
            return False


def read_log(last_lines=200):
    """Read a bounded preview; the on-disk Markdown keeps the full history."""
    with _LOCK:
        try:
            with LOG_PATH.open("r", encoding="utf-8-sig") as stream:
                return "".join(deque(stream, maxlen=max(1, int(last_lines)))).rstrip()
        except FileNotFoundError:
            return "尚无日志。启用后会创建日志文件。"
        except Exception as error:
            _error(error)
            return "无法读取日志，请查看下方错误信息。"


def _cell(value):
    return str(value).replace("\\", "\\\\").replace("|", "\\|").replace("\r\n", "\n").replace("\r", "\n").replace("\n", "<br>")


def _elapsed(start_time, end_time):
    try:
        seconds = float(end_time) - float(start_time)
        if not math.isfinite(seconds):
            return "未知"
        seconds = max(0, int(seconds))
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02}:{minutes:02}:{seconds:02}"
    except (TypeError, ValueError, OverflowError):
        return "未知"


def _floor_text(adventure, success):
    floor = getattr(adventure, "floor", None)
    if isinstance(floor, bool) or not isinstance(floor, (int, float)) or not math.isfinite(floor) or floor <= 0:
        return "未知"
    floor = int(floor)
    if getattr(adventure, "floor_limit_exit", False):
        target = getattr(adventure, "mirror_floor_limit", None)
        if isinstance(target, int) and not isinstance(target, bool) and 1 <= target <= 5 and floor > target:
            return f"完成 {target} 层"
    if success is True:
        return f"完成 {floor} 层"
    return f"到达第 {floor} 层"


def record_result(adventure, success, reason=""):
    """Append one confirmed end per instance/start_time; never block the game.

    ``success`` is True, False, or None for an unknown result. It is deliberately
    not inferred from truthy outcome enums. A restart resets ``start_time`` and
    can therefore produce another row without making battle retries new runs.
    """
    global LAST_ERROR
    with _LOCK:
        try:
            if not tool_available() or not _enabled_unlocked():
                return False
            start = getattr(adventure, "start_time", None)
            if getattr(adventure, _RECORDED_ATTRIBUTE, _MISSING) == start:
                return False
            end = time.time()
            result = "是" if success is True else "否" if success is False else "未确认"
            detail = _REASON_NAMES.get(reason, str(reason)) if reason else "—"
            if getattr(adventure, "bequest_from_the_previous_game", False):
                detail = f"{detail}；接续结算，计时不完整"
            team = getattr(adventure, "team_number", None)
            if team is None or team == "":
                team = getattr(adventure, "team_order", "未知")
            fields = (
                datetime.fromtimestamp(end).strftime("%Y-%m-%d %H:%M:%S"),
                team, _elapsed(start, end), _floor_text(adventure, success), result, detail,
            )
            row = "| " + " | ".join(_cell(value) for value in fields) + " |\n"
            # r+ intentionally cannot recreate a Markdown deleted after the
            # enabled check. A missing file remains an explicit disable switch.
            with LOG_PATH.open("r+b") as stream:
                if stream.readline().decode("utf-8-sig").strip() != _MARKER.format(enabled=1):
                    return False
                stream.seek(0, os.SEEK_END)
                position = stream.tell()
                if position:
                    stream.seek(position - 1)
                    final_character = stream.read(1)
                    stream.seek(0, os.SEEK_END)
                    if final_character != b"\n":
                        stream.write(b"\n")
                stream.write(row.encode("utf-8"))
                stream.flush()
            setattr(adventure, _RECORDED_ATTRIBUTE, start)
            LAST_ERROR = ""
            return True
        except FileNotFoundError:
            # The user may remove the journal while a run is ending.
            return False
        except Exception as error:
            _error(error)
            return False


def create_window(parent=None):
    """Create a passive viewer; Qt is imported only when opening the tool."""
    from PySide6.QtCore import Qt, QUrl
    from PySide6.QtGui import QDesktopServices
    from PySide6.QtWidgets import (
        QCheckBox,
        QDialog,
        QHBoxLayout,
        QLabel,
        QPlainTextEdit,
        QPushButton,
        QVBoxLayout,
    )

    window = QDialog(parent)
    window.setWindowTitle("镜牢长期日志")
    window.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
    window.resize(820, 520)
    layout = QVBoxLayout(window)
    enabled = QCheckBox("记录每局镜牢", window)
    enabled.setToolTip("默认关闭。每局结束后记录用时、层数、成功与失败原因；单场战斗重试不会新增记录。删除日志文件会停止记录。")
    layout.addWidget(enabled)
    path = QLabel(str(LOG_PATH), window)
    path.setWordWrap(True)
    path.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    path.setToolTip("日志与独立工具 mirror_run_log.py 保存在程序目录。两者均可删除；已有队伍配置和刷牢流程保持不变。")
    layout.addWidget(path)
    preview = QPlainTextEdit(window)
    preview.setReadOnly(True)
    preview.setToolTip("这里只显示最新 200 行。完整记录保存在 Markdown 文件中；点击刷新读取最新内容。")
    layout.addWidget(preview, 1)
    buttons = QHBoxLayout()
    refresh_button = QPushButton("刷新", window)
    refresh_button.setToolTip("重新读取日志，不会操作游戏。")
    open_button = QPushButton("打开 Markdown", window)
    open_button.setToolTip("使用系统默认程序打开完整日志。")
    buttons.addWidget(refresh_button)
    buttons.addWidget(open_button)
    buttons.addStretch()
    layout.addLayout(buttons)
    error_label = QLabel(window)
    error_label.setWordWrap(True)
    error_label.setStyleSheet("color: #c74a4a;")
    layout.addWidget(error_label)

    def refresh():
        enabled.blockSignals(True)
        enabled.setChecked(is_enabled())
        enabled.blockSignals(False)
        preview.setPlainText(read_log())
        error_label.setText(LAST_ERROR)
        error_label.setVisible(bool(LAST_ERROR))
        open_button.setEnabled(LOG_PATH.is_file())

    def toggle(value):
        set_enabled(value)
        refresh()

    def open_markdown():
        if LOG_PATH.is_file():
            if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(LOG_PATH))):
                error_label.setText("无法打开日志，请从上方路径手动打开。")
                error_label.show()
        else:
            refresh()

    enabled.toggled.connect(toggle)
    refresh_button.clicked.connect(refresh)
    open_button.clicked.connect(open_markdown)
    refresh()
    return window



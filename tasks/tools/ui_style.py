import os

from qfluentwidgets import isDarkTheme


_THEMES = {
    "dark": {
        "window_bg": "#1f1f1f",
        "window_fg": "#f0f0f0",
        "control_bg": "#2b2b2b",
        "button_hover": "#3a3a3a",
        "border": "#555",
        "scrollbar_bg": "#2b2b2b",
        "scrollbar_handle": "#666",
        "scrollbar_handle_hover": "#666",
        "splitter": "#555",
        "arrow": "#f0f0f0",
    },
    "light": {
        "window_bg": "#ffffff",
        "window_fg": "#202020",
        "control_bg": "#ffffff",
        "button_hover": "#f5f5f5",
        "border": "#d0d0d0",
        "scrollbar_bg": "#f3f3f3",
        "scrollbar_handle": "#c8c8c8",
        "scrollbar_handle_hover": "#a8a8a8",
        "splitter": "#d0d0d0",
        "arrow": "#202020",
    },
}

_QSS = """\
{selector} {{
    background-color: {window_bg};
    color: {window_fg};
}}
QLabel {{
    background-color: transparent;
    color: {window_fg};
}}
QCheckBox {{
    background-color: transparent;
    color: {window_fg};
}}
QPushButton {{
    background-color: {control_bg};
    color: {window_fg};
    border: 1px solid {border};
    border-radius: 4px;
    padding: 3px 12px;
}}
QPushButton:hover {{
    background-color: {button_hover};
}}
QTextEdit {{
    background-color: {control_bg};
    color: {window_fg};
    border: 1px solid {border};
    border-radius: 4px;
}}
QLineEdit, QComboBox, QTableWidget, QTreeWidget, QListWidget {{
    background-color: {control_bg};
    color: {window_fg};
    border: 1px solid {border};
    border-radius: 4px;
    padding: 3px 6px;
    selection-background-color: #9c080b;
    selection-color: #ffffff;
}}
QComboBox::drop-down {{
    border: none;
    width: 24px;
}}
QComboBox::down-arrow {{
    width: 0px;
    height: 0px;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid {arrow};
    margin-right: 8px;
}}
QComboBox QAbstractItemView {{
    background-color: {control_bg};
    color: {window_fg};
    border: 1px solid {border};
    border-radius: 4px;
    selection-background-color: #9c080b;
    selection-color: #ffffff;
    outline: none;
}}
QGroupBox {{
    color: {window_fg};
    border: 1px solid {border};
    border-radius: 4px;
    margin-top: 8px;
    padding-top: 8px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 8px;
    padding: 0 4px;
}}
QHeaderView::section, QStatusBar {{
    background-color: {control_bg};
    color: {window_fg};
    border: 1px solid {border};
}}
QSplitter::handle {{
    background-color: {splitter};
}}
QSplitter::handle:horizontal {{
    width: 1px;
    margin: 0 4px;
}}
QSplitter::handle:vertical {{
    height: 1px;
    margin: 4px 0;
}}
QScrollBar:vertical {{
    background-color: {scrollbar_bg};
    width: 10px;
    margin: 0;
    border: none;
}}
QScrollBar::handle:vertical {{
    background-color: {scrollbar_handle};
    min-height: 24px;
    border-radius: 5px;
}}
QScrollBar::handle:vertical:hover {{
    background-color: {scrollbar_handle_hover};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}
QScrollBar:horizontal {{
    background-color: {scrollbar_bg};
    height: 10px;
    margin: 0;
    border: none;
}}
QScrollBar::handle:horizontal {{
    background-color: {scrollbar_handle};
    min-width: 24px;
    border-radius: 5px;
}}
QScrollBar::handle:horizontal:hover {{
    background-color: {scrollbar_handle_hover};
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
}}
"""


def get_status_label_style() -> str:
    if isDarkTheme():
        return "QLabel { background-color: #2b2b2b; color: #f0f0f0; padding: 5px; border: 1px solid #555; }"
    return "QLabel { background-color: #f0f0f0; color: #202020; padding: 5px; border: 1px solid #ccc; }"


def get_tool_window_style(widget_selector: str) -> str:
    theme = _THEMES["dark"] if isDarkTheme() else _THEMES["light"]
    return _QSS.format(selector=widget_selector, **theme)


def apply_tool_window_theme(widget, widget_selector: str) -> None:
    dark = isDarkTheme()
    widget.setStyleSheet(get_tool_window_style(widget_selector))
    if os.name == "nt":
        _set_windows_title_bar_theme(widget, dark=dark)


def _set_windows_title_bar_theme(widget, dark: bool) -> None:
    try:
        import ctypes
        from ctypes import wintypes

        hwnd = int(widget.winId())
        value = ctypes.c_int(1 if dark else 0)
        for attr in (20, 19):
            result = ctypes.windll.dwmapi.DwmSetWindowAttribute(
                wintypes.HWND(hwnd),
                attr,
                ctypes.byref(value),
                ctypes.sizeof(value),
            )
            if result == 0:
                break
    except Exception:
        pass

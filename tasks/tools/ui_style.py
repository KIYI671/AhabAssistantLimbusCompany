import os

from qfluentwidgets import isDarkTheme


def get_status_label_style() -> str:
    if isDarkTheme():
        return "QLabel { background-color: #2b2b2b; color: #f0f0f0; padding: 5px; border: 1px solid #555; }"
    return "QLabel { background-color: #f0f0f0; color: #202020; padding: 5px; border: 1px solid #ccc; }"


def get_tool_window_style(widget_selector: str) -> str:
    if isDarkTheme():
        return f"""
            {widget_selector} {{
                background-color: #1f1f1f;
                color: #f0f0f0;
            }}
            QLabel {{
                background-color: transparent;
                color: #f0f0f0;
            }}
            QCheckBox {{
                background-color: transparent;
                color: #f0f0f0;
            }}
            QPushButton {{
                background-color: #2b2b2b;
                color: #f0f0f0;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 3px 12px;
            }}
            QPushButton:hover {{
                background-color: #3a3a3a;
            }}
            QTextEdit {{
                background-color: #2b2b2b;
                color: #f0f0f0;
                border: 1px solid #555;
                border-radius: 4px;
            }}
            QLineEdit, QComboBox, QTableWidget, QTreeWidget, QListWidget {{
                background-color: #2b2b2b;
                color: #f0f0f0;
                border: 1px solid #555;
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
                border-top: 5px solid #f0f0f0;
                margin-right: 8px;
            }}
            QComboBox QAbstractItemView {{
                background-color: #2b2b2b;
                color: #f0f0f0;
                border: 1px solid #555;
                border-radius: 4px;
                selection-background-color: #9c080b;
                selection-color: #ffffff;
                outline: none;
            }}
            QGroupBox {{
                color: #f0f0f0;
                border: 1px solid #555;
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
                background-color: #2b2b2b;
                color: #f0f0f0;
                border: 1px solid #555;
            }}
            QSplitter::handle {{
                background-color: #555;
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
                background-color: #2b2b2b;
                width: 10px;
                margin: 0;
                border: none;
            }}
            QScrollBar::handle:vertical {{
                background-color: #666;
                min-height: 24px;
                border-radius: 5px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QScrollBar:horizontal {{
                background-color: #2b2b2b;
                height: 10px;
                margin: 0;
                border: none;
            }}
            QScrollBar::handle:horizontal {{
                background-color: #666;
                min-width: 24px;
                border-radius: 5px;
            }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                width: 0px;
            }}
        """
    return f"""
        {widget_selector} {{
            background-color: #ffffff;
            color: #202020;
        }}
        QLabel {{
            background-color: transparent;
            color: #202020;
        }}
        QCheckBox {{
            background-color: transparent;
            color: #202020;
        }}
        QPushButton {{
            background-color: #ffffff;
            color: #202020;
            border: 1px solid #d0d0d0;
            border-radius: 4px;
            padding: 3px 12px;
        }}
        QPushButton:hover {{
            background-color: #f5f5f5;
        }}
        QTextEdit {{
            background-color: #ffffff;
            color: #202020;
            border: 1px solid #d0d0d0;
            border-radius: 4px;
        }}
        QLineEdit, QComboBox, QTableWidget, QTreeWidget, QListWidget {{
            background-color: #ffffff;
            color: #202020;
            border: 1px solid #d0d0d0;
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
            border-top: 5px solid #202020;
            margin-right: 8px;
        }}
        QComboBox QAbstractItemView {{
            background-color: #ffffff;
            color: #202020;
            border: 1px solid #d0d0d0;
            border-radius: 4px;
            selection-background-color: #9c080b;
            selection-color: #ffffff;
            outline: none;
        }}
        QGroupBox {{
            color: #202020;
            border: 1px solid #d0d0d0;
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
            background-color: #ffffff;
            color: #202020;
            border: 1px solid #d0d0d0;
        }}
        QSplitter::handle {{
            background-color: #d0d0d0;
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
            background-color: #f3f3f3;
            width: 10px;
            margin: 0;
            border: none;
        }}
        QScrollBar::handle:vertical {{
            background-color: #c8c8c8;
            min-height: 24px;
            border-radius: 5px;
        }}
        QScrollBar::handle:vertical:hover {{
            background-color: #a8a8a8;
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
        }}
        QScrollBar:horizontal {{
            background-color: #f3f3f3;
            height: 10px;
            margin: 0;
            border: none;
        }}
        QScrollBar::handle:horizontal {{
            background-color: #c8c8c8;
            min-width: 24px;
            border-radius: 5px;
        }}
        QScrollBar::handle:horizontal:hover {{
            background-color: #a8a8a8;
        }}
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
            width: 0px;
        }}
    """


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

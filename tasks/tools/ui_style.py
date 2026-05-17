from qfluentwidgets import isDarkTheme


def get_status_label_style() -> str:
    if isDarkTheme():
        return "QLabel { background-color: #2b2b2b; color: #f0f0f0; padding: 5px; border: 1px solid #555; }"
    return "QLabel { background-color: #f0f0f0; color: #202020; padding: 5px; border: 1px solid #ccc; }"

# 获取游戏窗口句柄

import win32gui


def enum_windows_callback(hwnd, keywords):
    # 检查窗口是否可见和可接受输入
    if win32gui.IsWindowVisible(hwnd) and win32gui.IsWindowEnabled(hwnd):
        # 获取窗口类名
        found_class = win32gui.GetClassName(hwnd)
        window_title = win32gui.GetWindowText(hwnd)
        # 如果对的上窗口标题和窗口类名，将句柄加入到数组中，以便使用
        if keywords[1] == found_class and keywords[0] == window_title:
            keywords.append(hwnd)


def get_win_handle() -> object:
    """
    获取窗口句柄的函数
    :return: 如果获取到窗口句柄，则返回句柄，若没有获取到，则返回None
    """
    # 指定匹配的关键词
    keyword = ["LimbusCompany", "UnityWndClass"]
    # 枚举所有窗口
    win32gui.EnumWindows(enum_windows_callback, keyword)
    if len(keyword) >= 3:
        return keyword[2]
    else:
        return None

import json
import winreg
from pathlib import Path

import psutil
import win32process
from PySide6.QtCore import QT_TRANSLATE_NOOP

from app.language_manager import SUPPORTED_GAME_LANG_CODE
from ..config import cfg
from ..logger import log


class AutoSwitchCon:
    "自动切换语言的返回值表达类"

    FINISH: int = 0
    "语言相同"
    CHANGED: int = 1
    "语言不同并自动切换"
    FAILED: int = 2
    "语言切换失败, 可能是不支持的语言"


def auto_switch_language_in_game(hwnd: int) -> int:
    """通过句柄获取程序路径以实现识别游戏当前语言
    \n(不过如果在运行时改动了游戏设置就没办法了)
    ---

    Returns:
        int: 从0-2三种情况 可以查看AutoSwitchCon类
            - 0: 当前语言相同
            - 1: 当前语言不同, 但位于支持的语言列表中 (自动切换)
            - 2: 当前语言不同, 且不支持
    """
    default_lang = {"kr": "한국어", "jp": "日本語", "Unknown": "未知"}
    output_lang_dict = default_lang
    output_lang_dict.update(SUPPORTED_GAME_LANG_CODE)
    path = None
    try:
        # 获取窗口的进程ID
        _, pid = win32process.GetWindowThreadProcessId(hwnd)

        # 通过psutil获取进程信息
        process = psutil.Process(pid)

        # 返回进程的可执行文件路径
        path = Path(process.exe())
    except Exception as e:
        log.error(f"获取路径时出错: {e}")

    if path is None:
        raise ValueError("未获取到程序路径")
    json_path = path.parent / "LimbusCompany_Data" / "Lang" / "config.json"
    lang_code = None

    log.debug(f"游戏设置路径: {json_path}")

    try:
        with open(json_path, "r") as f:
            content = f.read()
        json_content: dict = json.loads(content)
        log.debug(f"读取语言配置文件内容: {json_content}")
        lang_code = json_content.get("lang", "Unknown")
    except FileNotFoundError:
        log.debug(f"未找到语言配置文件: {json_path}")
        lang_code = "-"
    except Exception as e:
        log.debug(f"{type(e).__name__}, 读取语言配置文件时出错: {e}")
        lang_code = "Unknown"

    lang_dict = {"-": "default", "LLC_zh-CN": "zh_cn"}
    if lang_code in lang_dict:
        lang_code = lang_dict[lang_code]
    else:
        lang_code = "Unknown"

    if lang_code == "default":
        #  lang_list = ["한국어", "English", "日本語", "Unknown"]
        lang_list = ["kr", "en", "jp", "Unknown"]
        game_config = get_game_config_from_registry()
        lang_index = game_config.get("_language", 3)
        lang_code = lang_list[lang_index]

    if lang_code == cfg.language_in_game:
        return AutoSwitchCon.FINISH

    if cfg.language_in_game == "-":
        msg = QT_TRANSLATE_NOOP(
            "Logger", "当前游戏语言为 {current_game_lang}, 即将自动切换"
        )
        formatted_msg = msg.format(current_game_lang=output_lang_dict[lang_code])
        log.info(formatted_msg)
    else:
        msg = QT_TRANSLATE_NOOP(
            "Logger",
            "当前游戏语言为 {current_game_lang}, 但是被错误设置成了 {setting_game_lang}",
        )
        formatted_msg = msg.format(
            current_game_lang=output_lang_dict[lang_code],
            setting_game_lang=output_lang_dict[cfg.language_in_game],
        )
        log.info(formatted_msg)
    if lang_code in SUPPORTED_GAME_LANG_CODE:
        cfg.set_value("language_in_game", lang_code)
        return AutoSwitchCon.CHANGED
    msg = QT_TRANSLATE_NOOP("Logger", "自动切换失败, 不支持的游戏语言")
    log.info(msg)
    return AutoSwitchCon.FAILED


def get_game_config_from_registry() -> dict:
    """从注册表获取当前游戏设置
    Returns:
        dict: 游戏设置的字典, 如果读取失败则返回空字典
    """
    root = winreg.HKEY_CURRENT_USER
    sub_key = r"Software\ProjectMoon\LimbusCompany"
    value_name = "LocalSave.LocalGameOptionData_h467498167"

    try:
        # 打开注册表键

        with winreg.OpenKey(root, sub_key, 0, winreg.KEY_READ) as key:
            # 读取二进制数据
            raw_data, reg_type = winreg.QueryValueEx(key, value_name)

            # 验证数据类型
            if reg_type != winreg.REG_BINARY:
                log.debug(f"错误：值项类型为 {reg_type}，预期应为 REG_BINARY")
                return {}

            # 去除末尾的 NULL 字节并解码为字符串
            json_str = raw_data.rstrip(b"\x00").decode("utf-8")

            # 解析 JSON 数据
            config_data: dict = json.loads(json_str)

            return config_data

    except FileNotFoundError:
        log.debug(f"注册表路径不存在: HKEY_CURRENT_USER\\{sub_key}")
        return {}
    except PermissionError:
        log.debug("读取注册表时权限不足，请以管理员身份运行程序")
        return {}
    except Exception as e:
        log.debug(f"处理数据时出错: {str(e)}")
        return {}

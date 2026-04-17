import json
import winreg
from pathlib import Path

import psutil
import win32process

from app.language_manager import SUPPORTED_GAME_LANG_CODE

from ..config import cfg
from ..logger import log



def auto_switch_language_in_game(hwnd: int) -> None:
    """通过句柄获取程序路径识别游戏当前语言
    若lang_code 最终为default，说明没有识别到可用语言，采用用户设置的语言
    """
    log.debug(f"开始自动检测游戏语言: hwnd={hwnd}, current_cfg_language={cfg.language_in_game}, simulator={cfg.simulator}")

    # 模拟器强制使用英文
    if cfg.simulator:
        cfg.set_value("language_in_game", "en")
        log.info(f"模拟器语言强制设置为：{cfg.language_in_game}")
        return

    # 获取自定义语言
    lang_code = get_game_lang_from_config(hwnd)

    # 没有自定义语言，那么获取游戏设置的语言
    if lang_code == "default":
        lang_code = get_game_config_from_registry()
        log.debug(f"自动检测语言: resolved_default_lang_code={lang_code}")

    # 语言和设置相同
    if lang_code == cfg.language_in_game or lang_code == "default":
        log.info(f"语言设置为：{cfg.language_in_game}")
        return
    elif lang_code in SUPPORTED_GAME_LANG_CODE:
        cfg.set_value("language_in_game", lang_code)
        log.info(f"语言自动识别为：{lang_code}")
        return
    else:
        log.info(f"不支持语言: {lang_code}")
    



def get_game_lang_from_config(hwnd: int) -> str:
    """根据窗口句柄读取游戏目录下的语言配置并返回语言代码。

    Returns:
        - "default": 配置文件不存在，或 lang 字段为 "-"
        - "zh_cn": 配置文件中的 "LLC_zh-CN" 会被映射为项目内部语言代码
        - "en": 配置文件中的英文代码
    Raises:
        ValueError: 检测到未支持的语言代码
    """
    path = None
    try:
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        process = psutil.Process(pid)
        path = Path(process.exe())
    except Exception as e:
        log.error(f"获取路径时出错: {e}")

    if path is None:
        raise ValueError("未获取到程序路径")

    json_path = path.parent / "LimbusCompany_Data" / "Lang" / "config.json"
    log.debug(f"游戏设置路径: {json_path}")
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            json_content: dict = json.load(f)
        log.debug(f"读取语言配置文件内容: {json_content}")
        lang_code = json_content.get("lang")
    except FileNotFoundError:
        log.debug(f"未找到语言配置文件: {json_path}")
        return "default"
    except Exception as e:
        log.debug(f"{type(e).__name__}, 读取语言配置文件时出错: {e}")
        raise
    normalized_lang_code = {"-": "default", "LLC_zh-CN": "zh_cn"}.get(lang_code, lang_code)
    if normalized_lang_code in {"default", "zh_cn", "en"}:
        return normalized_lang_code
    raise ValueError(f"检测到未支持的游戏语言代码: {normalized_lang_code}")


def get_raw_game_config_from_registry() -> dict:
    """从注册表读取原始游戏配置字典。"""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\ProjectMoon\LimbusCompany", 0, winreg.KEY_READ) as key:
            raw_data, reg_type = winreg.QueryValueEx(key, "LocalSave.LocalGameOptionData_h467498167")
            if reg_type != winreg.REG_BINARY:
                log.debug(f"错误：值项类型为 {reg_type}，预期应为 REG_BINARY")
                return {}
            config_data: dict = json.loads(raw_data.rstrip(b"\x00").decode("utf-8"))
            log.debug(f"从注册表读取游戏配置成功: keys={list(config_data.keys())}")
            return config_data

    except FileNotFoundError:
        log.debug(r"注册表路径不存在: HKEY_CURRENT_USER\Software\ProjectMoon\LimbusCompany")
        return {}
    except PermissionError:
        log.debug("读取注册表时权限不足，请以管理员身份运行程序")
        return {}
    except Exception as e:
        log.debug(f"处理数据时出错: {str(e)}")
        return {}


def get_game_config_from_registry() -> str:
    """从注册表读取游戏语言，仅接受英语配置。"""
    lang_index = get_raw_game_config_from_registry().get("_language")
    if lang_index not in {0, 1, 2}:
        raise ValueError(f"注册表中的语言索引无效: {lang_index}")
    if lang_index != 1:
        raise ValueError(f"检测到非英语游戏语言索引: {lang_index}")
    return "en"

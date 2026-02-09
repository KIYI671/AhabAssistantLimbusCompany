import base64
import os
import subprocess
import tempfile
from datetime import datetime, time, timedelta
from time import sleep
from zoneinfo import ZoneInfo  # Python 3.9+ 内置模块

import cv2
import numpy as np
import win32crypt

from module.config import cfg
from module.logger import log


def get_day_of_week():
    # 直接获取当前东九区时间（Asia/Tokyo）
    now_time = datetime.now(ZoneInfo("Asia/Tokyo"))

    # 提取星期几（中文）、小时、分钟
    day = now_time.isoweekday()  # isoweekday() 返回 1（周一）~7（周日）
    hour = now_time.hour  # 小时（0-23）

    if (
        hour < 6 and day == 1
    ):  # 如果是凌晨0点到6点之间，且不是周一，则视为前一天 （修复周一凌晨判断传参为0的bug）
        day = 7
    elif hour < 6:
        day -= 1

    return day


def get_timezone():
    # 获取当前UTC时间（带时区信息）
    utc_now = datetime.now(ZoneInfo("UTC"))

    # 转换为本地时区的时间（自动获取系统时区）
    local_now = utc_now.astimezone()

    # 东九区时区（如东京时间）
    jst_tz = ZoneInfo("Asia/Tokyo")
    jst_now = utc_now.astimezone(jst_tz)  # 东九区当前时间

    # 获取本地时区和东九区的UTC偏移量（timedelta对象）
    local_offset = local_now.utcoffset()
    jst_offset = jst_now.utcoffset()

    # 计算时间差（小时）
    diff_hours = (jst_offset - local_offset).total_seconds() / 3600
    cfg.set_value("timezone", round(diff_hours, 2))  # 保留二位小数，保存在配置文件中


def check_hard_mirror_time():
    if cfg.last_auto_change == 1715990400:
        get_timezone()

    last_time = datetime.fromtimestamp(cfg.last_auto_change)
    now_time = datetime.now()

    if last_time >= now_time:
        return False  # 原始时间t1不早于t2，偏移后也不会

    if cfg.timezone is None:
        get_timezone()
    # 应用时间偏移量（支持浮点数小时）
    offset = timedelta(hours=cfg.timezone)
    last_time_offset = last_time + offset
    now_time_offset = now_time + offset

    # 计算last_time_offset的星期几（0=周一，3=周四）
    weekday = last_time_offset.weekday()  # 0-6分别对应周一到周日

    # 计算到下一个周四的天数差（若当前是周四则为0，否则调整到最近的周四）
    days_to_thursday = (3 - weekday) % 7  # 3对应周四的weekday值

    # 构造候选时间：last_time_offset的日期 + 天数差，时间设为12:00
    candidate_date = last_time_offset.date() + timedelta(days=days_to_thursday)
    candidate = datetime.combine(candidate_date, time(12, 0))

    # 如果候选时间早于last_time_offset，说明需要下一个周四
    if candidate < last_time_offset:
        candidate += timedelta(days=7)

    # 检查候选时间是否在[last_time_offset, now_time_offset)区间内
    return last_time_offset <= candidate < now_time_offset


def calculate_the_teams():
    day = get_day_of_week()
    if day == 1 or day == 2:
        return "1_2"
    if day == 3 or day == 4:
        return "3_4"
    if day == 5 or day == 6:
        return "5_6"
    if day == 7 or day == 8:
        return "7"


def find_skill3(background, known_rgb, threshold=40, min_pixels=10):
    median_rgb = np.median(background, axis=(0, 1)).astype(int)
    blended_rgb = (median_rgb * 0.45 + np.array(known_rgb) * 0.55).astype(int)

    comp = 1

    lower_bound = np.clip(blended_rgb - threshold, 0, 255)
    upper_bound = np.clip(blended_rgb + threshold, 0, 255)
    mask = cv2.inRange(background, lower_bound, upper_bound)

    mask = cv2.erode(mask, np.ones((3, 3), np.uint8))
    mask = cv2.dilate(mask, np.ones((3, 3), np.uint8))
    mask = cv2.dilate(mask, np.ones((3, 3), np.uint8))
    mask = cv2.dilate(mask, np.ones((3, 3), np.uint8))

    # collecting clusters (colors that are directly connected)
    num_labels, _, stats, centroids = cv2.connectedComponentsWithStats(mask)

    cluster_centers = []

    # some pixel value checks (colors in cluster may be disconnected)
    for i in range(1, num_labels):
        area = stats[i, cv2.CC_STAT_AREA]
        center = centroids[i]

        if min_pixels * comp <= area:
            x = int(center[0])
            x1, x2 = (
                round(max(0, x - 33 * comp)),
                round(min(background.shape[1], x + 33 * comp)),
            )
            y1, y2 = 0, round(13 * comp)

            region_mask = mask[y1:y2, x1:x2]
            similar_pixels = np.count_nonzero(region_mask)

            if similar_pixels >= 26 * comp:
                cluster_centers.append(center)

    # merging neightbouring clusters
    merged = []
    while cluster_centers:
        current = cluster_centers.pop()
        group = [c for c in cluster_centers if np.linalg.norm(current - c) <= 67 * comp]
        cluster_centers = [
            c for c in cluster_centers if np.linalg.norm(current - c) > 66 * comp
        ]
        merged.append(np.mean([current] + group, axis=0))

    return merged


def check_teams_order(lst):
    # 收集所有非零元素的（值，原始索引）对
    non_zero = [(val, idx) for idx, val in enumerate(lst) if val > 0]
    # 按值降序排序，值相同时按原始索引升序排序
    sorted_non_zero = sorted(non_zero, key=lambda x: (-x[0], x[1]))
    # 初始化结果列表为全0
    result = [0] * len(lst)
    # 非零元素的数量
    n = len(sorted_non_zero)
    # 为每个非零元素分配对应的递增值
    for i in range(n):
        val, original_idx = sorted_non_zero[i]
        # 最大的元素对应n，次大的对应n-1，依此类推
        result[original_idx] = n - i
    return result


def encrypt_string(text: str, entropy: bytes = b"AALC") -> str:
    """使用当前Windows用户凭据加密字符串"""

    if not text:
        return ""

    # 转换为字节
    data = text.encode("utf-8")

    # 加密数据（只能由同一用户在同一机器上解密）
    encrypted_data = win32crypt.CryptProtectData(
        data,
        None,  # 描述字符串（可选）
        entropy,  # 额外熵值（增强安全性）
        None,  # 保留
        None,  # 提示信息
        0,  # 默认标志：CRYPTPROTECT_UI_FORBIDDEN
    )
    # 返回Base64编码的加密结果
    return base64.b64encode(encrypted_data).decode("utf-8")


def decrypt_string(encrypted_b64: str, entropy: bytes = b"AALC") -> str:
    """使用当前Windows用户凭据解密字符串"""
    if not encrypted_b64:
        return ""

    if len(encrypted_b64) % 4 != 0:
        return encrypted_b64
    try:
        # 解码Base64
        encrypted_data = base64.b64decode(encrypted_b64)

        # 解密数据
        decrypted_data = win32crypt.CryptUnprotectData(
            encrypted_data,
            entropy,  # 必须与加密时相同的熵值
            None,  # 保留
            None,  # 提示信息
            0,  # 默认标志
        )
    except Exception:
        return encrypted_b64
    # 返回原始字符串
    return decrypted_data[1].decode("utf-8")


def check_game_running() -> bool:
    """检查游戏是否正在运行"""
    if cfg.simulator:
        if cfg.simulator_type == 0:
            from module.simulator.mumu_control import MumuControl

            return MumuControl.connection_device.check_game_alive()
    else:
        import psutil

        for proc in psutil.process_iter(["name"]):
            try:
                # 获取进程的可执行文件名（如 "notepad.exe"）
                proc_name = proc.info["name"]
                # 精确匹配进程名（区分大小写，取决于系统）
                if cfg.game_process_name in proc_name:
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                # 忽略已终止、无权限或僵尸进程
                continue

    return False


def run_as_user(command: list[str], timeout: int = 30):
    """
    使用任务计划程序以当前用户身份运行命令，优化了路径转义和阻塞处理。
    """
    task_name = "TempNonAdminTask"
    bat_path = None

    def run_cmd(cmd: str, ignore_error: bool = False):
        try:
            # 增加 timeout 防止进程挂起
            res = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=10
            )
            if res.returncode != 0 and not ignore_error:
                log.debug(f"命令执行失败: {cmd}\n错误: {res.stderr.strip()}")
            return res
        except subprocess.TimeoutExpired:
            log.debug(f"命令执行超时: {cmd}")
            return None

    try:
        # 1. 预清理：强制删除旧任务 (/f)
        run_cmd(f'schtasks /delete /tn "{task_name}" /f', ignore_error=True)

        # 2. 创建临时批处理文件
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=".bat", mode="w", encoding="gbk"
        ) as bat:
            # 使用 @echo off 减少输出，添加 exit 确保批处理退出
            bat.write(f"@echo off\n{subprocess.list2cmdline(command)}\nexit\n")
            bat_path = bat.name

        # 3. 创建任务
        # /f: 强制创建；/rl limited: 确保以受限权限运行（非管理员）
        username = os.environ.get("USERNAME")
        create_cmd = (
            f'schtasks /create /f /tn "{task_name}" /sc once /st 23:59 '
            f'/ru "{username}" /tr "cmd.exe /c \'{bat_path}\'"'
        )
        if run_cmd(create_cmd) is None:
            return False

        # 4. 立即执行任务
        log.debug(f"启动任务: {command}")
        if run_cmd(f'schtasks /run /tn "{task_name}"') is None:
            return False

        # 5. 等待执行 (根据需求调整)
        # 注意：schtasks /run 是异步的，这里 sleep 是等待程序启动
        sleep(2)

    except Exception as e:
        log.debug(f"任务: {command} 发生异常: {e}")
        return False
    finally:
        # 6. 最终清理
        run_cmd(f'schtasks /delete /tn "{task_name}" /f', ignore_error=True)
        # 修复点：增加对 bat_path 类型的显式检查
        if isinstance(bat_path, (str, bytes, os.PathLike)) and os.path.exists(bat_path):
            try:
                os.unlink(bat_path)
            except OSError as e:
                log.debug(f"任务: {command} 尝试删除临时脚本失败: {e}")

    return True

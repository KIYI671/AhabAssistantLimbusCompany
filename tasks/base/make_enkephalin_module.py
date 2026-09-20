import re
import time
from time import sleep

from module.automation import auto
from module.config import cfg
from module.decorator.decorator import begin_and_finish_time_log
from module.logger import log

from .retry import retry

GRANDET_MIN_INTERVAL_SECONDS = 5 * 60 + 20
"""葛朗台模式阈值：下一点体力的恢复时间不低于该值时才换体"""

GRANDET_MAX_WAIT_SECONDS = 7 * 60
"""葛朗台模式最长等待时间：略大于一个体力恢复周期，避免识别异常导致换体流程卡死"""

# 体力恢复时间的识别区域里必然包含标签文本（如 Enkephalin recovered in 5:55），
# 且 OCR 结果可能夹带空格、噪声字符（如 Enkephalinrecovered inD5:55），
# 所以直接在整段结果中匹配 mm:ss，不能假设时间恰好位于字符串的固定位置
_TIMING_PATTERN = re.compile(r"(\d{1,3})\s*[:：]\s*([0-5]?\d)")


def get_the_timing():
    """获取下一点体力的恢复时间（秒），无法识别时返回 None"""
    module_position = auto.find_element("enkephalin/lunacy_assets.png", take_screenshot=True)
    if not module_position:
        log.debug("未找到狂气图标，无法识别下一点体力的恢复时间")
        return None
    my_scale = cfg.set_win_size / 1440
    bbox = (
        module_position[0] - 200 * my_scale,
        module_position[1] + 150 * my_scale,
        module_position[0] + 600 * my_scale,
        module_position[1] + 220 * my_scale,
    )
    ocr_result = auto.find_text_element(None, my_crop=bbox, only_text=True)
    if not ocr_result:
        log.debug("未识别到体力恢复时间文本")
        return None
    ocr_text = "".join(str(ocr) for ocr in ocr_result)
    timing = _TIMING_PATTERN.search(ocr_text)
    if timing is None:
        log.debug(f"无法从识别结果 {ocr_text!r} 中解析出体力恢复时间")
        return None
    return int(timing.group(1)) * 60 + int(timing.group(2))


def wait_for_grandet_mode():
    """葛朗台模式：等待下一点体力的恢复时间超过阈值后再换体

    恢复时间识别异常时最多等待 GRANDET_MAX_WAIT_SECONDS 秒，超时后不再等待，
    避免识别失败时换体流程一直卡住。
    """
    start_time = time.time()
    last_log_time = start_time
    while True:
        timing = get_the_timing()
        now_time = time.time()
        if timing is not None:
            if timing >= GRANDET_MIN_INTERVAL_SECONDS:
                log.debug(f"生成下一点体力的时间为{timing // 60}分{timing % 60}秒，符合葛朗台模式操作")
                return
            log.debug(f"生成下一点体力的时间为{timing // 60}分{timing % 60}秒，未达到葛朗台模式阈值，等待中")
        elif now_time - last_log_time > 30:
            last_log_time = now_time
            log.warning(
                f"未能识别下一点体力的恢复时间，已等待{int(now_time - start_time)}秒，最多等待{GRANDET_MAX_WAIT_SECONDS}秒"
            )
        if now_time - start_time > GRANDET_MAX_WAIT_SECONDS:
            log.warning(f"等待{GRANDET_MAX_WAIT_SECONDS}秒仍未等到合适的换体时机，跳过葛朗台模式等待，直接换体")
            return
        sleep(2)


def get_current_enkephalin():
    import cv2
    import numpy as np

    from module.ocr import ocr
    from utils.image_utils import ImageUtils

    enkephalin_bbox = ImageUtils.get_bbox(ImageUtils.load_image("enkephalin/enkephalin_now_bbox.png"))
    for _ in range(5):
        try:
            while auto.take_screenshot() is None:
                continue
            sc = ImageUtils.crop(np.array(auto.screenshot), enkephalin_bbox)
            _, binary_image = cv2.threshold(sc, 110, 255, cv2.THRESH_BINARY)
            result = ocr.run(binary_image)
            ocr_result = [result.txts[i] for i in range(len(result.txts))]
            ocr_result = "".join(ocr_result)
            ocr_result = ocr_result.lower()
            if "/" in ocr_result:
                ocr_result = ocr_result.split("/")
                ocr_result_int = "".join(char for char in ocr_result[0] if char.isdigit())
                current_enkephalin = int(ocr_result_int)
                return current_enkephalin
        except:
            continue
    try:
        sc = ImageUtils.crop(np.array(auto.screenshot), enkephalin_bbox)
        _, binary_image = cv2.threshold(sc, 150, 255, cv2.THRESH_BINARY)
        result = ocr.run(binary_image)
        ocr_result = [result.txts[i] for i in range(len(result.txts))]
        ocr_result = "".join(ocr_result)
        current_enkephalin = int(ocr_result[0])
        return current_enkephalin
    except:
        pass
    return None


@begin_and_finish_time_log(task_name="体力换饼", calculate_time=False)
def make_enkephalin_module(cancel=True, skip=True, *, task_name: str = "体力换饼"):
    """体力换饼的模块
    Args:
        cancel (bool): 是否点击取消按钮 (即关闭换体界面)
        skip (bool): 是否遵循设置跳过换体 (优先于cfg.skip_enkephalin)
    """
    if skip and cfg.skip_enkephalin:
        return

    start_time = time.time()
    last_log_time = None
    first_popup_warning = True
    use_lunacy_threshold = 0.8
    all_in_threshold = 0.8
    popup_marker_threshold = 0.7
    open_panel_click_cooldown = 0.5
    last_open_panel_click_time = 0.0

    while True:
        now_time = time.time()
        if auto.get_restore_time() is not None:
            start_time = max(start_time, auto.get_restore_time())
        if 60 > now_time - start_time > 20 and int(now_time - start_time) % 10 == 0:
            if last_log_time is None or now_time - last_log_time > 5:
                msg = f"已尝试{task_name}超过{int(now_time - start_time)}秒，如果非电脑硬件配置不足，请确认是否执行了正确的语言配置"
                log.warning(msg)
                last_log_time = now_time
        if now_time - start_time > 60:
            from app import mediator

            if first_popup_warning and (last_log_time is None or now_time - last_log_time > 5):
                # only do it once
                first_popup_warning = False
                log.warning(f"已尝试{task_name}超过1分钟，脚本将停止运行，请先检查语言配置，或检查电脑配置是否支持")
                mediator.link_start.emit()
                message = f"脚本卡死在{task_name}，请检查语言配置，或检查电脑配置是否支持"
                mediator.warning.emit(message)
        # 自动截图
        if auto.take_screenshot() is None:
            continue
        auto.mouse_to_blank()
        if auto.find_element("base/update_close_assets.png", model="clam") and auto.find_element(
            "home/drive_assets.png", model="normal"
        ):
            auto.click_element("base/update_close_assets.png")
            from tasks.base.back_init_menu import back_init_menu

            back_init_menu()
            start_time = time.time()
            continue
        if auto.find_element("base/renew_confirm_assets.png", model="clam") and auto.find_element(
            "home/drive_assets.png", model="normal"
        ):
            auto.click_element("base/renew_confirm_assets.png")
            from tasks.base.back_init_menu import back_init_menu

            back_init_menu()
            start_time = time.time()
            continue
        panel_visible = bool(
            auto.find_element("enkephalin/use_lunacy_assets.png", threshold=use_lunacy_threshold)
            or auto.find_element("enkephalin/enkephalin_cancel_assets.png", threshold=popup_marker_threshold)
            or auto.find_element("enkephalin/all_in_assets.png", threshold=all_in_threshold)
        )
        if not panel_visible:
            if now_time - last_open_panel_click_time >= open_panel_click_cooldown and auto.click_element(
                "home/enkephalin_box_assets.png",
                threshold=0.75,
                offset=False,
            ):
                last_open_panel_click_time = now_time
                sleep(0.5)
            continue
        if auto.click_element(
            "enkephalin/all_in_assets.png",
            threshold=all_in_threshold,
        ):
            sleep(0.2)
            if auto.take_screenshot() is None:
                continue
            auto.click_element("enkephalin/enkephalin_confirm_assets.png")
            sleep(0.4)
            if retry() is False:
                log.error(f"{task_name}时因网络原因执行失败")
                return False
            if cancel:
                auto.click_element("enkephalin/enkephalin_cancel_assets.png")
            return True
        elif panel_visible:
            # 如果可见换体界面但不可见全换按钮, 则说明上次操作未恢复初始界面
            if not auto.click_element("enkephalin/enkephalin_cancel_assets.png"):
                auto.mouse_click_blank()

        sleep(0.2)
        continue


@begin_and_finish_time_log(task_name="狂气换体", calculate_time=False)
def lunacy_to_enkephalin(times=0):
    make_enkephalin_module(cancel=False, skip=False, task_name="狂气换体")
    auto.click_element("enkephalin/use_lunacy_assets.png")
    sleep(0.5)
    Grandet = False
    lunacy_map = {
        1: "26",
        2: "52",
        3: "78",
    }
    forward = True
    # 前向模式标识 处于判断当前换体次数时
    time = 1
    while time < times + 1:
        if auto.take_screenshot() is None:
            sleep(0.5)
            if auto.take_screenshot() is None:
                log.error("狂气换体时截图失败")
                break
        used_lunacy = lunacy_map.get(time)
        if not used_lunacy:
            log.error(f"无法识别的狂气换体次数: {time}")
            break
        lunacy_asset = f"enkephalin/lunacy_spend_{used_lunacy}_assets.png"
        if auto.find_element(lunacy_asset):
            forward = False
            # 葛朗台模式：只在第一次换体前等待（保持原有行为，避免多次换体之间长时间等待）
            if cfg.Dr_Grandet_mode and not Grandet:
                wait_for_grandet_mode()
                Grandet = True
            auto.click_element("enkephalin/enkephalin_confirm_assets.png")
            sleep(1)
            if retry() is False:
                log.error("狂气换体时重试失败")
                break
        elif not forward:
            forward = True
            # 非前向模式时, 遇到寻找失败可能是上一次点击时出错
            # 回退至上次换体并重复执行一次
            time -= 1
            continue
        if time == times:
            # 最后一步时, 检查是否成功换体
            if forward:
                # 如果是前向模式, 则说明换体成功, 直接退出
                break
            # 如果是非前向模式, 则说明至少换过一次体力
            if auto.find_element(lunacy_asset):
                # 如果仍然可见, 则说明换体失败, 继续尝试
                continue

        time += 1
    auto.click_element("enkephalin/enkephalin_cancel_assets.png")
    sleep(1)
    make_enkephalin_module(skip=False)

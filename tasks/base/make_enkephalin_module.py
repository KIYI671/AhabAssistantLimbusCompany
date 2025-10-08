from time import sleep

from module.automation import auto
from module.config import cfg
from module.decorator.decorator import begin_and_finish_time_log
from module.logger import log


def get_the_timing(return_time = False):
    if module_position := auto.find_element("enkephalin/lunacy_assets.png", take_screenshot=True):
        my_scale = cfg.set_win_size / 1440
        bbox = (
            module_position[0] - 200 * my_scale, module_position[1] + 150 * my_scale,
            module_position[0] + 600 * my_scale,
            module_position[1] + 220 * my_scale)
        ocr_result = auto.find_text_element(None, my_crop=bbox, only_text=True)
        s = ''
        if ocr_result is not None:
            try:
                for ocr in ocr_result:
                    s += str(ocr)
                if ':' in s:
                    l = s.split(":")
                    minute = int(l[0][-2:])
                    seconds = int(l[1][:2])
                    if return_time:
                        return minute * 60 + seconds
                    if minute >= 5 and seconds >= 20:
                        log.debug(f"生成下一点体力的时间为{minute}分{seconds}秒，符合葛朗台模式操作")
                        return True
            except:
                return False
        return False

def get_current_enkephalin():
    from utils.image_utils import ImageUtils
    import numpy as np
    from module.ocr import ocr
    import cv2
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
                current_enkephalin = int(ocr_result[0])
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
def make_enkephalin_module(cancel=True, skip=True):
    """体力换饼的模块
    Args:
        cancel (bool): 是否点击取消按钮 (即关闭换体界面)
        skip (bool): 是否遵循设置跳过换体 (优先于cfg.skip_enkephalin)
    """
    if skip and cfg.skip_enkephalin:
        return
    import time
    start_time = time.time()
    last_log_time = None
    first_popup_warning = True

    while True:
        now_time = time.time()
        if 60 > now_time - start_time > 20 and int(now_time - start_time) % 10 == 0:
            if last_log_time is None or now_time - last_log_time > 5:
                msg = f"已尝试狂气换体超过{int(now_time - start_time)}秒，如果非电脑硬件配置不足，请确认是否执行了正确的语言配置"
                log.warning(msg)
                last_log_time = now_time
        if now_time - start_time > 60:
            from app import mediator

            if first_popup_warning and (
                last_log_time is None or now_time - last_log_time > 5
            ):
                # only do it once
                first_popup_warning = False
                log.warning(
                    "已尝试狂气换体超过1分钟，脚本将停止运行，请先检查语言配置，或检查电脑配置是否支持"
                )
                mediator.link_start.emit()
                message = "脚本卡死在狂气换体，请检查语言配置，或检查电脑配置是否支持"
                mediator.warning.emit(message)
        # 自动截图
        if auto.take_screenshot() is None:
            continue
        auto.mouse_to_blank()
        if auto.find_element("base/update_close_assets.png", model="clam") and auto.find_element("home/drive_assets.png",
                                                                                              model="normal"):
            auto.click_element("base/update_close_assets.png")
            from tasks.base.back_init_menu import back_init_menu
            back_init_menu()
            start_time = time.time()
            continue
        if auto.find_element("base/renew_confirm_assets.png", model="clam") and auto.find_element(
                "home/drive_assets.png", model="normal"):
            auto.click_element("base/renew_confirm_assets.png")
            from tasks.base.back_init_menu import back_init_menu
            back_init_menu()
            start_time = time.time()
            continue
        if auto.find_element("enkephalin/use_lunacy_assets.png") is None:
            if auto.click_element("home/enkephalin_box_assets.png"):
                sleep(0.5)
            continue
        auto.click_element("enkephalin/all_in_assets.png")
        auto.click_element("enkephalin/enkephalin_confirm_assets.png")
        if cancel:
            auto.click_element("enkephalin/enkephalin_cancel_assets.png")

        break


@begin_and_finish_time_log(task_name="狂气换体", calculate_time=False)
def lunacy_to_enkephalin(times=0):
    make_enkephalin_module(cancel=False, skip=False)
    auto.click_element("enkephalin/use_lunacy_assets.png")
    sleep(0.5)
    Grandet = False
    while times > 0:
        auto.mouse_to_blank(move_back=False)
        # 自动截图
        if auto.take_screenshot() is None:
            continue
        if times > 0 and auto.find_element("enkephalin/lunacy_spend_26_assets.png"):
            # 葛朗台模式
            if cfg.Dr_Grandet_mode:
                while get_the_timing() is False:
                    if Grandet:
                        break
                    sleep(2)
                Grandet = True
            auto.click_element("enkephalin/enkephalin_confirm_assets.png")
            sleep(1)
            continue
        if times >= 2 and auto.find_element("enkephalin/lunacy_spend_52_assets.png"):
            if cfg.Dr_Grandet_mode:
                while get_the_timing() is False:
                    if Grandet:
                        break
                    sleep(2)
                    Grandet = True
            auto.click_element("enkephalin/enkephalin_confirm_assets.png")
            sleep(1)
            continue
        if times >= 3 and auto.find_element("enkephalin/lunacy_spend_78_assets.png"):
            if cfg.Dr_Grandet_mode:
                while get_the_timing() is False:
                    if Grandet:
                        break
                    sleep(2)
                    Grandet = True
            auto.click_element("enkephalin/enkephalin_confirm_assets.png")
            sleep(1)
            continue
        break
    auto.click_element("enkephalin/enkephalin_cancel_assets.png")
    make_enkephalin_module(skip=False)

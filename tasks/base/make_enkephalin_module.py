from time import sleep

from module.automation import auto
from module.config import cfg
from module.decorator.decorator import begin_and_finish_time_log


def get_the_timing():
    if module_position := auto.find_element("enkephalin/lunacy_assets.png", take_screenshot=True):
        my_scale = cfg.set_win_size / 1440
        bbox = (
            module_position[0] - 200* my_scale, module_position[1]+150* my_scale,
            module_position[0] + 600 * my_scale,
            module_position[1] + 220 * my_scale)
        ocr_result = auto.find_text_element(None,my_crop=bbox,only_text=True)
        s=''
        if ocr_result is not None:
            try:
                for ocr in ocr_result:
                    s+=str(ocr)
                if ':' in s:
                    l = s.split(":")
                    minute = int(l[0][-2:])
                    seconds = int(l[1][:2])
                    if minute>=5 and seconds>=20:
                        return True
            except:
                return False
        return False



@begin_and_finish_time_log(task_name="体力换饼", calculate_time=False)
def make_enkephalin_module(cancel=False):
    while True:
        # 自动截图
        if auto.take_screenshot() is None:
            continue
        auto.mouse_to_blank()
        if auto.find_element("enkephalin/use_lunacy_assets.png") is None:
            auto.click_element("home/enkephalin_box_assets.png")
            continue
        auto.click_element("enkephalin/all_in_assets.png")
        auto.click_element("enkephalin/enkephalin_confirm_assets.png")
        if cancel:
            auto.click_element("enkephalin/enkephalin_cancel_assets.png")

        break


@begin_and_finish_time_log(task_name="狂气换体", calculate_time=False)
def lunacy_to_enkephalin(times=0):
    make_enkephalin_module(cancel=False)
    auto.click_element("enkephalin/use_lunacy_assets.png")
    while times > 0:
        auto.mouse_to_blank()
        # 自动截图
        if auto.take_screenshot() is None:
            continue
        if times > 0 and auto.find_element("enkephalin/lunacy_spend_26_assets.png"):
            # 葛朗台模式
            if cfg.Dr_Grandet_mode:
                while get_the_timing() is False:
                    sleep(2)
            auto.click_element("enkephalin/enkephalin_confirm_assets.png")
            sleep(1)
            continue
        if times >= 2 and auto.find_element("enkephalin/lunacy_spend_52_assets.png"):
            if cfg.Dr_Grandet_mode:
                while get_the_timing() is False:
                    sleep(2)
            auto.click_element("enkephalin/enkephalin_confirm_assets.png")
            sleep(1)
            continue
        if times >= 3 and auto.find_element("enkephalin/lunacy_spend_78_assets.png"):
            if cfg.Dr_Grandet_mode:
                while get_the_timing() is False:
                    sleep(2)
            auto.click_element("enkephalin/enkephalin_confirm_assets.png")
            sleep(1)
            continue
        break
    auto.click_element("enkephalin/enkephalin_cancel_assets.png")
    make_enkephalin_module()

from time import sleep

from module.automation import auto
from module.decorator.decorator import begin_and_finish_time_log


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
    # TODO:待加入葛朗台模式
    make_enkephalin_module(cancel=False)
    auto.click_element("enkephalin/use_lunacy_assets.png")
    while times > 0:
        auto.mouse_to_blank()
        # 自动截图
        if auto.take_screenshot() is None:
            continue
        if times > 0 and auto.find_element("enkephalin/lunacy_spend_26_assets.png"):
            auto.click_element("enkephalin/enkephalin_confirm_assets.png")
            sleep(1)
            continue
        if times == 2 and auto.find_element("enkephalin/lunacy_spend_52_assets.png"):
            auto.click_element("enkephalin/enkephalin_confirm_assets.png")
            sleep(1)
            continue
        break
    auto.click_element("enkephalin/enkephalin_cancel_assets.png")
    make_enkephalin_module()

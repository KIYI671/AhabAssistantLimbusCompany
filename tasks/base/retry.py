from time import sleep

from module.automation import auto


def retry():
    while True:
        # 自动截图
        if auto.take_screenshot() is None:
            continue
        if auto.find_element("base/connecting_assets.png"):
            continue
        if position := auto.find_element("base/retry_countdown.png"):
            sleep(5)
            auto.mouse_click(position[0], position[1], times=3)
            continue
        if auto.click_element("base/retry.png", threshold=0.9):
            continue
        if auto.find_element("base/retry_countdown.png") \
                or auto.find_element("base/retry.png") \
                or auto.find_element("base/try_again.png"):
            auto.click_element("base/retry.png", threshold=0.9)
            continue
        break

from time import sleep

from module.automation import auto


def click_drive_entry(entry: str) -> bool:
    """识别常规驾驶席和魔女之夜活动布局的入口。"""
    regular = f"home/{entry}_assets.png"
    event = f"home/{entry}_walpurgis_assets.png"
    hub = "home/inferno_bus_assets.png"

    if auto.click_element(regular, model="clam"):
        return True
    if not auto.find_element(hub, model="clam"):
        return False
    if auto.click_element(event, model="clam"):
        return True

    # 驾驶席切换时先等入口加载，刷新截图后再决定是否返回主页。
    sleep(1)
    if auto.take_screenshot() is None or not auto.find_element(hub, model="clam"):
        return False
    if auto.click_element(regular, model="clam") or auto.click_element(event, model="clam"):
        return True
    return auto.click_element("home/window_assets.png")

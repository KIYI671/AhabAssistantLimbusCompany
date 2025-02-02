from module.automation import auto
from module.config import cfg
from tasks.base.retry import retry
from time import sleep

# 在默认缩放情况下，进行镜牢寻路
def search_road_default_distance():
    scale = cfg.set_win_size / 1440
    three_roads = [[500 * scale, 0],
                   [500 * scale, -400 * scale],
                   [500 * scale, 450 * scale]]
    while auto.take_screenshot() is None:
        continue
    retry()
    if bus_position := auto.find_element("mirror/mybus_default_distance.png"):
        for road in three_roads:
            road[0] += bus_position[0]
            road[1] += bus_position[1]
            if 0 < road[0] < cfg.set_win_size * 16 / 9 and 0 < road[1] < cfg.set_win_size:
                auto.mouse_click(road[0], road[1])
                sleep(0.75)
                if auto.click_element("mirror/road_in_mir/enter_assets.png", take_screenshot=True):
                    return True
        auto.mouse_click(bus_position[0], bus_position[1])
        if auto.click_element("mirror/road_in_mir/enter_assets.png", take_screenshot=True):
            return True
    return False


# 如果默认缩放无法镜牢寻路，进行滚轮缩放后继续寻路
def search_road_farthest_distance():
    scale = cfg.set_win_size / 1440
    auto.mouse_click_blank()
    auto.mouse_scroll()
    while auto.take_screenshot() is None:
        continue
    retry()
    three_roads = [[250 * scale, -200 * scale],
                   [250 * scale, 0],
                   [250 * scale, 225 * scale]]
    if bus_position := auto.find_element("mirror/mybus_maximum_distance.png"):
        for road in three_roads:
            road[0] += bus_position[0]
            road[1] += bus_position[1]
            if 0 < road[0] < cfg.set_win_size * 16 / 9 and 0 < road[1] < cfg.set_win_size:
                auto.mouse_click(road[0], road[1])
                while auto.take_screenshot() is None:
                    continue
                if auto.click_element("mirror/road_in_mir/enter_assets.png", take_screenshot=True):
                    return True
        auto.mouse_click(bus_position[0], bus_position[1])
        if auto.click_element("mirror/road_in_mir/enter_assets.png", take_screenshot=True):
            return True
    return False

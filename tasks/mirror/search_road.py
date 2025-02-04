from time import sleep

from module.automation import auto
from module.config import cfg
from tasks.base.retry import retry


# 在默认缩放情况下，进行镜牢寻路
def search_road_default_distance():
    scale = cfg.set_win_size / 1440
    three_roads = [[500 * scale, 50 * scale],
                   [500 * scale, -400 * scale],
                   [500 * scale, 450 * scale]]
    while auto.take_screenshot() is None:
        continue
    retry()
    if bus_position := auto.find_element("mirror/mybus_default_distance.png"):
        while True:
            if 600 * scale<bus_position[1]<700 * scale:
                break
            dy = 650 * scale-bus_position[1]
            auto.mouse_drag(bus_position[0], bus_position[1], drag_time=1.5, dx=0, dy=dy)
            sleep(1)
            auto.mouse_to_blank()
            while auto.take_screenshot() is None:
                continue
            bus_position = auto.find_element("mirror/mybus_default_distance.png")
            if bus_position is None:
                break

    if bus_position := auto.find_element("mirror/mybus_default_distance.png"):
        node_weight={}
        for road in three_roads:
            road[0] += bus_position[0]
            road[1] += bus_position[1]
            road_node_bbox = (road[0] - 200 * scale, road[1] - 200 * scale, road[0] + 200 * scale,road[1] + 200 * scale)
            if auto.find_feature_element("mirror/road_in_mir/shop.png",road_node_bbox):
                node_weight[(road[0],road[1])]=3
                continue
            elif auto.find_feature_element("mirror/road_in_mir/event.png",road_node_bbox):
                node_weight[(road[0],road[1])]=3
                continue
            elif auto.find_feature_element("mirror/road_in_mir/battle.png",road_node_bbox):
                node_weight[(road[0],road[1])]=2
                continue
            elif auto.find_feature_element("mirror/road_in_mir/hard_battle.png",road_node_bbox):
                node_weight[(road[0],road[1])]=1
                continue
            elif auto.find_feature_element("mirror/road_in_mir/hard_battle2.png",road_node_bbox):
                node_weight[(road[0],road[1])]=0
                continue
            node_weight[(road[0],road[1])]=-5
            continue
        node_weight[(bus_position[0],bus_position[1])]=-1
        print(node_weight)
        # 根据node_weight，按照各个键的值，从大到小以生成只有键的新的列表
        road_list = sorted(node_weight, key=node_weight.get, reverse=True)
        print(road_list)
        for road in road_list:
            if 0 < road[0] < cfg.set_win_size * 16 / 9 and 0 < road[1] < cfg.set_win_size:
                auto.mouse_click(road[0], road[1])
                sleep(0.75)
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

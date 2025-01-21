from time import sleep

from module.automation import auto
from module.config import cfg
from module.decorator.decorator import begin_and_finish_time_log
from module.logger import log

all_sinner = {
    1: "YiSang", 2: "Faust", 3: "DonQuixote",
    4: "Ryoshu", 5: "Meursault", 6: "HongLu",
    7: "Heathcliff", 8: "Ishmael", 9: "Rodion",
    10: "Dante",
    11: "Sinclair", 12: "Outis", 13: "Gregor"
}

pic_path = "teams/"


# 清队
def clean_team():
    while True:
        # 自动截图
        if auto.take_screenshot() is None:
            continue
        if auto.click_element("teams/clear_selection_confirm_assets.png"):
            break
        if auto.click_element("teams/clear_selection_assets.png"):
            sleep(0.5)
            auto.take_screenshot()
            if auto.find_element("teams/clear_selection_confirm_assets.png") is None:
                break


@begin_and_finish_time_log(task_name="罪人编队")
# 编队
def team_formation(sinner_team):
    scale = cfg.set_win_size/1440

    clean_team()
    while auto.take_screenshot() is None:
        continue
    announcer_position = auto.find_element("teams/announcer_assets.png")
    first_sinner = [announcer_position[0] + 350 * scale, announcer_position[1]]

    for sinner in sinner_team:
        name = pic_path + all_sinner[sinner] + '_assets.png'
        if not auto.click_element(name):
            if sinner <= 6:
                auto.mouse_click(first_sinner[0] + 270 * (sinner - 1) * scale, first_sinner[1])
            elif sinner <= 10:
                auto.mouse_click(first_sinner[0] + 270 * (sinner - 7) * scale,first_sinner[1] + 500 * scale)
            else:
                auto.mouse_click(first_sinner[0] + 270 * (sinner - 8) * scale,first_sinner[1] + 500 * scale)


@begin_and_finish_time_log(task_name="寻找队伍")
# 找队
def select_battle_team(num):
    scale = cfg.set_win_size/1080
    my_position = [0, 150 * scale]
    find = False
    while auto.take_screenshot() is None:
        continue
    if position := auto.find_element("battle/teams_assets.png"):
        my_position[0] += position[0]
        my_position[1] += position[1]
        auto.mouse_drag(my_position[0],my_position[1], dy=1000 * scale, drag_time=0.2)
        #TODO: 多语言适配   if cfg.language == 'en':
        team_name = "TEAMS#"+str(num)
        team_name_error_correcting="TFAMS#"+str(num)
        for i in range(10):
            while auto.take_screenshot() is None:
                continue
            if auto.click_element(team_name,find_type="text",offset=False):
                find = True
                break
            if auto.click_element(team_name_error_correcting,find_type="text",offset=False):
                find = True
                break
            auto.mouse_drag(my_position[0],my_position[1], dy=-200 * scale, drag_time=1.5)
            sleep(1)
            while auto.take_screenshot() is None:
                continue
    if find:
        msg = f"成功找到队伍 # {num}"
        log.INFO(msg)
        sleep(1)
        return True
    else:
        msg = f"找不到队伍 # {num}"
        log.INFO(msg)
        return False


@begin_and_finish_time_log(task_name="检查队伍剩余战斗力")
def check_team():
    # 至少还有5人可以战斗
    sinner_nums = [f"{a}/{b}" for b in range(5, 10) for a in range(5, b + 1)]
    if auto.find_element(sinner_nums,find_type="text"):
        return True
    else:
        return False

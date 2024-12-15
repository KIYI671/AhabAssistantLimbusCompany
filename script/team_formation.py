from os import environ
from time import sleep

from command.get_position import get_pic_position, get_all_pic_position
from command.mouse_activity import mouse_click, mouse_drag
from my_decorator.decorator import begin_and_finish_log,begin_and_finish_time_log
from my_log.my_log import my_log
from my_ocr.ocr import get_all_team, search_team_number, commom_gain_text, commom_all_ocr, commom_range_ocr, \
    find_and_click_text

all_sinner = {
    1: "YiSang", 2: "Faust", 3: "DonQuixote",
    4: "Ryoshu", 5: "Meursault", 6: "HongLu",
    7: "Heathcliff", 8: "Ishmael", 9: "Rodion",
    10: "Dante",
    11: "Sinclair", 12: "Outis", 13: "Gregor"
}

pic_path = "./pic/teams/"


# 清队
def clean_team():
    find_and_click_text("clear")
    find_and_click_text("confirm")


@begin_and_finish_time_log(task_name="罪人编队")
# 编队
def team_formation(sinner_team):
    scale = 0
    if environ.get('window_size'):
        scale = int(environ.get('window_size'))
    scale_factors = [0.75, 1.0, 0.5, 0.625, 1.25, 1.5]
    clean_team()
    announcer_position = get_pic_position("./pic/teams/announcer.png")
    first_sinner = [announcer_position[0] + 350 * scale_factors[scale], announcer_position[1]]

    for sinner in sinner_team:
        name = pic_path + all_sinner[sinner] + '.png'
        if my_sinner := get_pic_position(name):
            mouse_click(my_sinner)
        else:
            if sinner <= 6:
                mouse_click([first_sinner[0] + 270 * (sinner - 1) * scale_factors[scale], first_sinner[1]])
            elif sinner <= 10:
                mouse_click([first_sinner[0] + 270 * (sinner - 7) * scale_factors[scale],
                             first_sinner[1] + 500 * scale_factors[scale]])
            else:
                mouse_click([first_sinner[0] + 270 * (sinner - 8) * scale_factors[scale],
                             first_sinner[1] + 500 * scale_factors[scale]])


@begin_and_finish_time_log(task_name="寻找队伍")
# 找队
def select_battle_team(num):
    scale = 0
    if environ.get('window_size'):
        scale = int(environ.get('window_size'))
    scale_factors = [1, 1.333, 0.667, 0.833, 1.667, 2]
    my_position = [0, 150 * scale_factors[scale]]
    find = False
    if position := get_pic_position("./pic/teams/teams.png"):
        my_position[0] += position[0]
        my_position[1] += position[1]
        mouse_drag(my_position, y=1000 * scale_factors[scale], time=0.2)
        for i in range(10):
            pic_byte_stream = get_all_team("./pic/teams/teams.png")
            if team_position := search_team_number(pic_byte_stream[0], num):
                mouse_click(team_position)
                find = True
                break
            mouse_drag(my_position, y=-200 * scale_factors[scale], time=1.5)
            sleep(1)
    if find:
        msg = f"成功找到队伍 # {num}"
        my_log("info", msg)
        sleep(1)
        return True
    else:
        msg = f"找不到队伍"
        my_log("info", msg)
        return False


@begin_and_finish_time_log(task_name="检查队伍剩余战斗力")
def check_team():
    leave = commom_gain_text(commom_all_ocr()[0], language="models/config_chinese.txt")
    # 至少还有5人可以战斗
    sinner_nums = [f"{a}/{b}" for b in range(5, 10) for a in range(5, b + 1)]
    p1, p2 = None, None
    for b in leave:
        if "selection" in b['text'].lower():
            box = b['box']
            p1 = [box[0][0], box[0][1]]
            p2 = [box[2][0], box[2][1]]
    p2[1] += 180
    leave = commom_gain_text(commom_range_ocr(p1, p2), language="models/config_chinese.txt")
    all_text = ""
    for b in leave:
        all_text += b['text'].lower() + " "
    # 如果还有至少5人能战斗就继续，不然就退出重开
    if any(sinner in all_text for sinner in sinner_nums):
        return True
    else:
        return False

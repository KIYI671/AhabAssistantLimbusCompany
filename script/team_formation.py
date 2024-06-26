from time import sleep

from command.get_position import get_pic_position, get_all_pic_position
from command.mouse_activity import mouse_click, mouse_drag
from my_decorator.decorator import begin_and_finish_log
from my_log.my_log import my_log
from my_ocr.ocr import get_all_team, search_team_number

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
    if team_selected := get_all_pic_position("./pic/teams/selected.png"):
        for sinner in team_selected:
            mouse_click(sinner)


@begin_and_finish_log(task_name="罪人编队")
# 编队
def team_formation(sinner_team):
    clean_team()
    while get_pic_position("./pic/teams/full_team.png", 0.9) is None:
        for sinner in sinner_team:
            name = pic_path + all_sinner[sinner] + '.png'
            if my_sinner := get_pic_position(name):
                mouse_click(my_sinner)
        if get_pic_position("./pic/teams/full_team.png") is None:
            clean_team()


@begin_and_finish_log(task_name="寻找队伍")
# 找队
def select_battle_team(num):
    my_position = [0, 150]
    find = False
    if position := get_pic_position("./pic/teams/teams.png"):
        my_position[0] += position[0]
        my_position[1] += position[1]
        mouse_drag(my_position, y=1000, time=0.2)
        for i in range(10):
            pic_byte_stream = get_all_team("./pic/teams/teams.png")
            if team_position := search_team_number(pic_byte_stream[0], num):

                mouse_click(team_position)
                find = True
                break
            mouse_drag(my_position, y=-200, time=1.5)
            sleep(1)
    if find:
        msg = f"成功找到队伍"
        my_log("info", msg)
        return True
    else:
        msg = f"找不到队伍"
        my_log("info", msg)
        return False

from command.get_position import get_pic_position
from command.mouse_activity import mouse_click


def team_preparation():
    if get_pic_position("./pic/teams/to_battle.png") :
        mouse_click(get_pic_position("./pic/teams/to_battle.png"))
    else:
        pass

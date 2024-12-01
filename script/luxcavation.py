from command.get_position import get_pic_position, get_pic_temp_position
from command.mouse_activity import mouse_click


def EXP_luxcavation():
    level_select = ["./pic/luxcavation/EXP_lv48_1.png", "./pic/luxcavation/EXP_lv48_2.png",
                    "./pic/luxcavation/EXP_lv48_3.png", "./pic/luxcavation/EXP_lv43.png",
                    "./pic/luxcavation/EXP_lv38.png",
                    "./pic/luxcavation/EXP_lv33.png",
                    "./pic/luxcavation/EXP_lv28.png",
                    "./pic/luxcavation/EXP_lv18.png", "./pic/luxcavation/EXP_lv8.png"]
    while get_pic_position("./pic/scenes/drive_features.png") is None:
        mouse_click(get_pic_position("./pic/scenes/init_drive.png"))
    mouse_click(get_pic_position("./pic/luxcavation/luxcavation.png"))
    temp_position1, temp_position2 = None, None
    for level in level_select:
        temp_position1 = get_pic_temp_position(level)
        if temp_position1:
            temp_position2 = get_pic_position("./pic/luxcavation/EXP_enter.png",
                                              screenshot=level)
            break
    if temp_position1 and temp_position2:
        position = (temp_position1[0] + temp_position2[0], temp_position1[1] + temp_position2[1])
        mouse_click(position)
    else:
        print("no position")


def thread_luxcavation():
    while get_pic_position("./pic/scenes/drive_features.png") is None:
        mouse_click(get_pic_position("./pic/scenes/init_drive.png"))
    mouse_click(get_pic_position("./pic/luxcavation/luxcavation.png"))
    mouse_click(get_pic_position("./pic/luxcavation/thread.png"))
    temp_position1 = get_pic_temp_position("./pic/luxcavation/first_thread.png")
    temp_position2 = get_pic_position("./pic/luxcavation/thread_enter.png",
                                      screenshot="./pic/luxcavation/first_thread.png")
    position = (temp_position1[0] + temp_position2[0], temp_position1[1] + temp_position2[1])
    mouse_click(position)
    level_select = ["./pic/luxcavation/thread_lv50.png", "./pic/luxcavation/thread_lv40.png",
                    "./pic/luxcavation/thread_lv30.png",
                    "./pic/luxcavation/thread_lv20.png"]
    for level in level_select:
        if get_pic_position(level):
            mouse_click(get_pic_position(level))
            break

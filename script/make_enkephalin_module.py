from command.get_position import get_pic_position
from command.mouse_activity import mouse_click
from my_decorator.decorator import begin_and_finish_log


@begin_and_finish_log(task_name="体力换饼")
def make_enkephalin_module():
    while get_pic_position("./pic/scenes/charge_enkephalin.png") is None:
        mouse_click(get_pic_position("./pic/enkephalin/enkephalin_box.png"))
    if max_module := get_pic_position("./pic/enkephalin/max_module.png"):
        mouse_click(max_module)
    if confirm_make_module := get_pic_position("./pic/enkephalin/confirm.png"):
        mouse_click(confirm_make_module)
    mouse_click(get_pic_position("./pic/enkephalin/leave_cancel.png"))


@begin_and_finish_log(task_name="狂气换体")
def lunacy_to_enkephalin(times=0):
    # 待加入葛朗台模式!!!
    make_enkephalin_module()
    while get_pic_position("./pic/scenes/charge_enkephalin.png") is None:
        mouse_click(get_pic_position("./pic/enkephalin/enkephalin_box.png"))
    mouse_click(get_pic_position("./pic/enkephalin/use_lunacy.png"))
    if times >= 1:
        if get_pic_position("./pic/enkephalin/26lunacy.png") and get_pic_position(
                "./pic/enkephalin/first_exchange.png"):
            mouse_click(get_pic_position("./pic/enkephalin/confirm.png"))
    if times == 2:
        if get_pic_position("./pic/enkephalin/52lunacy.png") and get_pic_position(
                "./pic/enkephalin/second_exchange.png"):
            mouse_click(get_pic_position("./pic/enkephalin/confirm.png"))
    mouse_click(get_pic_position("./pic/enkephalin/modules.png"))
    if get_pic_position("./pic/enkephalin/max_module.png"):
        mouse_click(get_pic_position("./pic/enkephalin/max_module.png"))
    if get_pic_position("./pic/enkephalin/confirm.png"):
        mouse_click(get_pic_position("./pic/enkephalin/confirm.png"))
    mouse_click(get_pic_position("./pic/enkephalin/leave_cancel.png"))

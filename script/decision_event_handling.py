from command.get_position import get_pic_position
from command.mouse_activity import mouse_click


def decision_event_handling():
    if best_option := get_pic_position("./pic/event/very_high.png"):
        mouse_click(best_option)
    elif best_option := get_pic_position("./pic/event/high.png"):
        mouse_click(best_option)
    elif best_option := get_pic_position("./pic/event/normal.png"):
        mouse_click(best_option)
    elif best_option := get_pic_position("./pic/event/low.png"):
        mouse_click(best_option)
    elif best_option := get_pic_position("./pic/event/very_low.png"):
        mouse_click(best_option)
    if commence_button := get_pic_position("./pic/event/commence.png"):
        mouse_click(commence_button)

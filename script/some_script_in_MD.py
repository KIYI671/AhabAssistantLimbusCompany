from time import sleep

from command.get_position import get_pic_position
from command.mouse_activity import mouse_click
from my_decorator.decorator import begin_and_finish_log


@begin_and_finish_log(task_name="镜牢获取奖励卡")
# 获取奖励卡
def get_reward_card():
    all_cards = ["./pic/mirror/gain_ego_resource.png", "./pic/mirror/gain_cost.png",
                 "./pic/mirror/gain_ego.png", "./pic/mirror/gain_cost_and_ego.png"]
    for card in all_cards[::-1]:
        card_position = get_pic_position(card)
        if card_position:
            mouse_click(card_position)
            break
    if reward_card_confirm := get_pic_position("./pic/mirror/reward_card_confirm.png"):
        mouse_click(reward_card_confirm)
        sleep(2)
        if ego_gift_get_confirm := get_pic_position("./pic/mirror/ego_gift_get_confirm.png"):
            mouse_click(ego_gift_get_confirm)
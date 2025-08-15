from module.automation import auto
from module.decorator.decorator import begin_and_finish_time_log
from module.logger import log
from tasks.base.retry import retry
from utils.image_utils import ImageUtils

reward_card_model = {0: ["gain_starlight", "gain_ego", "gain_cost", "gain_cost_and_ego", "gain_ego_resource"],
                     1: ["gain_starlight", "gain_ego", "gain_cost", "gain_cost_and_ego", "gain_ego_resource"],
                     2: ["gain_starlight", "gain_cost", "gain_ego", "gain_cost_and_ego", "gain_ego_resource"],
                     3: ["gain_cost", "gain_ego", "gain_cost_and_ego", "gain_ego_resource", "gain_starlight"],
                     4: ["gain_ego", "gain_cost", "gain_cost_and_ego", "gain_ego_resource", "gain_starlight"]}


@begin_and_finish_time_log(task_name="镜牢获取奖励卡", calculate_time=False)
# 获取奖励卡
def get_reward_card(model=0):
    loop_count = 30
    auto.model = 'clam'
    reward_card = reward_card_model[model]
    while True:
        # 自动截图
        if auto.take_screenshot() is None:
            continue
        auto.mouse_to_blank()
        if auto.find_element("mirror/road_in_mir/legend_assets.png"):
            break
        if auto.find_element("mirror/road_in_mir/acquire_ego_gift.png"):
            break
        if auto.click_element("mirror/get_reward_card/continue_choosing_assets.png", model='clam'):
            continue
        select_reward = False
        for card in reward_card:
            if auto.click_element(f"mirror/get_reward_card/{card}.png"):
                select_reward = True
                break
        if select_reward:
            break
        if auto.click_element("mirror/road_in_mir/ego_gift_get_confirm_assets.png"):
            break
        if retry() is False:
            return False
        loop_count -= 1
        if loop_count < 20:
            auto.model = "normal"
        if loop_count < 10:
            auto.model = 'aggressive'
        if loop_count < 0:
            log.ERROR("无法获取奖励卡")
            return
    if retry() is False:
        return False
    get_reward_card_confirm_bbox = ImageUtils.get_bbox(
        ImageUtils.load_image("mirror/get_reward_card/get_reward_card_confirm_assets.png"))
    auto.mouse_click((get_reward_card_confirm_bbox[0] + get_reward_card_confirm_bbox[2]) / 2,
                     (get_reward_card_confirm_bbox[1] + get_reward_card_confirm_bbox[3]) / 2)
    while auto.click_element("mirror/get_reward_card/get_reward_card_confirm_assets.png", threshold=0.75):
        while auto.take_screenshot() is None:
            continue
        auto.mouse_to_blank()
        if auto.click_element("mirror/get_reward_card/continue_choosing_assets.png", model='clam'):
            break
        continue

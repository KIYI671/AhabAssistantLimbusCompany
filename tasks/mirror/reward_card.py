from module.automation import auto
from module.decorator.decorator import begin_and_finish_time_log
from module.logger import log
from tasks.base.retry import retry


@begin_and_finish_time_log(task_name="镜牢获取奖励卡", calculate_time=False)
# 获取奖励卡
def get_reward_card():
    loop_count = 30
    auto.model = 'clam'
    while True:
        # 自动截图
        if auto.take_screenshot() is None:
            continue
        if auto.find_element("mirror/road_in_mir/legend_assets.png"):
            break
        if auto.find_element("mirror/road_in_mir/acquire_ego_gift.png"):
            break
        if auto.click_element("mirror/get_reward_card/gain_cost_and_ego.png"):
            break
        if auto.click_element("mirror/get_reward_card/gain_ego.png"):
            break
        if auto.click_element("mirror/get_reward_card/gain_cost.png"):
            break
        if auto.click_element("mirror/get_reward_card/gain_ego_resource.png"):
            break
        retry()
        loop_count -= 1
        if loop_count < 20:
            auto.model = "normal"
        if loop_count < 10:
            auto.model = 'aggressive'
        if loop_count < 0:
            log.ERROR("无法获取奖励卡")
            return
    while auto.click_element("mirror/get_reward_card/get_reward_card_confirm_assets.png"):
        while auto.take_screenshot() is None:
            continue
        continue

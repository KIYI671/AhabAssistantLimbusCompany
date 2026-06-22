from time import monotonic

from module.automation import auto
from module.decorator.decorator import begin_and_finish_time_log
from module.logger import log
from tasks.base.retry import retry

reward_card_model = {
    0: [
        "gain_starlight",
        "gain_ego",
        "gain_cost",
        "gain_cost_and_ego",
        "gain_ego_resource",
    ],
    1: [
        "gain_starlight",
        "gain_cost",
        "gain_ego",
        "gain_cost_and_ego",
        "gain_ego_resource",
    ],
    2: [
        "gain_cost",
        "gain_ego",
        "gain_cost_and_ego",
        "gain_ego_resource",
        "gain_starlight",
    ],
    3: [
        "gain_ego",
        "gain_cost",
        "gain_cost_and_ego",
        "gain_ego_resource",
        "gain_starlight",
    ],
}

_CLAIM_RETRY_DELAY = 5.0


@begin_and_finish_time_log(task_name="镜牢获取奖励卡", calculate_time=False)
# 获取奖励卡
def get_reward_card(model=0):
    loop_count = 30
    claim_retry_at = 0.0
    state = "select_reward"
    auto.model = "clam"
    reward_card = reward_card_model[model]
    while True:
        # 自动截图
        if auto.take_screenshot() is None:
            continue
        auto.mouse_to_blank()
        if auto.find_element("mirror/road_in_mir/legend_assets.png"):
            return True
        if auto.click_element("mirror/road_in_mir/ego_gift_get_confirm_assets.png", model="clam"):
            log.debug("奖励卡领取后识别到EGO确认，领取流程结束")
            return True
        if auto.find_element("mirror/road_in_mir/acquire_ego_gift_card.png"):
            log.debug("奖励卡领取后进入饰品选择，交回镜牢主循环处理")
            return True
        if auto.click_element("mirror/get_reward_card/continue_choosing_assets.png", model="clam"):
            state = "select_reward"
            continue

        if state == "claim_reward":
            if confirm_position := auto.find_element(
                "mirror/get_reward_card/get_reward_card_confirm_assets.png",
                threshold=0.75,
                model="clam",
            ):
                auto.mouse_click(confirm_position[0], confirm_position[1])
                claim_retry_at = monotonic() + _CLAIM_RETRY_DELAY
                state = "wait_result"
                log.debug("已点击奖励卡领取按钮，等待页面切换")
                continue

        elif state == "wait_result":
            if confirm_position := auto.find_element(
                "mirror/get_reward_card/get_reward_card_confirm_assets.png",
                threshold=0.75,
                model="clam",
            ):
                if monotonic() >= claim_retry_at:
                    auto.mouse_click(confirm_position[0], confirm_position[1])
                    claim_retry_at = monotonic() + _CLAIM_RETRY_DELAY
                    log.debug("奖励卡领取按钮仍在原位置，重新点击")
                    continue

        if state == "select_reward":
            select_reward = False
            for card in reward_card:
                if auto.click_element(f"mirror/get_reward_card/{card}.png"):
                    select_reward = True
                    break
            if select_reward:
                state = "claim_reward"
                continue
        if retry() is False:
            return False
        loop_count -= 1
        if loop_count < 20:
            auto.model = "normal"
        if loop_count < 10:
            auto.model = "aggressive"
        if loop_count < 0:
            log.error("无法获取奖励卡")
            return False

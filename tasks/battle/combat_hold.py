"""Optional centre hold while the original pause-button signal is visible."""

from time import monotonic

from module.my_error.my_error import userStopError


class CombatSpeedHold:
    def __init__(self, auto, running=lambda: True, logger=None):
        self.auto, self.running, self.log = auto, running, logger
        self.active, self.blocked, self.since = False, False, 0.0

    def visible(self):
        if not self.running() or not self.auto.find_element("battle/pause_assets.png"):
            return False
        return not any(self.auto.find_element(marker) for marker in (
            "battle/dead_all.png", "battle/battle_finish_confirm_assets.png", "battle/continue_assets.png",
            "mirror/road_in_mir/select_encounter_reward_card_assets.png",
            "mirror/road_in_mir/acquire_ego_gift_card.png", "mirror/road_in_mir/legend_assets.png",
            "mirror/claim_reward/battle_statistics_assets.png", "event/choices_assets.png", "base/waiting_assets.png",
        ))

    def release(self, block=False):
        if self.active:
            self.auto.mouse_end_hold()
            if self.log:
                self.log.debug("长按加速：已松开鼠标")
        self.active = False
        if block:
            self.blocked = True

    def update(self, visible):
        if not self.running() or not visible:
            self.release()
            self.blocked = False
            return False
        if self.active and (monotonic() - self.since >= 30 or not self.auto.input_handler.has_active_hold()):
            self.release(block=True)
            if self.log:
                self.log.info("长按加速：已达到单次30秒上限，等待加速信号消失后重新启用")
        if self.blocked:
            return False
        try:
            if not self.active:
                width, height = self.auto.screenshot.size
                self.auto.mouse_begin_hold(width / 2, height / 2, max_duration=30)
                self.active, self.since = True, monotonic()
                if self.log:
                    self.log.debug("长按加速：识别到加速信号，长按屏幕中央")
            self.auto.mouse_keep_hold()
            return True
        except userStopError:
            self.release(block=True)
            raise
        except Exception as error:
            self.release(block=True)
            if self.log:
                self.log.warning(f"交战中加速未完成，继续原战斗流程：{error}")
            return False

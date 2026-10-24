"""Bounded battle retries and explicit, verified abandonment of a mirror run."""

from time import sleep

from tasks.mirror.settlement import settlement_wait


class MirrorBattleAttemptsExhausted(RuntimeError):
    pass


class BattleAttemptBudget:
    def __init__(self, limit=4):
        if limit < 1:
            raise ValueError("attempt limit must be positive")
        self.limit, self.failures, self.defeat_latched = limit, 0, False

    def defeat(self):
        if not self.defeat_latched:
            self.failures += 1
            self.defeat_latched = True
        if self.failures >= self.limit:
            raise MirrorBattleAttemptsExhausted(f"本关已尝试 {self.limit} 次仍失败，放弃本次镜牢")

    def combat_resumed(self):
        self.defeat_latched = False


class DefeatDialogAction:
    """Choose row 2/3 in the supplied defeat dialog; submit only once per page.

    Positions are offsets from its recognized Confirm button, in 1080 client
    pixels. No desktop/window-title coordinates or translated row OCR is used.
    """

    def __init__(self):
        self.reset()

    def reset(self):
        self.selected = False
        self.submitted = False

    def submit(self, auto, *, retry, config, pause=sleep):
        if self.submitted:
            return False
        confirm = auto.find_element("battle/dead_all_confirm_assets.png")
        if not confirm:
            return False
        if not self.selected:
            # The first recognized frame may still be the dialog's slide-in.
            pause(settlement_wait(config))
            if auto.take_screenshot() is None:
                return False
            confirm = auto.find_element("battle/dead_all_confirm_assets.png")
            if not confirm:
                return False
            screenshot = getattr(auto, "screenshot", None)
            height = screenshot.height if screenshot is not None else config.set_win_size
            scale = height / 1080
            # Reference: Confirm=(973,790), Retry=(1189,532), Accept=(1189,670).
            point = (confirm[0] + 216 * scale,
                     confirm[1] - (258 if retry else 120) * scale)
            auto.wait_pause()
            auto.mouse_click(*point)
            self.selected = True
            pause(settlement_wait(config))
        auto.wait_pause()
        if auto.click_element("battle/dead_all_confirm_assets.png", take_screenshot=True, offset=False):
            self.submitted = True
            pause(settlement_wait(config))
            return True
        return False


def forfeit_failed_run(auto, log, *, running=lambda: True, max_steps=90, pause=sleep, already_exited=False, config=None):
    """No currency/reward confirmation is permitted before clicking Forfeit.

    Only a confirmed return home completes the abandonment. Unrecognized UI
    stops the task, leaving the scheduled run count unchanged.
    """
    exit_requested = False
    reward_forfeited = False
    defeat_action = DefeatDialogAction()
    accepted_defeat = False
    reward_choice_opened = False
    reward_confirmed = False
    if config is None:
        from types import SimpleNamespace
        config = SimpleNamespace(set_win_size=1440, mouse_action_interval=.5, screenshot_interval=.85)
    for _ in range(max_steps):
        if not running():
            raise RuntimeError("放弃镜牢已停止，未扣除次数")
        auto.wait_pause()
        if auto.take_screenshot() is None:
            pause(0.2)
            continue
        if auto.find_element("home/drive_assets.png") and auto.find_element("home/mail_assets.png"):
            if not reward_forfeited:
                raise RuntimeError("已返回主界面，但未核实放弃流程；停止并保留次数")
            log.info("已退出镜牢并放弃奖励，本次计入已用次数")
            return True
        if auto.find_element("base/waiting_assets.png") or auto.find_element("base/waiting_2_assets.png"):
            pause(0.5)
            continue
        if reward_forfeited:
            if not reward_confirmed and auto.click_element(
                "mirror/claim_reward/claim_rewards_confirm_assets.png", model="normal", offset=False,
            ):
                reward_confirmed = True
                pause(settlement_wait(config))
                continue
            pause(settlement_wait(config))
            continue
        if auto.click_element("battle/battle_finish_confirm_assets.png", offset=False):
            pause(settlement_wait(config))
            continue
        if (
            already_exited or auto.find_element("mirror/claim_reward/claim_rewards_assets.png")
            or auto.find_element("mirror/claim_reward/battle_statistics_assets.png")
            or auto.find_element("mirror/claim_reward/use_enkephalin_assets.png")
        ):
            if auto.click_element("mirror/claim_reward/claim_forfeit_assets.png", model="normal", offset=False):
                reward_forfeited = True
            else:
                # Open the reward choice, then select its explicit X/Forfeit.
                if not reward_choice_opened and auto.click_element("mirror/claim_reward/claim_rewards_assets.png", offset=False):
                    reward_choice_opened = True
                elif already_exited or reward_choice_opened:
                    forfeit = auto.find_language_text(["放弃奖励", "放弃领取"], ["Forfeit Rewards", "Forfeit"])
                    if forfeit:
                        auto.mouse_click(*forfeit)
                        reward_forfeited = True
                    elif not reward_choice_opened:
                        # Zero-progress rewards have a disabled Claim button.
                        auto.key_press("esc")
            pause(settlement_wait(config))
            continue
        if exit_requested and auto.click_element("mirror/road_in_mir/towindow&forfeit_confirm_assets.png", offset=False):
            already_exited = True
            pause(settlement_wait(config))
            continue
        if auto.find_element("battle/dead_all.png"):
            if defeat_action.submit(auto, retry=False, config=config, pause=pause):
                accepted_defeat = True
            pause(0.5)
            continue
        if accepted_defeat:
            # Accepting the result only returns to the entry page. Start the
            # existing Esc -> exit exploration -> forfeit rewards chain next.
            auto.key_press("esc")
            accepted_defeat = False
            pause(settlement_wait(config))
            continue
        if not exit_requested and auto.click_element("mirror/road_in_mir/forfeit_assets.png", offset=False):
            exit_requested = True
            pause(settlement_wait(config))
            continue
        if auto.click_element("battle/give_up_assets.png"):
            continue
        if auto.click_element("battle/normal_give_up_assets.png"):
            continue
        if auto.click_element("mirror/road_in_mir/setting_assets.png"):
            pause(settlement_wait(config))
            continue
        if auto.click_element("battle/setting_assets.png"):
            pause(settlement_wait(config))
            continue
        auto.key_press("esc")
        pause(0.5)
    raise RuntimeError("未能核实退出镜牢并放弃奖励，已停止；本次尚未扣除次数，请人工检查")

"""Exit exploration for a failed observation; reward handling stays in Mirror.run."""

from enum import Enum
from time import sleep


class MirrorRunOutcome(Enum):
    ABANDONED = "observation_abandoned"
    DEVELOPER_NO_REWARDS = "developer_no_rewards"


class ObservationCleanupError(RuntimeError):
    """No confirmed cancellation/exit: stop without counting an abandoned run."""


def exit_failed_observation(auto, logger, pause=sleep, max_steps=24):
    """Use the original settings/forfeit/confirm sequence, with a finite wait."""
    requested = False
    for _ in range(max_steps):
        auto.wait_pause()
        if auto.take_screenshot() is None:
            continue
        if auto.find_element("mirror/claim_reward/battle_statistics_assets.png"):
            return
        if requested:
            if auto.click_element("mirror/road_in_mir/towindow&forfeit_confirm_assets.png"):
                return
            # The normal button template may differ by theme; constrain this
            # fallback to the exploration-termination dialog, never reward use.
            width, height = auto.screenshot.size
            crop = (int(width * .25), int(height * .12), int(width * .75), int(height * .8))
            words = auto._run_ocr_for_text(my_crop=crop)
            if isinstance(words, dict):
                text = "".join("".join(words).split()).casefold()
                if any(token in text for token in ("终止迷宫探索", "terminateexploration", "terminatelabyrinth")):
                    for label, point in words.items():
                        if label.strip().casefold() in {"确认", "confirm"}:
                            auto.mouse_click(point[0] + crop[0], point[1] + crop[1])
                            return
            pause(.3)
            continue
        if auto.click_element("mirror/road_in_mir/forfeit_assets.png"):
            requested = True
            continue
        if auto.click_element("mirror/theme_pack/theme_pack_setting_assets.png") or auto.click_element(
            "mirror/road_in_mir/setting_assets.png"
        ):
            continue
        pause(.3)
    logger.error("观测失败后未能确认退出探索，保留现场，不扣次数")
    raise ObservationCleanupError("观测失败：退出探索未确认，不扣次数")

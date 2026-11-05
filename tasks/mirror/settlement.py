"""Local settlement transitions; never a replacement for global input timing."""

from time import sleep


def settlement_wait(config):
    return max(1.0, float(getattr(config, "mouse_action_interval", 0) or .5),
               float(getattr(config, "screenshot_interval", 0) or .85))


class ExplorationExit:
    """Select each exit stage once and wait for its next visible state."""

    def __init__(self):
        self.requested = False
        self.opened = False
        self.steps = 0

    def advance(self, auto, config, *, pause=sleep):
        self.steps += 1
        if self.steps > 60:
            raise RuntimeError("退出探索未确认，保留现场，不进入领奖或扣次")
        if auto.click_element("mirror/road_in_mir/towindow&forfeit_confirm_assets.png", offset=False):
            pause(settlement_wait(config))
            return True
        if not self.requested and auto.click_element("mirror/road_in_mir/forfeit_assets.png", offset=False):
            self.requested = True
            pause(settlement_wait(config))
            return False
        if not self.requested and not self.opened:
            if auto.click_element("mirror/road_in_mir/setting_assets.png", offset=False) or auto.click_element(
                "mirror/theme_pack/theme_pack_setting_assets.png", offset=False,
            ):
                self.opened = True
        pause(settlement_wait(config))
        return False

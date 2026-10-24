"""One input owner for either combat or EGO animation acceleration."""

from tasks.battle.animation_hold import overclock_banner
from tasks.battle.combat_hold import CombatSpeedHold
from utils.animation_signals import corner_play_marker, total_marker, visual_overclock


class UnifiedSpeedHold(CombatSpeedHold):
    def __init__(self, auto, running=lambda: True, logger=None):
        super().__init__(auto, running, logger)
        self.combat_visible = self.signal_visible = False

    def probe(self):
        """Probe once per captured frame; terminal screens override both signals."""
        self.combat_visible = self.signal_visible = False
        if not self.running():
            self.update(False)
            return False
        if any(self.auto.find_element(marker) for marker in (
            "battle/dead_all.png", "battle/battle_finish_confirm_assets.png", "battle/continue_assets.png",
            "mirror/road_in_mir/select_encounter_reward_card_assets.png",
            "mirror/road_in_mir/acquire_ego_gift_card.png", "mirror/road_in_mir/legend_assets.png",
            "mirror/claim_reward/battle_statistics_assets.png", "event/choices_assets.png", "base/waiting_assets.png",
        )):
            self.update(False)
            return False
        self.combat_visible = bool(self.auto.find_element("battle/pause_assets.png"))
        if self.combat_visible:
            self.signal_visible = True
        elif not (self.auto.find_element("battle/gear_left.png", threshold=0.9) or
                  self.auto.find_element("battle/win_rate_assets.png", threshold=0.9)):
            # Preserve the fast image/TOTAL path before slower banner OCR.
            self.signal_visible = bool(corner_play_marker(self.auto) or visual_overclock(self.auto)
                                       or total_marker(self.auto) or overclock_banner(self.auto))
        self.update(self.signal_visible)
        # A still-visible signal after the limit must not restart a hold or
        # fall through to repeated centre clicks. Rearm only after both vanish.
        return self.signal_visible

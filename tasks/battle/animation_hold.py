"""Optional animation acceleration copied from faust.11."""
from functools import wraps
from time import monotonic, sleep

from utils.animation_signals import corner_play_marker, total_marker, visual_overclock


def overclock_banner(auto):
    if visual_overclock(auto):
        return True
    width, height = auto.screenshot.size
    words = auto._run_ocr_for_text(my_crop=(int(width * 0.25), 0, width, int(height * 0.25)), only_text=True)
    text = "".join(c for c in "".join(words or []).upper() if c.isalpha())
    return "OVERCLOCK" in text and "WARNING" in text


class ContinuousAnimationHold:
    def __init__(self, auto, running=lambda: True, logger=None):
        self.auto, self.running = auto, running
        self.log = logger
        self.active, self.since = False, 0.0
        self.pending, self.pending_since = False, 0.0
        self.blocked, self.misses, self.animation_visible = False, 0, False

    def arm(self):
        """Remember the EGO request; it never starts a hold by itself."""
        self.pending, self.pending_since = True, monotonic()

    def release(self, block=False):
        if self.active:
            self.auto.mouse_end_hold()
            if self.log:
                self.log.debug("动画加速：已松开鼠标")
        self.active, self.pending = False, False
        if block:
            self.blocked = True

    def _limit_reached(self):
        if self.active and (monotonic() - self.since >= 30 or not self.auto.input_handler.has_active_hold()):
            if self.log:
                self.log.info("动画加速：本次长按达到上限或输入已释放，等待动画结束后再启用")
            self.release(block=True)
            return True
        return False

    def start_from_visual(self):
        """Start on the current frame before slower text OCR blocks input."""
        if self.active or self.blocked or not self.running():
            return False
        if corner_play_marker(self.auto) or visual_overclock(self.auto) or total_marker(self.auto):
            return self.update(known_visible=True)
        return False

    def update(self, known_visible=None):
        if not self.running():
            self.release()
            return False
        # Check before image/OCR work. The input adapter also has an independent
        # timer, so a slow recognition call cannot keep the mouse down forever.
        if self._limit_reached():
            return False
        for marker in (
            "battle/dead_all.png",
            "battle/battle_finish_confirm_assets.png",
            "battle/continue_assets.png",
            "mirror/road_in_mir/acquire_ego_gift_card.png",
            "mirror/road_in_mir/legend_assets.png",
            "mirror/claim_reward/battle_statistics_assets.png",
            "event/choices_assets.png",
            "mirror/road_in_mir/select_encounter_reward_card_assets.png",
        ):
            if self.auto.find_element(marker):
                self.release(block=True)
                self.animation_visible = False
                return False
        if self.auto.find_element("battle/gear_left.png", threshold=0.9) or self.auto.find_element(
            "battle/win_rate_assets.png", threshold=0.9
        ):
            self.release()
            self.blocked, self.misses, self.animation_visible = False, 0, False
            return False
        visible = known_visible if known_visible is not None else (
            corner_play_marker(self.auto) or overclock_banner(self.auto) or total_marker(self.auto)
        )
        self.animation_visible = bool(visible)
        if self._limit_reached():
            return False
        if visible:
            self.misses = 0
            if self.blocked:
                return False
            if not self.active:
                width, height = self.auto.screenshot.size
                self.since = monotonic()
                self.auto.mouse_begin_hold(width * 0.08, height * 0.78, max_duration=30)
                self.active = True
                self.pending = False
                if self.log:
                    self.log.debug("动画加速：识别到动画信号，开始长按（最多30秒）")
            self.auto.mouse_keep_hold()
        else:
            self.misses += 1
            if self.misses >= 2:
                self.release()
                self.blocked = False
        return self.active


def release_hold_on_exit(auto):
    def decorate(fn):
        @wraps(fn)
        def call(*args, **kwargs):
            try:
                return fn(*args, **kwargs)
            finally:
                auto.mouse_end_hold()

        return call

    return decorate


def optional_hold_cleanup(auto):
    def decorate(fn):
        @wraps(fn)
        def call(*args, **kwargs):
            if not (kwargs.get("speed_hold", False) or kwargs.get("rabbit_animation_hold", False) or kwargs.get("combat_speed_hold", False)):
                return fn(*args, **kwargs)
            try:
                return fn(*args, **kwargs)
            finally:
                auto.mouse_end_hold()
        return call
    return decorate

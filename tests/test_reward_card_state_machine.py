import unittest
from unittest import mock

import tasks.mirror.reward_card as reward_card_module

REWARD_CONFIRM = "mirror/get_reward_card/get_reward_card_confirm_assets.png"
EGO_CONFIRM = "mirror/road_in_mir/ego_gift_get_confirm_assets.png"
EGO_GIFT_SCREEN = "mirror/road_in_mir/acquire_ego_gift_card.png"
REWARD_SCREEN = "mirror/road_in_mir/select_encounter_reward_card_assets.png"


class _RewardCardAuto:
    def __init__(self, frames):
        self.frames = frames
        self.frame_index = -1
        self.model = None
        self.click_calls = []
        self.mouse_click_calls = []

    @property
    def frame(self):
        return self.frames[min(self.frame_index, len(self.frames) - 1)]

    def take_screenshot(self):
        self.frame_index += 1
        return object()

    def mouse_to_blank(self):
        return None

    def find_element(self, target, *_, **__):
        return self.frame.get(target, False)

    def click_element(self, target, *_, **__):
        position = self.find_element(target)
        if position:
            self.click_calls.append(target)
        return position

    def mouse_click(self, x, y, *_, **__):
        self.mouse_click_calls.append((x, y))
        return True


class TestRewardCardStateMachine(unittest.TestCase):
    def test_ego_confirm_ends_reward_card_flow(self):
        auto = _RewardCardAuto(
            [
                {"mirror/get_reward_card/gain_starlight.png": (500, 300)},
                {REWARD_CONFIRM: (1100, 800)},
                {EGO_CONFIRM: (900, 800)},
            ]
        )

        with (
            mock.patch.object(reward_card_module, "auto", auto),
            mock.patch.object(reward_card_module, "monotonic", return_value=0.0),
            mock.patch.object(reward_card_module, "retry", return_value=True),
        ):
            result = reward_card_module.get_reward_card()

        self.assertTrue(result)
        self.assertEqual(auto.mouse_click_calls, [(1100, 800)])
        self.assertIn(EGO_CONFIRM, auto.click_calls)

    def test_visible_claim_button_is_not_clicked_again_before_retry_delay(self):
        auto = _RewardCardAuto(
            [
                {"mirror/get_reward_card/gain_starlight.png": (500, 300)},
                {REWARD_CONFIRM: (1100, 800)},
                {REWARD_CONFIRM: (1100, 800)},
                {EGO_GIFT_SCREEN: (700, 400)},
            ]
        )

        with (
            mock.patch.object(reward_card_module, "auto", auto),
            mock.patch.object(reward_card_module, "monotonic", side_effect=[0.0, 1.0]),
            mock.patch.object(reward_card_module, "retry", return_value=True),
        ):
            result = reward_card_module.get_reward_card()

        self.assertTrue(result)
        self.assertEqual(auto.mouse_click_calls, [(1100, 800)])

    def test_claim_button_is_retried_after_delay(self):
        auto = _RewardCardAuto(
            [
                {"mirror/get_reward_card/gain_starlight.png": (500, 300)},
                {REWARD_CONFIRM: (1100, 800)},
                {REWARD_CONFIRM: (1100, 800)},
                {EGO_GIFT_SCREEN: (700, 400)},
            ]
        )

        with (
            mock.patch.object(reward_card_module, "auto", auto),
            mock.patch.object(reward_card_module, "monotonic", side_effect=[0.0, 6.0, 6.0]),
            mock.patch.object(reward_card_module, "retry", return_value=True),
        ):
            result = reward_card_module.get_reward_card()

        self.assertTrue(result)
        self.assertEqual(auto.mouse_click_calls, [(1100, 800), (1100, 800)])

    def test_reward_screen_false_positive_does_not_return_to_card_selection(self):
        gain_cost = "mirror/get_reward_card/gain_cost.png"
        auto = _RewardCardAuto(
            [
                {"mirror/get_reward_card/gain_starlight.png": (500, 300)},
                {REWARD_CONFIRM: (1100, 800)},
                {REWARD_SCREEN: (800, 200), gain_cost: (700, 300)},
                {EGO_GIFT_SCREEN: (700, 400)},
            ]
        )

        with (
            mock.patch.object(reward_card_module, "auto", auto),
            mock.patch.object(reward_card_module, "monotonic", return_value=0.0),
            mock.patch.object(reward_card_module, "retry", return_value=True),
        ):
            result = reward_card_module.get_reward_card()

        self.assertTrue(result)
        self.assertNotIn(gain_cost, auto.click_calls)
        self.assertEqual(auto.mouse_click_calls, [(1100, 800)])


if __name__ == "__main__":
    unittest.main()

"""Real artwork and offline input/state regressions for the integrated release."""

import sys
from functools import partial
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock, patch

import pytest
from PIL import Image, ImageEnhance
from test_added_options import NEEDLE_CAPTURE, icons, make_shop, schema
from test_optional_battle import ROOT, FakeAuto, actions, animation, battle_class_without_game_imports

from tasks.mirror.priority_purchase import ACQUIRED, COINS, PURCHASE, PurchaseResult, buy_specified, merchant_region












def ego_control(auto=None, state=None):
    return actions.TurnEgoAction(auto or FakeAuto(), 1440,
                                 actions.BattleOptions(ego_enabled=True, ego_name="空洞(le trou)"),
                                 Mock(), (0, 0, 120, 40), pause=lambda _: None, attempted_turns=state)


def test_slow_menu_second_frame_name_is_read_in_one_entry_attempt():
    auto = FakeAuto()
    actual_read = auto._run_ocr_for_text
    reads = [0]

    def read(**kwargs):
        if kwargs.get("only_text"):
            return actual_read(**kwargs)
        reads[0] += 1
        return {"胜率": (1000, 500)} if reads[0] == 1 else {"空洞(le trou)": (800, 350)}

    auto._run_ocr_for_text = read
    control = ego_control(auto)
    assert control.perform()
    assert [e[1] for e in auto.events if e[0] == "hold"] == [.8, 1.2]
    assert not control.perform()


def test_menu_not_open_retries_entry_once_then_reads_name_without_new_turn_attempt():
    auto = FakeAuto()
    reads = [0]

    def read(**kwargs):
        if kwargs.get("only_text"):
            return ["TURN 1"]
        reads[0] += 1
        return {"胜率": (1000, 500)} if reads[0] < 3 else {"空洞(le trou)": (800, 350)}

    auto._run_ocr_for_text = read
    control = ego_control(auto)
    assert control.perform()
    assert [e[1] for e in auto.events if e[0] == "hold"] == [.8, .8, 1.2]
    assert control.attempted_turns == {1}
    assert not control.perform()


def test_narrow_title_read_keeps_exact_name_and_maps_crop_coordinates():
    auto = FakeAuto()

    def read(**kwargs):
        if kwargs.get("only_text"):
            return ["TURN 1"]
        if kwargs["my_crop"][0] == 0:
            return {"侵蚀概率": (600, 200), "空洞": (900, 400)}
        return {"空洞(le trou)": (600, 200)}

    auto._run_ocr_for_text = read
    assert ego_control(auto).perform()
    assert ("click", 600 + int(2560 * .2), 200 + int(1440 * .32) - 170) in auto.events


def test_shared_state_same_turn_dedup_and_reset_after_observed_retry_or_rollback():
    shared = actions.EgoAttemptState()
    first = ego_control(state=shared)
    assert first.perform()
    assert not ego_control(state=shared).perform()  # reentry alone must not reset
    first.observe_running()
    assert ego_control(state=shared).perform()  # combat ran, then ready TURN 1 again
    assert shared == {1}
    shared.ready(3)
    shared.combat_seen = True
    assert ego_control(state=shared).perform()
    assert shared.last_turn == 1


def test_actual_defeat_retry_releases_ego_again_even_if_pause_is_visible_behind_dialog():
    auto = FakeAuto()
    state = ["first_ready"]
    auto.get_restore_time = lambda: None
    base_find = auto.find_element

    def find(path, **kw):
        if path == "battle/dead_all.png" and state[0] == "defeat":
            return [(10, 10), (20, 20), (30, 30)] if kw.get("find_type") else (10, 10)
        if path == "battle/pause_assets.png" and state[0] in {"first_running", "defeat"}:
            if state[0] == "first_running":
                state[0] = "pending_defeat"
            return (100, 100)
        if path == "battle/more_information_assets.png" and state[0] in {"first_ready", "retry_ready"}:
            return (100, 100)
        if path.endswith("select_encounter_reward_card_assets.png") and state[0] == "reward":
            return (100, 100)
        return base_find(path, **kw)

    def capture(**kw):
        if state[0] == "pending_defeat":
            state[0] = "defeat"
        return auto.screenshot

    def click_asset(path, **kw):
        if path.endswith("dead_all_confirm_assets.png"):
            state[0] = "retry_ready"
            return True
        return False

    def key(key):
        auto.events.append(("key", key))
        if key == "enter":
            state[0] = "first_running" if state[0] == "first_ready" else "reward"

    auto.find_element, auto.take_screenshot, auto.click_element, auto.key_press = find, capture, click_asset, key
    auto.mouse_click_blank = Mock()
    auto.mouse_to_blank = Mock()
    ns = battle_class_without_game_imports(ROOT / "tasks/battle/battle.py", auto)
    ns["TurnEgoAction"] = partial(actions.TurnEgoAction, pause=lambda _: None)
    ns["general_battle"] = partial(actions.general_battle, pause=lambda _: None)
    ns["ImageUtils"].get_bbox.return_value = (0, 0, 120, 40)
    retry = ModuleType("tasks.base.retry")
    retry.check_times = lambda *args, **kw: False
    with patch.dict(sys.modules, {"tasks.base.retry": retry}):
        ns["Battle"](is_tool=True).fight(rabbit_options=actions.BattleOptions(ego_enabled=True, ego_name="空洞(le trou)"),
                                         ego_attempt_state=actions.EgoAttemptState())
    assert [e[1] for e in auto.events if e[0] == "hold"] == [.8, 1.2, .8, 1.2]


class Merchant:
    def __init__(self, *, affordable=True, delayed=False, stuck=False):
        self.screenshot = Image.new("RGB", (2560, 1440), "#242424")
        self.events, self.phase = [], "stock"
        self.affordable, self.delayed, self.stuck = affordable, delayed, stuck
        self.frames = 0

    def take_screenshot(self, **kwargs):
        self.frames += 1
        assert self.frames < 100
        if self.phase == "payment" and not self.delayed:
            self.phase = "acquired"
        return self.screenshot

    def find_element(self, target, **kwargs):
        if target == COINS:
            return (1102, 274) if self.phase != "stuck" else None
        if target == PURCHASE:
            return (1500, 960) if self.phase in {"selected", "payment", "stuck"} and self.affordable else None
        if target == ACQUIRED:
            return (1200, 800) if self.phase == "acquired" else None
        return None

    def mouse_click(self, *point):
        self.events.append(("select", point))
        self.phase = "selected"

    def click_element(self, target, **kwargs):
        self.events.append(("asset", target))
        if target == PURCHASE:
            self.phase = "stuck" if self.stuck else "payment"
        if target == ACQUIRED:
            self.phase = "stock"
        return True

    def mouse_click_blank(self, **kwargs):
        self.events.append(("blank",))
        if not self.stuck:
            self.phase = "stock"


def specified_matcher():
    matcher = Mock(paths=("first.png", "second.png"))
    matcher.find_in_region.side_effect = lambda screenshot, region, excluded: next(
        ((path, (1200 + i * 300, 550)) for i, path in enumerate(matcher.paths) if path not in excluded), None)
    return matcher


def test_specified_purchase_order_one_payment_per_target_and_acquired_count():
    auto, attempted = Merchant(), set()
    result = buy_specified(auto, specified_matcher(), attempted, Mock(), pause=lambda _: None)
    assert result == PurchaseResult(2, True)
    assert attempted == {"first.png", "second.png"}
    assert [e for e in auto.events if e == ("asset", PURCHASE)] == [("asset", PURCHASE)] * 2
    assert [e for e in auto.events if e[0] == "select"] == [("select", (1200, 550)), ("select", (1500, 550))]
    before = auto.events[:]
    assert buy_specified(auto, specified_matcher(), attempted, Mock(), pause=lambda _: None).count == 0
    assert auto.events == before


@pytest.mark.parametrize("conditions", [dict(affordable=False), dict(delayed=True), dict(stuck=True)])
def test_unaffordable_or_unchanged_payment_does_not_repeat_or_claim_success(conditions):
    auto, attempted = Merchant(**conditions), set()
    matcher = specified_matcher()
    matcher.paths = ("first.png",)
    result = buy_specified(auto, matcher, attempted, Mock(), pause=lambda _: None)
    assert result.count == 0
    assert len([e for e in auto.events if e == ("asset", PURCHASE)]) <= 1
    assert auto.frames < 25
    if conditions.get("stuck"):
        assert not result.ready


def test_missing_reference_and_user_stop_do_not_turn_into_random_purchase():
    auto, matcher = Merchant(), specified_matcher()
    matcher.find_in_region.side_effect = FileNotFoundError("missing artwork")
    assert buy_specified(auto, matcher, set(), Mock(), pause=lambda _: None) == PurchaseResult()
    assert auto.events == []
    matcher.find_in_region.side_effect = actions.userStopError("stop")
    with pytest.raises(actions.userStopError):
        buy_specified(auto, matcher, set(), Mock(), pause=lambda _: None)


def test_previous_confirmation_modal_is_never_treated_as_stock():
    auto = Merchant()
    auto.phase = "acquired"
    matcher = specified_matcher()
    result = buy_specified(auto, matcher, set(), Mock(), pause=lambda _: None)
    assert not result.ready
    matcher.find_in_region.assert_not_called()
    assert auto.events == []


@pytest.mark.parametrize("height", [1080, 1440])
def test_real_imported_icon_is_found_in_stock_and_owned_copy_is_excluded(height):
    scale = height / 1440
    screen = Image.new("RGB", (round(height * 16 / 9), height), "#242424")
    icon = Image.open(NEEDLE_CAPTURE).convert("RGB")
    screen.paste(icon, (round(350 * scale), round(550 * scale)))
    stock_x, stock_y = round(1450 * scale), round(550 * scale)
    screen.paste(icon, (stock_x, stock_y))
    matcher = icons.ProtectedGiftMatcher([str(NEEDLE_CAPTURE)])
    region = merchant_region(screen.size, (1102 * scale, 274 * scale))
    found = matcher.find_in_region(screen, region)
    assert found and found[0] == str(NEEDLE_CAPTURE)
    assert abs(found[1][0] - (stock_x + icon.width / 2)) < 3
    assert abs(found[1][1] - (stock_y + icon.height / 2)) < 3
    assert matcher.find_in_region(screen, region, {str(NEEDLE_CAPTURE)}) is None


def test_disabled_or_do_not_buy_never_calls_specified_detector():
    for settings in ({}, {"do_not_buy": True, "specify_gift_images": True, "specified_gift_images": ["item.png"]}):
        shop, auto, ns = make_shop(**settings)
        ns["PurchaseResult"], ns["buy_specified"] = PurchaseResult, Mock()
        assert shop._buy_specified_gifts() == PurchaseResult()
        ns["buy_specified"].assert_not_called()
        auto.mouse_click.assert_not_called()


def test_specified_buyer_precedes_standard_categories_and_passes_off_to_them():
    shop, auto, ns = make_shop(specify_gift_images=True, specified_gift_images=["item.png"],
                               shopping_strategy=True, shopping_strategy_select=0, max_normal_refresh=0,
                               max_keyword_refresh=0)
    order = []
    shop._buy_specified_gifts = Mock(side_effect=lambda: (order.append("specified") or PurchaseResult()))
    shop._get_cost = lambda: 0
    auto.take_screenshot.return_value = Image.new("RGB", (2560, 1440))
    auto.click_element.side_effect = lambda target, **kw: (order.append("standard") or False)
    ns["must_purchase"] = ["mandatory.png"]
    shop.buy_gifts()
    assert order[:2] == ["specified", "standard"]




def test_actual_team_editor_layout_and_merged_gift_list_are_preserved():
    from PySide6.QtWidgets import QApplication, QLabel

    from app.team_setting_card import TeamSettingCard
    from module.config import cfg

    application = QApplication.instance() or QApplication([])
    with patch.object(cfg, "set_value") as save:
        editor = TeamSettingCard(1)
        try:
            editor.team_setting = schema.TeamSetting(protect_gift_images=True, protected_gift_images=[str(NEEDLE_CAPTURE)],
                                                      specify_gift_images=True, specified_gift_images=[str(NEEDLE_CAPTURE)],
                                                      stop_fusion_on_failure=True,
                                                      route_weights_enabled=True)
            editor.read_settings()
            assert editor.theme_observation_layout.card.titleLabel.text() == "观测主题卡包"
            assert editor.gift_lock_layout.card.titleLabel.text() == "饰品锁定"
            assert not hasattr(editor, "gift_protection_layout")
            assert not hasattr(editor, "gift_priority_layout")
            assert editor.event_options_layout is not editor.team_advanced_layout
            assert any(label.text() == "仅支持单通，名称需要与语言对应"
                       for label in editor.ego_release_module.findChildren(QLabel))
            custom = editor.customize_settings_module
            assert custom.second_line.indexOf(custom.stop_fusion_on_failure) > custom.second_line.indexOf(custom.only_system_fuse)
            assert not editor.findChildren(type(editor.gift_lock_module.checks["gift_lock_enabled"]), "auto_corrosion_direct")
            assert editor.gift_lock_module.protected_paths == [str(NEEDLE_CAPTURE)]
            editor.gift_lock_module._remove_protection_image(str(NEEDLE_CAPTURE))
            custom.mirror_floor_limit.combo_box.set_options(2)
            editor.save_team_setting()
            saved = save.call_args.args[1]
            assert saved.gift_lock_enabled and saved.gift_lock_images == []
            assert saved.mirror_floor_limit == 3
            assert saved.stop_fusion_on_failure and saved.route_weights_enabled
        finally:
            editor.disconnect_mediator()
            editor.close()
            editor.deleteLater()
            application.processEvents()

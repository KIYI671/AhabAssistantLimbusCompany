"""Original settlement and shop priority regressions; no game I/O."""
from upstream_reference import REFERENCE, original_source
import ast
import subprocess
from types import ModuleType
from unittest.mock import Mock, patch
import pytest
from test_optional_battle import ROOT, FakeAuto, battle_class_without_game_imports
from test_rabbit_options import schema
from test_options10_flows import make_shop
from tasks.battle.speed_hold import UnifiedSpeedHold





def test_original_center_click_and_result_confirmation_blocks_restored():
    path = "tasks/battle/battle.py"
    original = original_source(path)
    current = (ROOT/path).read_text(encoding="utf-8")
    def blocks(source):
        nodes = ast.walk(ast.parse(source))
        return {ast.unparse(n.test): ast.dump(n) for n in nodes if isinstance(n,ast.If)}
    before, after = blocks(original), blocks(current)
    assert before["not self.is_tool"] == after["not self.is_tool"]
    key = next(k for k in before if "battle_finish_confirm_assets.png" in k and "battle_statistics_assets.png" in k)
    assert before[key] == after[key]
    assert "VictoryClicker" not in current and "victory_release" not in current
    assert "victory_click" not in schema.ConfigModel.model_fields

@pytest.mark.parametrize("speed", [False, True])
def test_original_center_click_still_runs_with_acceleration_enabled_but_no_signal(speed):
    auto = FakeAuto(gears=False)
    phase = ["result"]
    auto.get_restore_time = lambda: None
    auto.mouse_to_blank = Mock()
    auto._run_ocr_for_text = Mock(return_value={})
    auto.find_element = lambda path, **kwargs: (10,10) if phase[0] == "reward" and path.endswith("select_encounter_reward_card_assets.png") else None
    auto.click_element = Mock(return_value=False)
    def click(x,y,**kwargs):
        auto.events.append(("click",x,y))
        phase[0] = "reward"
    auto.mouse_click = click
    namespace = battle_class_without_game_imports(ROOT/"tasks/battle/battle.py", auto)
    namespace["UnifiedSpeedHold"] = UnifiedSpeedHold
    retry = ModuleType("tasks.base.retry")
    retry.check_times = lambda *args, **kwargs: False
    with patch.dict("sys.modules", {"tasks.base.retry": retry}):
        namespace["Battle"](is_tool=False).fight(speed_hold=speed)
    assert len([e for e in auto.events if e[0] == "click"]) == 1
    assert not auto.held

def test_do_not_buy_overrides_locked_purchase_without_disabling_protection():
    shop, auto, _ = make_shop(do_not_buy=True, gift_lock_enabled=True, gift_lock_images=["needle.png"])
    assert shop.protect_gift_images and shop.protected_gift_images == ("needle.png",)
    shop._specified_matcher = Mock(side_effect=AssertionError("must not attempt purchase"))
    from tasks.mirror.priority_purchase import PurchaseResult
    shop._buy_specified_gifts.__globals__["PurchaseResult"] = PurchaseResult
    result = shop._buy_specified_gifts()
    assert result.count == 0
    auto.mouse_click.assert_not_called()




@pytest.mark.parametrize("speed,from_combat", [(False, False), (True, False), (True, True)])
def test_theme_pack_screen_leaves_battle_before_center_click_or_hold(speed, from_combat):
    auto = FakeAuto(gears=False)
    auto.get_restore_time = lambda: None
    phases = ["combat", "theme"] if from_combat else ["theme"]
    frame = [-1]

    def capture(**kwargs):
        frame[0] += 1
        assert frame[0] < len(phases), "Battle retained control on the theme-pack screen"
        return auto.screenshot

    def find(path, **kwargs):
        if phases[frame[0]] == "theme" and path.endswith("feature_theme_pack_assets.png"):
            return (2420, 235)
        if phases[frame[0]] == "combat" and path == "battle/pause_assets.png":
            return (2350, 100)
        return None

    auto.take_screenshot = capture
    auto.find_element = find
    auto.click_element = Mock(side_effect=AssertionError("No battle clicks on the theme-pack screen"))
    auto.mouse_click = Mock(side_effect=AssertionError("No center click on the theme-pack screen"))
    auto._run_ocr_for_text = Mock(side_effect=AssertionError("Reuse the original page marker; no extra OCR"))
    namespace = battle_class_without_game_imports(ROOT/"tasks/battle/battle.py", auto)
    namespace["UnifiedSpeedHold"] = UnifiedSpeedHold
    retry = ModuleType("tasks.base.retry")
    retry.check_times = lambda *args, **kwargs: False
    with patch.dict("sys.modules", {"tasks.base.retry": retry}):
        assert namespace["Battle"](is_tool=False).fight(speed_hold=speed) is False
    assert not auto.held
    assert len([event for event in auto.events if event[0] == "begin"]) == int(from_combat)
    auto.mouse_click.assert_not_called()
    auto.click_element.assert_not_called()
    auto._run_ocr_for_text.assert_not_called()

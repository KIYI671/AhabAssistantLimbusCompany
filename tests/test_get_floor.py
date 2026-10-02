"""隔离图形环境，验证颜色计数和中途接续的楼层状态。"""

import ast
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, call

import cv2
import numpy as np
import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def _load_function(path, name, **namespace):
    tree = ast.parse((ROOT / path).read_text(encoding="utf-8"))
    node = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == name)
    node.decorator_list = []
    exec(compile(ast.Module(body=[node], type_ignores=[]), path, "exec"), namespace)
    return namespace[name]


@pytest.mark.parametrize(
    "page_feature", ["event/skip_assets.png", "mirror/road_in_mir/select_encounter_reward_card_assets.png"]
)
def test_resuming_mirror_on_event_or_reward_page_returns_to_main_loop(page_feature):
    auto = Mock()
    auto.take_screenshot.return_value = True
    auto.find_element.side_effect = lambda name, *args, **kwargs: name == page_feature
    auto.click_element.return_value = False
    back_init_menu = Mock()
    road_to_mir = _load_function(
        "tasks/mirror/mirror.py",
        "road_to_mir",
        auto=auto,
        retry=lambda: True,
        sleep=lambda seconds: None,
        ImageUtils=SimpleNamespace(get_bbox=lambda image: (0, 0, 100, 100), load_image=lambda name: None),
        log=Mock(),
        back_init_menu=back_init_menu,
    )
    road_to_mir(SimpleNamespace())
    auto.take_screenshot.assert_called_once()
    back_init_menu.assert_not_called()


def test_color_match_distinguishes_empty_result_from_error():
    match = _load_function("utils/image_utils.py", "match_color_regions", np=np, cv2=cv2, log=Mock())
    frame = np.zeros((24, 24, 3), dtype=np.uint8)
    assert match(frame, lambda roi: np.zeros(roi.shape[:2], dtype=np.uint8)) == []
    assert match(frame, lambda roi: np.zeros((1, 1), dtype=np.uint8)) is None


def test_adb_screenshot_returns_rgb_for_floor_color_matching():
    rgb = np.random.default_rng(0).integers(0, 256, (24, 24, 3), dtype=np.uint8)
    rgb[:8, :8] = (230, 40, 20)
    encoded = cv2.imencode(".png", cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))[1].tobytes()
    connection = SimpleNamespace(
        simulator_device=SimpleNamespace(shell=Mock(return_value=encoded)),
        _call_with_reconnect=lambda action, fn: fn(),
    )
    screenshot = _load_function(
        "module/automation/input_handlers/simulator/simulator_control.py", "screenshot", np=np, cv2=cv2
    )
    np.testing.assert_array_equal(screenshot(connection), rgb)


@pytest.mark.parametrize("loading_frames", [3, 14])
def test_event_waits_for_map_after_options_are_used_up(loading_frames):
    state = SimpleNamespace(frame=0, now=0, page="choices")

    def screenshot():
        state.frame += 1
        state.now += 1
        state.page = "choices" if state.frame <= 15 else "loading" if state.frame <= 15 + loading_frames else "map"
        return True

    def find(name, *args, **kwargs):
        if name.endswith("legend_assets.png"):
            return state.page == "map"
        if name.endswith("choices_assets.png"):
            return state.page == "choices"
        if name.endswith("select_first_option_assets.png") and state.page == "choices":
            return [(10, 10)] if kwargs.get("find_type") == "image_with_multiple_targets" else True
        return False

    auto = Mock()
    auto.take_screenshot.side_effect = screenshot
    auto.find_element.side_effect = find
    auto.click_element.side_effect = lambda name, **kwargs: (
        name.endswith("select_first_option_assets.png")
        and state.page == "choices"
        or name.endswith("proceed_assets.png")
        and state.frame == 15
    )
    auto.find_language_text.return_value = False
    auto.find_text_element.return_value = False
    back_init_menu = Mock(side_effect=RuntimeError("Loading must not return to Home"))
    handle = _load_function(
        "tasks/mirror/mirror.py",
        "event_handling",
        auto=auto,
        retry=lambda: True,
        time=SimpleNamespace(time=lambda: state.now),
        log=Mock(),
        back_init_menu=back_init_menu,
        ImageUtils=SimpleNamespace(get_bbox=lambda image: (0, 0, 100, 100), load_image=lambda name: None),
        event_handling=SimpleNamespace(decision_event_handling=Mock()),
    )
    mirror = SimpleNamespace(event_total_time=0, event_times=0)
    handle(mirror)
    back_init_menu.assert_not_called()
    assert mirror.event_times == 1 and mirror.event_total_time == 16 + loading_frames


@pytest.mark.parametrize("regions", [None, [], [(10, 10, 300)]])
def test_automation_propagates_result_and_restores_grayscale(regions):
    find = _load_function(
        "module/automation/automation.py",
        "find_regions_by_color",
        np=np,
        log=Mock(),
        ImageUtils=SimpleNamespace(match_color_regions=Mock(return_value=regions)),
    )
    auto = SimpleNamespace(screenshot=Image.new("RGB", (24, 24)), take_screenshot=Mock(return_value=True))
    assert find(auto, None, lambda roi: None) == regions
    assert auto.screenshot.mode == "L"


@pytest.mark.parametrize(
    "previous_floor, regions, expected, mismatch",
    [
        (4, None, 0, False),
        (4, [], 1, True),
        (4, [(10, 10, 300)], 2, True),
        (0, [], 1, False),
        (1, [(10, 10, 300)], 2, False),
        (0, [(10, 10, 300)] * 3, 4, True),
    ],
)
def test_floor_count_checks_previous_floor_and_keeps_detected_result(previous_floor, regions, expected, mismatch):
    auto = Mock()
    auto.find_regions_by_color.return_value = regions
    log = Mock()
    get_floor = _load_function(
        "tasks/mirror/get_floor.py",
        "get_floor",
        auto=auto,
        log=log,
        sleep=lambda seconds: None,
        FLOOR_BAND_ROI=(760, 495, 1860, 590),
        FLOOR_CLEAR_MIN_AREA=300,
        clear_badge_mask=lambda roi: None,
    )
    assert get_floor(previous_floor=previous_floor) == expected
    expected_info = []
    if mismatch:
        expected_info.append(
            call(
                f"楼层识别异常：上一层为 {previous_floor}，预计当前为 {previous_floor + 1}，"
                f"实际识别为 {expected}，使用识别结果继续"
            )
        )
    if regions is not None:
        expected_info.append(call(f"楼层识别结果：当前为第{expected}层"))
    assert log.info.call_args_list == expected_info
    if regions is None:
        log.error.assert_called_once_with("楼层识别异常：未能确认当前楼层，标记为 0（未知）")
    else:
        log.error.assert_not_called()


@pytest.mark.parametrize("setting_found, panel_found", [(False, False), (True, False)])
def test_floor_is_unknown_and_reports_error_when_panel_is_unavailable(setting_found, panel_found):
    auto = Mock()
    auto.find_element.side_effect = [setting_found, panel_found]
    log = Mock()
    get_floor = _load_function(
        "tasks/mirror/get_floor.py",
        "get_floor",
        auto=auto,
        log=log,
        sleep=lambda seconds: None,
        FLOOR_BAND_ROI=(760, 495, 1860, 590),
        FLOOR_CLEAR_MIN_AREA=300,
        clear_badge_mask=lambda roi: None,
    )
    assert get_floor(previous_floor=4) == 0
    log.error.assert_called_once()
    auto.find_regions_by_color.assert_not_called()
    assert auto.mouse_click_blank.call_count == int(setting_found)


@pytest.mark.parametrize("detected_floor", [0, 2])
def test_theme_pack_checks_floor_before_map_and_continues_when_unknown(detected_floor):
    class Halt(Exception):
        pass

    auto = SimpleNamespace(
        click_element=Mock(return_value=False),
        find_element=Mock(
            side_effect=lambda name, *args, **kwargs: name.endswith(
                ("feature_theme_pack_assets.png", "legend_assets.png")
            )
        ),
        take_screenshot=Mock(side_effect=[True, Halt()]),
    )
    get_floor = Mock(return_value=detected_floor)
    select_theme_pack = Mock()
    mirror = SimpleNamespace(
        floor=0,
        LOOP_COUNT=250,
        mirror_map=Mock(),
        _enter_hard_mode_if_needed=Mock(),
        hard_mode=False,
        team_order=1,
        use_custom_theme_pack_weight=False,
        re_formation_each_floor=False,
        floor_times=[None] * 5,
        current_floor_start_time=None,
        current_floor_time_complete=False,
        _log_floor_time=Mock(),
    )
    run = _load_function(
        "tasks/mirror/mirror.py",
        "run",
        auto=auto,
        cfg=SimpleNamespace(floor_3_exit=False),
        retry=lambda: True,
        get_floor=get_floor,
        switch_theme_pack_difficulty=Mock(),
        select_theme_pack=select_theme_pack,
        to_log_with_time=Mock(),
        time=SimpleNamespace(time=lambda: 1),
        sleep=lambda seconds: None,
    )
    with pytest.raises(Halt):
        run(mirror)
    get_floor.assert_called_once_with(0, "mirror/theme_pack/theme_pack_setting_assets.png")
    mirror.mirror_map.refresh_floor.assert_called_once_with(detected_floor, reset=True)
    select_theme_pack.assert_called_once_with(False, detected_floor, 1, False)
    assert mirror.floor == detected_floor
    assert mirror.current_floor_start_time == 1
    assert mirror.current_floor_time_complete is True
    if detected_floor == 0:
        assert mirror.floor_times == [None] * 5
    assert not any(call.args[0].endswith("legend_assets.png") for call in auto.find_element.call_args_list)


@pytest.mark.parametrize(
    "initial_floor, detected_floor, expected_checks, exits",
    [(0, 4, 1, True), (0, 0, 1, False), (2, 4, 0, False)],
)
def test_map_checks_unknown_floor_before_searching(initial_floor, detected_floor, expected_checks, exits):
    class Halt(Exception):
        pass

    mirror = SimpleNamespace(
        floor=initial_floor,
        LOOP_COUNT=250,
        mirror_map=Mock(),
        current_floor_start_time=None,
        current_floor_time_complete=False,
    )
    get_floor = Mock(return_value=detected_floor)
    mirror.search_road = Mock(side_effect=Halt)
    mirror._time_call = lambda fn: fn()
    forfeit = Mock(side_effect=Halt)

    def click(name, *args, **kwargs):
        if name.endswith("towindow&forfeit_confirm_assets.png"):
            return forfeit()
        return False

    auto = SimpleNamespace(
        click_element=click,
        find_element=lambda name, *args, **kwargs: name.endswith("legend_assets.png"),
        take_screenshot=lambda: True,
        mouse_to_blank=lambda: None,
    )
    run = _load_function(
        "tasks/mirror/mirror.py",
        "run",
        auto=auto,
        cfg=SimpleNamespace(floor_3_exit=True),
        retry=lambda: True,
        get_floor=get_floor,
        time=SimpleNamespace(time=lambda: 1),
        sleep=lambda seconds: None,
    )
    with pytest.raises(Halt):
        run(mirror)
    assert get_floor.call_count == expected_checks
    if expected_checks:
        mirror.mirror_map.refresh_floor.assert_called_once_with(detected_floor)
    else:
        mirror.mirror_map.refresh_floor.assert_not_called()
    assert forfeit.call_count == int(exits)
    assert mirror.search_road.call_count == int(not exits)


def test_map_keeps_searching_when_floor_recognition_repeatedly_fails():
    class Halt(Exception):
        pass

    mirror = SimpleNamespace(
        floor=0,
        LOOP_COUNT=250,
        mirror_map=Mock(),
        find_road_total_time=0,
        search_road=Mock(side_effect=[True, True, Halt()]),
        current_floor_start_time=None,
        current_floor_time_complete=False,
    )
    mirror._time_call = lambda fn: (fn(), 0)
    get_floor = Mock(return_value=0)
    auto = SimpleNamespace(
        click_element=Mock(return_value=False),
        find_element=lambda name, *args, **kwargs: name.endswith("legend_assets.png"),
        take_screenshot=lambda: True,
        mouse_to_blank=lambda: None,
    )
    run = _load_function(
        "tasks/mirror/mirror.py",
        "run",
        auto=auto,
        cfg=SimpleNamespace(floor_3_exit=True),
        retry=lambda: True,
        get_floor=get_floor,
        time=SimpleNamespace(time=lambda: 1),
        sleep=lambda seconds: None,
    )
    with pytest.raises(Halt):
        run(mirror)
    assert get_floor.call_count == mirror.search_road.call_count == 3
    assert mirror.floor == 0
    assert mirror.current_floor_start_time == 1
    assert mirror.current_floor_time_complete is False


@pytest.mark.parametrize("new_floor, reset, clears_route", [(0, False, False), (0, True, True), (2, False, True)])
def test_map_resets_route_for_new_floor_but_preserves_unknown_floor_route(new_floor, reset, clears_route):
    refresh_floor = _load_function("tasks/mirror/search_road.py", "refresh_floor", log=Mock())
    mirror_map = SimpleNamespace(floor=0, floor_map=["M", "U"])
    refresh_floor(mirror_map, new_floor, reset=reset)
    assert mirror_map.floor == new_floor
    assert mirror_map.floor_map == ([] if clears_route else ["M", "U"])


def test_unknown_floor_map_can_build_and_follow_route():
    identify_route = Mock(return_value=(["M", "U"], ["battle", "event"]))
    get_next_step = _load_function(
        "tasks/mirror/search_road.py", "get_next_step", search_road_from_road_map=identify_route
    )
    mirror_map = SimpleNamespace(floor=0, floor_map=[], map={}, hard_mode=False)
    assert get_next_step(mirror_map) == "M"
    assert get_next_step(mirror_map) == "U"
    identify_route.assert_called_once_with(hard_mode=False)


@pytest.mark.parametrize("floor", [0, 5])
def test_unknown_floor_shop_does_not_use_fifth_floor_ignore_setting(floor):
    class Halt(Exception):
        pass

    auto = Mock()
    auto.take_screenshot.side_effect = Halt()
    log = Mock()
    in_shop = _load_function("tasks/mirror/in_shop.py", "in_shop", auto=auto, log=log)
    shop = SimpleNamespace(ignore_shop=[False] * 4 + [True], RestartGame=RuntimeError)
    with pytest.raises(Halt):
        in_shop(shop, floor)
    auto.take_screenshot.assert_called_once()
    if floor == 0:
        log.info.assert_not_called()
    else:
        log.info.assert_called_once_with("第5楼层商店被忽略")


def test_unknown_floor_selects_theme_pack_by_normal_weights():
    auto = Mock()
    auto.find_element.side_effect = lambda name, **kwargs: (
        [(1000, 300), (1300, 300)] if name.endswith("theme_pack_features.png") else False
    )
    auto.find_language_text.return_value = SimpleNamespace(value=100, text="sample")
    select_theme_pack = _load_function(
        "tasks/mirror/select_theme_pack.py",
        "select_theme_pack",
        auto=auto,
        cfg=SimpleNamespace(set_win_size=1080, select_event_pack=True, skip_event_pack=True),
        theme_list=SimpleNamespace(
            get_effective_theme_pack_list=Mock(return_value={"sample": 100}), preferred_thresholds=0
        ),
        path_manager=SimpleNamespace(current_language="zh_cn"),
        TextMatchResult=SimpleNamespace,
        log=Mock(),
        sleep=lambda seconds: None,
    )
    select_theme_pack(floor=0)
    assert auto.find_language_text.call_count == 2
    auto.mouse_drag_down.assert_called_once_with(1000, 300)


@pytest.mark.parametrize("floor, complete", [(0, True), (2, True), (0, False), (2, False)])
def test_floor_timing_does_not_depend_on_recognition(floor, complete):
    timings = Mock()
    log_floor_time = _load_function("tasks/mirror/mirror.py", "_log_floor_time", to_log_with_time=timings)
    mirror = SimpleNamespace(current_floor_start_time=100, current_floor_time_complete=complete)
    log_floor_time(mirror, 160, floor)
    label = f"第{floor}层" if floor else "楼层未知"
    if not complete:
        label += "，计时不完整"
    timings.assert_called_once_with(label, 60)


def test_floor_timing_does_not_invent_start_time():
    timings = Mock()
    log_floor_time = _load_function("tasks/mirror/mirror.py", "_log_floor_time", to_log_with_time=timings)
    log_floor_time(SimpleNamespace(current_floor_start_time=None), 160, 0)
    timings.assert_not_called()


@pytest.mark.parametrize(
    "start_page, detected_floor",
    [("card", 0), ("card", 2), ("map", 0), ("map", 2), ("reward", 0), ("legacy_reward", 0)],
)
def test_run_times_unknown_floor_and_recovers_complete_timing_on_next_card(start_page, detected_floor):
    state = SimpleNamespace(page=start_page, now=100, cards=0)
    timings = Mock()
    log_floor_time = _load_function("tasks/mirror/mirror.py", "_log_floor_time", to_log_with_time=timings)
    mirror = SimpleNamespace(
        floor=0,
        floor_times=[None] * 5,
        current_floor_start_time=None,
        current_floor_time_complete=False,
        LOOP_COUNT=250,
        mirror_map=Mock(),
        _enter_hard_mode_if_needed=Mock(),
        hard_mode=False,
        team_order=1,
        use_custom_theme_pack_weight=False,
        re_formation_each_floor=False,
        bequest_from_the_previous_game=start_page == "legacy_reward",
        battle_total_time=0,
        event_times=0,
        event_total_time=0,
        shop_total_time=0,
        find_road_total_time=0,
        system="test",
    )
    mirror._log_floor_time = lambda end, floor: log_floor_time(mirror, end, floor)

    def find(name, *args, **kwargs):
        return (
            (name.endswith("feature_theme_pack_assets.png") and state.page == "card")
            or (name.endswith("legend_assets.png") and state.page == "map")
            or (name.endswith("battle_statistics_assets.png") and state.page == "reward")
            or (name.endswith("complete_mirror_100%_assets.png") and state.page in {"reward", "home", "legacy_reward"})
            or (name.endswith("home/drive_assets.png") and state.page == "home")
            or (name.endswith("claim_rewards_assets.png") and state.page == "legacy_reward")
        )

    def click(name, *args, **kwargs):
        if name.endswith("claim_rewards_assets.png") and state.page == "reward":
            state.page = "home"
            state.now = 190
            return True
        return False

    def select(*args):
        state.cards += 1
        if start_page == "card" and state.cards == 1:
            state.now = 110
        else:
            state.now = 160
            state.page = "reward"

    def search():
        state.page = "card"
        state.now = 160
        return True

    mirror.search_road = search

    def claim_legacy_reward():
        state.page = "home"
        state.now = 190

    mirror.get_reward_in_road = Mock(side_effect=claim_legacy_reward)
    mirror._time_call = lambda fn: (fn(), 0)
    auto = Mock()
    auto.take_screenshot.return_value = True
    auto.find_element.side_effect = find
    auto.click_element.side_effect = click
    get_floor = Mock(side_effect=[detected_floor, 0])
    run = _load_function(
        "tasks/mirror/mirror.py",
        "run",
        auto=auto,
        cfg=SimpleNamespace(floor_3_exit=False),
        log=Mock(),
        retry=lambda: True,
        get_floor=get_floor,
        switch_theme_pack_difficulty=Mock(),
        select_theme_pack=select,
        to_log_with_time=timings,
        time=SimpleNamespace(time=lambda: state.now),
        sleep=lambda seconds: None,
    )
    assert run(mirror) is True
    floor_logs = [entry for entry in timings.call_args_list if entry.args[0].startswith(("第", "楼层未知"))]
    if start_page in {"reward", "legacy_reward"}:
        assert floor_logs == [call("楼层未知，计时不完整", 90)]
        get_floor.assert_not_called()
    else:
        label = f"第{detected_floor}层" if detected_floor else "楼层未知"
        duration = 50 if start_page == "card" else 60
        if start_page == "map":
            label += "，计时不完整"
        assert floor_logs == [call(label, duration), call("楼层未知", 30)]
        assert mirror.current_floor_time_complete is True
    assert mirror.floor == 0
    if detected_floor == 0 or start_page != "card":
        assert mirror.floor_times == [None] * 5


def test_restart_resets_floor_timing():
    auto = Mock()
    auto.take_screenshot.return_value = True
    auto.click_element.return_value = True
    restart = _load_function(
        "tasks/mirror/mirror.py", "re_start", auto=auto, log=Mock(), time=SimpleNamespace(time=lambda: 200)
    )
    mirror = SimpleNamespace(
        start_time=50, floor=3, floor_times=[100] * 5, current_floor_start_time=100, current_floor_time_complete=True
    )
    restart(mirror)
    assert mirror.floor == 0
    assert mirror.floor_times == [None] * 5
    assert mirror.current_floor_start_time is None
    assert mirror.current_floor_time_complete is False


@pytest.mark.parametrize("hard, first_card_unknown", [(False, False), (True, False), (False, True), (True, True)])
@pytest.mark.parametrize("from_home", [False, True])
def test_whole_run_history_requires_all_five_card_starts(hard, first_card_unknown, from_home):
    state = SimpleNamespace(page="home" if from_home else "card", floor=1, now=100)
    timings = Mock()
    team = SimpleNamespace(
        total_mirror_time_normal=[100.0] * 3,
        mirror_normal_count=3,
        total_mirror_time_hard=[200.0] * 3,
        mirror_hard_count=2,
    )
    mirror = SimpleNamespace(
        floor=0,
        floor_times=[None] * 5,
        current_floor_start_time=None,
        current_floor_time_complete=False,
        LOOP_COUNT=250,
        mirror_map=Mock(),
        _enter_hard_mode_if_needed=Mock(),
        hard_mode=hard,
        hard_reward_eligible=hard,
        team_order=1,
        use_custom_theme_pack_weight=False,
        re_formation_each_floor=False,
        bequest_from_the_previous_game=False,
        battle_total_time=0,
        event_times=0,
        event_total_time=0,
        shop_total_time=0,
        find_road_total_time=0,
        system="test",
    )
    log_floor_time = _load_function("tasks/mirror/mirror.py", "_log_floor_time", to_log_with_time=timings)
    mirror._log_floor_time = lambda end, floor: log_floor_time(mirror, end, floor)

    def find(name, *args, **kwargs):
        return (
            name.endswith("feature_theme_pack_assets.png")
            and state.page == "card"
            or name.endswith("legend_assets.png")
            and state.page == "map"
            or name.endswith("battle_statistics_assets.png")
            and state.page == "reward"
            or name.endswith("complete_mirror_100%_assets.png")
            and state.page in {"reward", "home"}
            or name.endswith(("teams/identify_assets.png", "select_team_stars_assets.png"))
            and state.page == "entry_team"
            or name.endswith(("home/drive_assets.png", "home/window_assets.png"))
            and state.page == "home"
        )

    def click(name, *args, **kwargs):
        if name.endswith("claim_rewards_assets.png") and state.page == "reward":
            state.page = "home"
            state.now += 30
            return True
        return False

    def select(*args):
        state.now += 10
        state.page = "map"

    def search():
        state.now += 50
        if state.floor == 5:
            state.page = "reward"
        else:
            state.floor += 1
            state.page = "card"
        return True

    def detect(*args):
        # 卡包页识别失败后，地图页恢复楼层，但不能补写缺失的卡包开始记录。
        if first_card_unknown and state.floor == 1 and state.page == "card":
            return 0
        return state.floor

    def enter():
        state.now += 25
        state.page = "entry_team"
        return True

    def select_team():
        state.page = "card"

    mirror.select_mirror_team = select_team
    mirror.road_to_mir = enter
    mirror.search_road = search
    mirror._time_call = lambda fn: (fn(), 0)
    auto = Mock()
    auto.take_screenshot.return_value = True
    auto.find_element.side_effect = find
    auto.click_element.side_effect = click
    auto.find_text_element.return_value = False
    auto.find_language_text.return_value = False
    run = _load_function(
        "tasks/mirror/mirror.py",
        "run",
        auto=auto,
        cfg=SimpleNamespace(floor_3_exit=False, config=SimpleNamespace(teams={"1": team})),
        log=Mock(),
        retry=lambda: True,
        get_floor=detect,
        switch_theme_pack_difficulty=Mock(),
        select_theme_pack=select,
        to_log_with_time=timings,
        make_enkephalin_module=Mock(),
        battle=SimpleNamespace(fail_times=0, identify_keyword_turn=False),
        ImageUtils=SimpleNamespace(get_bbox=lambda image: (0, 0, 100, 100), load_image=lambda name: None),
        time=SimpleNamespace(time=lambda: state.now),
        sleep=lambda seconds: None,
    )
    assert run(mirror) is True
    assert [c.args[1] for c in timings.call_args_list if c.args[0].startswith(("第", "楼层未知"))] == [60] * 4 + [80]
    timings.assert_any_call("此次镜牢使用test体系队伍", 330 + (25 if from_home else 0))
    if first_card_unknown:
        assert mirror.floor_times[0] is None
        assert (team.mirror_normal_count, team.mirror_hard_count) == (3, 2)
        assert team.total_mirror_time_normal == [100.0] * 3
        assert team.total_mirror_time_hard == [200.0] * 3
    else:
        assert all(start is not None for start in mirror.floor_times)
        assert (team.mirror_normal_count, team.mirror_hard_count) == ((3, 3) if hard else (4, 2))
        total = 330 + (25 if from_home else 0)
        expected = (200 * 2 + total) / 3 if hard else (100 * 3 + total) / 4
        assert (team.total_mirror_time_hard if hard else team.total_mirror_time_normal) == [expected] * 3

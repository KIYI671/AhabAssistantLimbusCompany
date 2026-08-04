import importlib.util
import sys
import types
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]


def _module(name, **attributes):
    module = types.ModuleType(name)
    module.__dict__.update(attributes)
    return module


def _load_team_formation_module(monkeypatch, cfg):
    stubs = {
        "module.automation": _module("module.automation", auto=object()),
        "module.config": _module("module.config", cfg=cfg),
        "module.decorator.decorator": _module(
            "module.decorator.decorator",
            begin_and_finish_time_log=lambda **_kwargs: lambda func: func,
        ),
        "module.logger": _module(
            "module.logger", log=types.SimpleNamespace(info=lambda *_args: None)
        ),
    }
    for name, module in stubs.items():
        monkeypatch.setitem(sys.modules, name, module)

    spec = importlib.util.spec_from_file_location(
        "tasks.teams.team_formation_under_test",
        REPO_ROOT / "tasks/teams/team_formation.py",
    )
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, module)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    (
        "simulator",
        "background_click",
        "win_input_type",
        "use_post_message",
        "expected",
    ),
    [
        (True, True, "background", True, 375),
        (False, True, "background", True, 400),
        (False, True, "background", False, 400),
        (False, False, "foreground", True, 400),
        (False, True, "window_move", True, 400),
    ],
)
def test_ordered_team_page_distance_is_scoped_to_platform(
    monkeypatch,
    simulator,
    background_click,
    win_input_type,
    use_post_message,
    expected,
):
    cfg = types.SimpleNamespace(
        simulator=simulator,
        background_click=background_click,
        win_input_type=win_input_type,
        config=types.SimpleNamespace(use_post_message=use_post_message),
    )
    module = _load_team_formation_module(monkeypatch, cfg)

    assert module._ordered_team_page_swipe_distance() == expected


def test_team_list_reset_swipe_endpoint_stays_inside_client(monkeypatch):
    cfg = types.SimpleNamespace(simulator=False)
    module = _load_team_formation_module(monkeypatch, cfg)

    distance = module._team_list_reset_swipe_distance(539, 1080, 0.75)

    assert distance == 496
    assert 539 + distance == 1035


@pytest.mark.parametrize("team", [1, 6, 11, 16, 19, 20])
def test_windows_ordered_selection_uses_one_page_gesture_and_selects_requested_row(
    monkeypatch, team
):
    """Replay the captured Windows battle-selection list geometry."""

    class CapturedWindowsTeamList:
        row_spacing = 54.24
        initial_first_row_y = 467.68

        def __init__(self, requested_team):
            self.expected_page_count = (requested_team - 1) // 5
            self.positive_swipes = 0
            self.negative_swipes = 0
            self.rows_scrolled = 0
            self.page_distances = []
            self.selected_team = None

        def take_screenshot(self):
            return object()

        def find_element(self, path, **_kwargs):
            if path == "teams/identify_assets.png":
                return (1800, 266)
            return None

        def mouse_swipe_for_scroll(self, _x, _y, *, dy, **_kwargs):
            if dy > 0:
                self.positive_swipes += 1
            else:
                self.negative_swipes += 1
                design_distance = abs(dy) / 0.75
                self.page_distances.append(design_distance)
                rows = 5 if design_distance >= 390 else 4
                self.rows_scrolled = min(self.rows_scrolled + rows, 14)

        def mouse_click(self, _x, y, *_args, **_kwargs):
            if (
                self.positive_swipes == 3
                and self.negative_swipes == self.expected_page_count
            ):
                first_row_y = self.initial_first_row_y - (
                    self.rows_scrolled * self.row_spacing
                )
                self.selected_team = round((y - first_row_y) / self.row_spacing) + 1

    cfg = types.SimpleNamespace(
        simulator=False,
        set_win_size=1080,
        select_team_by_order=True,
    )
    module = _load_team_formation_module(monkeypatch, cfg)
    team_list = CapturedWindowsTeamList(team)
    monkeypatch.setattr(module, "auto", team_list)
    monkeypatch.setattr(module, "sleep", lambda _duration: None)

    assert module.select_battle_team(team) is True
    assert team_list.selected_team == team
    assert all(distance == 400 for distance in team_list.page_distances)

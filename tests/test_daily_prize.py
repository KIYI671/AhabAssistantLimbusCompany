from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock, call

import pytest


@pytest.fixture
def prize_context(monkeypatch):
    auto = SimpleNamespace(
        # Limit frames so an unbounded fallback fails instead of hanging the test.
        take_screenshot=Mock(side_effect=[object() for _ in range(20)]),
        find_element=Mock(return_value=None),
        click_element=Mock(return_value=False),
        find_text_element=Mock(return_value=False),
        mouse_click=Mock(),
        mouse_to_blank=Mock(),
    )
    log = Mock()
    retry = Mock()
    # Run the real reward workflow without initializing desktop input or user config.
    automation = ModuleType("module.automation")
    automation.auto = auto
    config = ModuleType("module.config")
    config.cfg = SimpleNamespace(set_win_size=720)
    retry_module = ModuleType("tasks.base.retry")
    retry_module.retry = retry
    images = ModuleType("utils.image_utils")
    images.ImageUtils = SimpleNamespace(load_image=Mock(), get_bbox=Mock(return_value=(0, 0, 100, 100)))
    for name, dependency in {
        "module.automation": automation,
        "module.config": config,
        "tasks.base.retry": retry_module,
        "utils.image_utils": images,
    }.items():
        monkeypatch.setitem(sys.modules, name, dependency)
    source = Path(__file__).resolve().parents[1] / "tasks" / "daily" / "get_prize.py"
    spec = importlib.util.spec_from_file_location("isolated_daily_prize", source)
    get_prize = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(get_prize)
    monkeypatch.setattr(get_prize, "log", log)
    monkeypatch.setattr(get_prize, "retry", retry)
    monkeypatch.setattr(get_prize, "update_model_for_retry", Mock())
    return get_prize, auto, log, retry


def test_pass_prize_stops_when_fallback_mail_anchor_is_missing(prize_context):
    get_prize, auto, log, _retry = prize_context

    get_prize.get_pass_prize()

    auto.mouse_click.assert_not_called()
    assert auto.find_element.call_args_list.count(call("home/mail_assets.png")) == 1
    log.error.assert_called_once_with("无法收取日常/周常")


def test_pass_prize_fallback_is_attempted_once(prize_context):
    get_prize, auto, log, _retry = prize_context
    auto.find_element.side_effect = lambda target, **_kwargs: (120, 180) if target == "home/mail_assets.png" else None

    get_prize.get_pass_prize()

    auto.mouse_click.assert_called_once_with(120, 280)
    assert auto.find_element.call_args_list.count(call("home/mail_assets.png")) == 1
    log.error.assert_called_once_with("无法收取日常/周常")


def test_pass_prize_can_collect_daily_and_weekly_rewards_after_fallback(prize_context):
    get_prize, auto, log, retry = prize_context
    fallback_used = False

    def find_element(target, **_kwargs):
        nonlocal fallback_used
        if target == "home/mail_assets.png":
            fallback_used = True
            return (120, 180)
        if target == "pass/pass_coin.png" and fallback_used:
            return [(10, 20)]
        return None

    auto.find_element.side_effect = find_element

    get_prize.get_pass_prize()

    assert auto.mouse_click.call_args_list == [call(120, 280), call(10, 20), call(10, 20)]
    assert call("pass/weekly_assets.png") in auto.click_element.call_args_list
    assert retry.call_count == 2
    log.error.assert_not_called()

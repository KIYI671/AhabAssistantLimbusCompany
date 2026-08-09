from __future__ import annotations

import importlib
import logging
from types import SimpleNamespace

import pytest

import module.game_and_screen as game_and_screen
import module.game_and_screen.game as game_module
from module.game_and_screen.game import Game
from module.game_and_screen.screen import Screen
from module.game_and_screen.steam_cloud import (
    handle_steam_cloud_sync_dialog,
    resolve_steam_cloud_dialog,
)


def _entry(text: str, box: tuple[int, int, int, int]) -> tuple[str, tuple[int, int, int, int]]:
    return text, box


def _reported_cloud_sync_entries() -> list[tuple[str, tuple[int, int, int, int]]]:
    return [
        _entry("无法同步", (157, 133, 278, 166)),
        _entry("Steam 未能将您的存档与 Steam 云同步。", (156, 179, 573, 203)),
        _entry("如果您现在进行游戏，可能无法获取之前的游戏进度，且可能永远失去进度。", (155, 246, 820, 267)),
        _entry("仍然进行游戏", (520, 330, 668, 371)),
        _entry("取消", (687, 330, 837, 371)),
    ]


def test_resolve_steam_cloud_dialog_returns_only_continue_button_from_reported_layout() -> None:
    dialog = resolve_steam_cloud_dialog(_reported_cloud_sync_entries())

    assert dialog is not None
    assert dialog.continue_position == (594, 350)
    assert dialog.continue_bounds == (520, 330, 668, 371)


def test_resolve_steam_cloud_dialog_requires_all_cloud_sync_evidence() -> None:
    required_fragments = ("无法同步", "未能将您的存档", "Steam 云同步", "仍然进行游戏")

    for fragment in required_fragments:
        entries = [entry for entry in _reported_cloud_sync_entries() if fragment not in entry[0]]
        assert resolve_steam_cloud_dialog(entries) is None


def test_resolve_steam_cloud_dialog_rejects_cancel_only_and_misplaced_continue() -> None:
    cancel_only = [entry for entry in _reported_cloud_sync_entries() if "仍然进行游戏" not in entry[0]]
    misplaced_continue = _reported_cloud_sync_entries()
    misplaced_continue[3] = _entry("仍然进行游戏", (520, 150, 668, 175))

    assert resolve_steam_cloud_dialog(cancel_only) is None
    assert resolve_steam_cloud_dialog(misplaced_continue) is None


def test_resolve_steam_cloud_dialog_rejects_evidence_from_separate_desktop_regions() -> None:
    entries = _reported_cloud_sync_entries()
    entries[1] = _entry("Steam 未能将您的存档与 Steam 云同步。", (1200, 600, 1600, 640))
    entries[2] = _entry("仍然进行游戏", (1280, 700, 1420, 740))

    assert resolve_steam_cloud_dialog(entries) is None


def test_resolve_steam_cloud_dialog_rejects_adjacent_window_button_and_nonexact_title() -> None:
    adjacent_button = _reported_cloud_sync_entries()
    adjacent_button[3] = _entry("仍然进行游戏", (700, 330, 848, 371))
    adjacent_button[4] = _entry("其他窗口", (867, 330, 1017, 371))
    nonexact_title = _reported_cloud_sync_entries()
    nonexact_title[0] = _entry("其他无法同步提示", (157, 133, 358, 166))

    assert resolve_steam_cloud_dialog(adjacent_button) is None
    assert resolve_steam_cloud_dialog(nonexact_title) is None


def test_handle_steam_cloud_sync_dialog_clicks_only_authorized_continue_button() -> None:
    clicks: list[tuple[int, int]] = []

    handled = handle_steam_cloud_sync_dialog(
        capture=lambda: object(),
        recognize=lambda _: _reported_cloud_sync_entries(),
        click=lambda x, y: clicks.append((x, y)),
    )

    assert handled is True
    assert clicks == [(594, 350)]


def test_handle_steam_cloud_sync_dialog_consumes_confirmation_before_click_exception() -> None:
    confirmations: list[str] = []
    clicks: list[tuple[int, int]] = []

    handled = handle_steam_cloud_sync_dialog(
        capture=lambda: object(),
        recognize=lambda _: _reported_cloud_sync_entries(),
        click=lambda x, y: clicks.append((x, y)) or (_ for _ in ()).throw(RuntimeError("click failed")),
        on_dialog_detected=lambda: confirmations.append("consumed"),
    )

    assert handled is False
    assert confirmations == ["consumed"]
    assert clicks == [(594, 350)]


def test_handle_steam_cloud_sync_dialog_does_not_click_on_empty_or_failed_recognition() -> None:
    for recognize in (
        lambda _: [],
        lambda _: [entry for entry in _reported_cloud_sync_entries() if "仍然进行游戏" not in entry[0]],
        lambda _: (_ for _ in ()).throw(RuntimeError("OCR unavailable")),
    ):
        clicks: list[tuple[int, int]] = []

        handled = handle_steam_cloud_sync_dialog(
            capture=lambda: object(),
            recognize=recognize,
            click=lambda x, y: clicks.append((x, y)),
        )

        assert handled is False
        assert clicks == []


def test_handle_steam_cloud_sync_dialog_does_not_click_when_capture_returns_nothing() -> None:
    clicks: list[tuple[int, int]] = []

    handled = handle_steam_cloud_sync_dialog(
        capture=lambda: None,
        recognize=lambda _: _reported_cloud_sync_entries(),
        click=lambda x, y: clicks.append((x, y)),
    )

    assert handled is False
    assert clicks == []


def _new_game(game_path: str = r"Z:\missing\LimbusCompany.exe") -> Game:
    game = object.__new__(Game)
    game.game_path = game_path
    game.game_url = "steam://rungameid/1973530"
    game.log = logging.getLogger("test-steam-cloud")
    game.process_name = "LimbusCompany.exe"
    game.game_path_exists = True
    game._launch_requested_at = None
    game._cloud_sync_confirmation_attempted = False
    game._invalid_path_logged = False
    return game


def test_check_game_alive_matches_only_the_full_process_name_case_insensitively(monkeypatch) -> None:
    game = _new_game()
    matching_process = SimpleNamespace(info={"name": "limbuscompany.EXE"}, pid=99)
    similar_process = SimpleNamespace(info={"name": "LimbusCompany.exe.helper"}, pid=100)
    monkeypatch.setattr(game_module.psutil, "process_iter", lambda _: [matching_process, similar_process])

    assert game.check_game_alive() is True

    monkeypatch.setattr(game_module.psutil, "process_iter", lambda _: [similar_process])
    assert game.check_game_alive() is False


def test_start_game_uses_one_steam_request_while_launch_is_pending(monkeypatch) -> None:
    game = _new_game()
    steam_requests: list[str] = []
    monkeypatch.setattr(game, "check_game_alive", lambda: False)
    monkeypatch.setattr(game_module.os.path, "exists", lambda _: False)
    monkeypatch.setattr(game_module.webbrowser, "open", lambda url: steam_requests.append(url))
    monkeypatch.setattr(game_module, "sleep", lambda _: None)
    monkeypatch.setattr(game_module, "monotonic", lambda: 10.0)

    assert game.start_game() is True
    assert game.start_game() is True

    assert steam_requests == ["steam://rungameid/1973530"]


def test_start_game_prefers_existing_local_game_path(monkeypatch) -> None:
    game = _new_game(r"D:\\SteamLibrary\\steamapps\\common\\Limbus Company\\LimbusCompany.exe")
    local_launches: list[str] = []
    monkeypatch.setattr(game, "check_game_alive", lambda: False)
    monkeypatch.setattr(game_module.os.path, "exists", lambda _: True)
    monkeypatch.setattr(game_module.os, "startfile", lambda path: local_launches.append(path), raising=False)
    monkeypatch.setattr(game_module.webbrowser, "open", lambda _: pytest.fail("本地路径存在时不应调用 Steam URL"))
    monkeypatch.setattr(game_module, "monotonic", lambda: 10.0)

    assert game.start_game() is True
    assert local_launches == [r"D:\\SteamLibrary\\steamapps\\common\\Limbus Company\\LimbusCompany.exe"]


def test_existing_game_process_enters_pending_launch_without_requesting_steam_again(monkeypatch) -> None:
    game = _new_game()
    confirmations: list[str] = []
    monkeypatch.setattr(game, "check_game_alive", lambda: True)
    monkeypatch.setattr(game_module.webbrowser, "open", lambda _: pytest.fail("已有游戏进程时不应重启 Steam"))
    monkeypatch.setattr(game_module, "monotonic", lambda: 10.0)
    monkeypatch.setattr(game_module, "handle_steam_cloud_sync_dialog", lambda **_: confirmations.append("continue") or True)

    assert game.start_game() is True
    assert game.handle_pending_launch() is True
    assert game._launch_requested_at == 10.0
    assert confirmations == ["continue"]


def test_pending_launch_consumes_cloud_confirmation_even_when_click_fails(monkeypatch) -> None:
    game = _new_game()
    attempts: list[str] = []
    game._launch_requested_at = 10.0
    monkeypatch.setattr(
        game_module,
        "handle_steam_cloud_sync_dialog",
        lambda *, on_dialog_detected: attempts.append("click") or on_dialog_detected() or False,
    )

    assert game.handle_pending_launch() is False
    assert game.handle_pending_launch() is False
    assert attempts == ["click"]


def test_pending_launch_attempts_cloud_confirmation_only_once(monkeypatch) -> None:
    game = _new_game()
    confirmations: list[str] = []
    game._launch_requested_at = 10.0
    game._cloud_sync_confirmation_attempted = False
    monkeypatch.setattr(
        game_module,
        "handle_steam_cloud_sync_dialog",
        lambda *, on_dialog_detected: confirmations.append("continue") or on_dialog_detected() or True,
    )

    assert game.handle_pending_launch() is True
    assert game.handle_pending_launch() is False

    assert confirmations == ["continue"]


def test_close_game_clears_pending_launch_before_a_following_start(monkeypatch) -> None:
    game = _new_game()
    steam_requests: list[str] = []
    game._launch_requested_at = 10.0
    monkeypatch.setattr(game, "check_game_alive", lambda: False)
    monkeypatch.setattr(game_module.os.path, "exists", lambda _: False)
    monkeypatch.setattr(game_module.webbrowser, "open", lambda url: steam_requests.append(url))
    monkeypatch.setattr(game_module, "monotonic", lambda: 20.0)

    assert game.close_game() is True
    assert game.start_game() is True
    assert steam_requests == ["steam://rungameid/1973530"]


def test_finish_launch_attempt_clears_pending_state() -> None:
    game = _new_game()
    game._launch_requested_at = 10.0
    game._cloud_sync_confirmation_attempted = True

    game.finish_launch_attempt()

    assert game._launch_requested_at is None
    assert game._cloud_sync_confirmation_attempted is False


def test_init_handle_can_check_for_window_without_implicitly_restarting_game() -> None:
    starts: list[str] = []
    screen = object.__new__(Screen)
    screen.title = "LimbusCompany"
    screen.game = SimpleNamespace(start_game=lambda: starts.append("start"))
    screen.handle = SimpleNamespace(hwnd=0, init_handle=lambda _: 0)

    assert screen.init_handle(start_if_missing=False) is False
    assert starts == []


def test_init_game_stops_after_one_bounded_launch_attempt(monkeypatch) -> None:
    scheme = importlib.import_module("tasks.base.script_task_scheme")
    calls: list[str] = []
    moments = iter((0.0, 0.0, scheme.GAME_LAUNCH_TIMEOUT_SECONDS + 1.0))
    monkeypatch.setattr(scheme, "cfg", SimpleNamespace(simulator=False, set_windows=False))
    monkeypatch.setattr(scheme, "auto", SimpleNamespace(init_input=lambda: calls.append("input")))
    monkeypatch.setattr(
        scheme,
        "game_process",
        SimpleNamespace(
            start_game=lambda: calls.append("start") or True,
            handle_pending_launch=lambda: calls.append("pending"),
            finish_launch_attempt=lambda: calls.append("finish"),
        ),
    )
    monkeypatch.setattr(scheme, "screen", SimpleNamespace(init_handle=lambda **kwargs: calls.append(kwargs) or False))
    monkeypatch.setattr(scheme, "sleep", lambda _: None)
    monkeypatch.setattr(scheme, "monotonic", lambda: next(moments))

    with pytest.raises(scheme.withOutGameWinError, match="游戏窗口启动超时"):
        scheme.init_game()

    assert calls == ["input", "start", {"start_if_missing": False}, "pending", "finish"]


def test_close_game_requests_normal_exit_and_avoids_forced_termination(monkeypatch) -> None:
    game = _new_game()
    alive_states = iter((True, True, False, False))
    messages: list[tuple[int, int]] = []
    monkeypatch.setattr(game, "check_game_alive", lambda: next(alive_states))
    monkeypatch.setattr(game_and_screen, "screen", SimpleNamespace(handle=SimpleNamespace(hwnd=42)))
    monkeypatch.setattr(game_module.win32gui, "IsWindow", lambda hwnd: hwnd == 42)
    monkeypatch.setattr(
        game_module.win32gui,
        "PostMessage",
        lambda hwnd, message, _wparam, _lparam: messages.append((hwnd, message)),
    )
    monkeypatch.setattr(game_module, "monotonic", lambda: 0.0)
    monkeypatch.setattr(game_module, "sleep", lambda _: None)
    monkeypatch.setattr(game_module.subprocess, "run", lambda *_args, **_kwargs: pytest.fail("正常退出不应强杀"))

    assert game.close_game() is True

    assert messages == [(42, game_module.win32con.WM_CLOSE)]


def test_close_game_forces_process_only_after_graceful_timeout(monkeypatch) -> None:
    game = _new_game()
    alive_states = iter((True, True, True, True))
    forced_commands: list[list[str]] = []
    monkeypatch.setattr(game, "check_game_alive", lambda: next(alive_states))
    monkeypatch.setattr(game_and_screen, "screen", SimpleNamespace(handle=SimpleNamespace(hwnd=0)))
    moments = iter((0.0, 31.0))
    monkeypatch.setattr(game_module, "monotonic", lambda: next(moments))
    monkeypatch.setattr(game_module, "sleep", lambda _: None)
    monkeypatch.setattr(
        game_module.subprocess,
        "run",
        lambda command, **_kwargs: forced_commands.append(command) or SimpleNamespace(returncode=0, stderr="", stdout=""),
    )

    assert game.close_game() is True

    assert forced_commands == [["taskkill", "/F", "/IM", "LimbusCompany.exe"]]


def test_background_screenshot_recovery_delegates_to_graceful_game_close(monkeypatch) -> None:
    import module.automation.screenshot as screenshot_module

    scheme = importlib.import_module("tasks.base.script_task_scheme")
    calls: list[str] = []
    monkeypatch.setattr(screenshot_module, "screen", SimpleNamespace(handle=SimpleNamespace(hwnd=0)))
    monkeypatch.setattr(game_and_screen, "game_process", SimpleNamespace(close_game=lambda: calls.append("close")))
    monkeypatch.setattr(scheme, "init_game", lambda: calls.append("restart"))

    assert screenshot_module.ScreenShot.background_screenshot() is None
    assert calls == ["close", "restart"]


def test_automation_screenshot_timeout_delegates_to_graceful_game_close(monkeypatch) -> None:
    import module.automation.automation as automation_module

    scheme = importlib.import_module("tasks.base.script_task_scheme")
    calls: list[str] = []
    automation = object.__new__(automation_module.Automation)
    automation.last_screenshot_time = 0.0
    monkeypatch.setattr(automation_module, "cfg", SimpleNamespace(screenshot_interval=0.0))
    monkeypatch.setattr(automation_module.ScreenShot, "take_screenshot", lambda _: (_ for _ in ()).throw(RuntimeError("capture failed")))
    monkeypatch.setattr(game_and_screen, "game_process", SimpleNamespace(close_game=lambda: calls.append("close")))
    monkeypatch.setattr(scheme, "init_game", lambda: calls.append("restart"))
    times = iter((0.0, 61.0, 61.0))
    monkeypatch.setattr(automation_module.time, "time", lambda: next(times))
    monkeypatch.setattr(automation_module.time, "sleep", lambda _: None)

    with pytest.raises(StopIteration):
        automation.take_screenshot()

    assert calls == ["close", "restart"]


def test_all_windows_game_exit_callers_delegate_to_game_close(monkeypatch) -> None:
    import module.system_actions as system_actions
    import tasks.base.retry as retry

    calls: list[str] = []
    monkeypatch.setattr(game_and_screen, "game_process", SimpleNamespace(close_game=lambda: calls.append("close") or True))
    monkeypatch.setattr(retry, "cfg", SimpleNamespace(simulator=False))
    monkeypatch.setattr(system_actions, "cfg", SimpleNamespace(get_value=lambda key, default=None: False))

    retry.kill_game()
    system_actions._action_exit_game()

    assert calls == ["close", "close"]

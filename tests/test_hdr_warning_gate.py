import unittest
from types import SimpleNamespace
from unittest import mock

import tasks.base.script_task_scheme as scheme
from module.game_and_screen.hdr import HdrDisplayInfo
from module.my_error.my_error import userStopError


class ImmediateSignal:
    def __init__(self):
        self.events = []

    def emit(self, event):
        self.events.append(event)
        event.set()


class TestHdrWarningGate(unittest.TestCase):
    def test_simulator_mode_skips_hdr_query(self):
        with (
            mock.patch.object(scheme, "cfg", SimpleNamespace(simulator=True)),
            mock.patch.object(scheme, "get_monitor_hdr_info") as query,
        ):
            scheme._warn_if_game_monitor_hdr_enabled()

        query.assert_not_called()

    def test_disabled_setting_skips_hdr_query(self):
        cfg_stub = SimpleNamespace(
            simulator=False,
            get_value=lambda key, default=None: False,
        )
        with (
            mock.patch.object(scheme, "cfg", cfg_stub),
            mock.patch.object(scheme, "get_monitor_hdr_info") as query,
        ):
            scheme._warn_if_game_monitor_hdr_enabled()

        query.assert_not_called()

    def test_query_failure_allows_task_to_continue(self):
        warning = mock.Mock()
        mediator_stub = SimpleNamespace(
            hdr_warning=SimpleNamespace(emit=warning),
            hdr_warning_clear=SimpleNamespace(emit=mock.Mock()),
        )
        with (
            mock.patch.object(
                scheme,
                "cfg",
                SimpleNamespace(
                    simulator=False,
                    get_value=lambda key, default=None: True,
                ),
            ),
            mock.patch.object(scheme, "mediator", mediator_stub),
            mock.patch.object(
                scheme,
                "screen",
                SimpleNamespace(handle=SimpleNamespace(hwnd=123)),
            ),
            mock.patch.object(scheme.win32api, "MonitorFromWindow", return_value=456),
            mock.patch.object(
                scheme,
                "get_monitor_hdr_info",
                side_effect=RuntimeError("query failed"),
            ),
        ):
            scheme._warn_if_game_monitor_hdr_enabled()

        warning.assert_not_called()

    def test_hdr_warning_waits_for_acknowledgement(self):
        signal = ImmediateSignal()
        mediator_stub = SimpleNamespace(
            hdr_warning=signal,
            hdr_warning_clear=SimpleNamespace(emit=mock.Mock()),
        )
        with (
            mock.patch.object(
                scheme,
                "cfg",
                SimpleNamespace(
                    simulator=False,
                    get_value=lambda key, default=None: True,
                ),
            ),
            mock.patch.object(scheme, "mediator", mediator_stub),
            mock.patch.object(
                scheme,
                "screen",
                SimpleNamespace(handle=SimpleNamespace(hwnd=123)),
            ),
            mock.patch.object(scheme.win32api, "MonitorFromWindow", return_value=456),
            mock.patch.object(
                scheme,
                "get_monitor_hdr_info",
                return_value=HdrDisplayInfo(456, 12),
            ),
        ):
            scheme._warn_if_game_monitor_hdr_enabled()

        self.assertEqual(len(signal.events), 1)

    def test_stop_wins_when_acknowledgement_is_already_set(self):
        signal = ImmediateSignal()
        clear = mock.Mock()
        mediator_stub = SimpleNamespace(
            hdr_warning=signal,
            hdr_warning_clear=SimpleNamespace(emit=clear),
        )
        with (
            mock.patch.object(
                scheme,
                "cfg",
                SimpleNamespace(
                    simulator=False,
                    get_value=lambda key, default=None: True,
                ),
            ),
            mock.patch.object(scheme, "mediator", mediator_stub),
            mock.patch.object(
                scheme,
                "screen",
                SimpleNamespace(handle=SimpleNamespace(hwnd=123)),
            ),
            mock.patch.object(scheme.win32api, "MonitorFromWindow", return_value=456),
            mock.patch.object(
                scheme,
                "get_monitor_hdr_info",
                return_value=HdrDisplayInfo(456, 12),
            ),
            mock.patch.object(
                scheme.QThread,
                "currentThread",
                return_value=SimpleNamespace(
                    waiting_for_hdr_warning=False,
                    isInterruptionRequested=lambda: True,
                ),
            ),
            self.assertRaises(userStopError),
        ):
            scheme._warn_if_game_monitor_hdr_enabled()

        clear.assert_not_called()

    def test_stop_during_warning_closes_dialog_and_propagates(self):
        event = mock.Mock()
        event.wait.return_value = False
        event.is_set.return_value = False
        clear = mock.Mock()
        mediator_stub = SimpleNamespace(
            hdr_warning=SimpleNamespace(emit=mock.Mock()),
            hdr_warning_clear=SimpleNamespace(emit=clear),
        )
        with (
            mock.patch.object(
                scheme,
                "cfg",
                SimpleNamespace(
                    simulator=False,
                    get_value=lambda key, default=None: True,
                ),
            ),
            mock.patch.object(scheme, "mediator", mediator_stub),
            mock.patch.object(
                scheme,
                "screen",
                SimpleNamespace(handle=SimpleNamespace(hwnd=123)),
            ),
            mock.patch.object(scheme.win32api, "MonitorFromWindow", return_value=456),
            mock.patch.object(
                scheme,
                "get_monitor_hdr_info",
                return_value=HdrDisplayInfo(456, 12),
            ),
            mock.patch.object(scheme, "Event", return_value=event),
            mock.patch.object(
                scheme.QThread,
                "currentThread",
                return_value=SimpleNamespace(
                    waiting_for_hdr_warning=False,
                    isInterruptionRequested=lambda: True,
                ),
            ),
            self.assertRaises(userStopError),
        ):
            scheme._warn_if_game_monitor_hdr_enabled()

        clear.assert_called_once_with(event)


if __name__ == "__main__":
    unittest.main()

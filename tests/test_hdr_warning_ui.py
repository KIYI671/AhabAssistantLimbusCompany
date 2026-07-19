import unittest
from pathlib import Path
from typing import get_type_hints
from unittest import mock

from PySide6.QtWidgets import QApplication

import app.base_combination as base_combination_module
import app.my_app as my_app_module
import module.config.config_typing as config_typing_module
from app.farming_interface import FarmingInterfaceLeft
from app.setting_interface import SettingInterface


class EventStub:
    def __init__(self):
        self.was_set = False

    def set(self):
        self.was_set = True


class TestHdrWarningUi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_dialog_always_releases_waiting_task(self):
        event = EventStub()
        dialog = mock.Mock()
        dialog.exec.side_effect = RuntimeError("dialog failed")
        window = my_app_module.MainWindow.__new__(my_app_module.MainWindow)
        window.tr = lambda text: text

        with mock.patch.object(my_app_module, "MessageBoxWarning", return_value=dialog):
            my_app_module.MainWindow.show_hdr_warning(window, event)

        self.assertTrue(event.was_set)
        self.assertIsNone(window._current_hdr_warning_box)

    def test_clear_only_closes_matching_hdr_dialog(self):
        current_event = EventStub()
        other_event = EventStub()
        dialog = mock.Mock()
        window = my_app_module.MainWindow.__new__(my_app_module.MainWindow)
        window._current_hdr_warning_event = current_event
        window._current_hdr_warning_box = dialog

        my_app_module.MainWindow.clear_hdr_warning(window, other_event)
        dialog.accept.assert_not_called()

        my_app_module.MainWindow.clear_hdr_warning(window, current_event)
        dialog.accept.assert_called_once_with()

    def test_config_default_is_enabled(self):
        hints = get_type_hints(config_typing_module.ConfigModel)
        self.assertIs(hints["experimental_hdr_warning"], bool)

        config_text = (
            Path(__file__).resolve().parents[1]
            / "assets/config/config.example.yaml"
        ).read_text(encoding="utf-8")
        self.assertIn("experimental_hdr_warning: True", config_text)

    def test_setting_card_is_in_experimental_group_and_enabled(self):
        original_get_value = base_combination_module.cfg.get_value

        def get_value(key, *args, **kwargs):
            if key == "experimental_hdr_warning":
                return True
            return original_get_value(key, *args, **kwargs)

        with mock.patch.object(
            base_combination_module.cfg,
            "get_value",
            side_effect=get_value,
        ):
            interface = SettingInterface()
        try:
            widgets = interface.experimental_group.cardLayout._ExpandLayout__widgets
            self.assertIn(interface.hdr_warning_card, widgets)
            self.assertTrue(interface.hdr_warning_card.switchButton.checked)
        finally:
            interface.close()
            self.app.processEvents()

    def test_hdr_warning_stop_waits_for_original_task(self):
        script = mock.Mock()
        script.isRunning.return_value = True
        script.waiting_for_hdr_warning = True
        interface = FarmingInterfaceLeft.__new__(FarmingInterfaceLeft)
        interface.my_script = script

        FarmingInterfaceLeft.stop_script(interface)

        script.stop.assert_called_once_with()
        script.wait.assert_called_once_with(2000)
        script.terminate.assert_not_called()

    def test_hdr_warning_stop_timeout_falls_back_to_terminate(self):
        script = mock.Mock()
        script.isRunning.return_value = True
        script.waiting_for_hdr_warning = True
        script.wait.side_effect = [False, True]
        interface = FarmingInterfaceLeft.__new__(FarmingInterfaceLeft)
        interface.my_script = script

        FarmingInterfaceLeft.stop_script(interface)

        script.terminate.assert_called_once_with()
        self.assertEqual(
            script.wait.call_args_list,
            [mock.call(2000), mock.call(500)],
        )


if __name__ == "__main__":
    unittest.main()

import unittest
from unittest import mock

from module.game_and_screen import hdr


class TestHdrDetection(unittest.TestCase):
    def test_only_pq_bt2020_color_space_is_hdr(self):
        self.assertTrue(hdr.HdrDisplayInfo(1, 12).hdr_enabled)
        self.assertFalse(hdr.HdrDisplayInfo(1, 0).hdr_enabled)
        self.assertFalse(hdr.HdrDisplayInfo(1, 14).hdr_enabled)

    def test_get_monitor_hdr_info_returns_matching_monitor(self):
        first = hdr.HdrDisplayInfo(1, 0)
        second = hdr.HdrDisplayInfo(2, 12)

        with mock.patch.object(
            hdr,
            "enumerate_hdr_displays",
            return_value=[first, second],
        ):
            result = hdr.get_monitor_hdr_info(2)

        self.assertIs(result, second)

    def test_get_monitor_hdr_info_returns_none_when_monitor_is_missing(self):
        with mock.patch.object(hdr, "enumerate_hdr_displays", return_value=[]):
            result = hdr.get_monitor_hdr_info(999)

        self.assertIsNone(result)

    def test_com_initialization_failure_does_not_uninitialize(self):
        with (
            mock.patch.object(
                hdr._ole32,
                "CoInitializeEx",
                return_value=-2147417850,
            ),
            mock.patch.object(hdr._ole32, "CoUninitialize") as uninitialize,
        ):
            result = hdr.enumerate_hdr_displays()

        self.assertEqual(result, [])
        uninitialize.assert_not_called()


if __name__ == "__main__":
    unittest.main()

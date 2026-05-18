import types
import unittest
from unittest import mock

from PIL import Image

from tasks.mirror.in_shop import _extract_money_from_ocr_texts, _retry_money_ocr_with_scaled_crop


class TestShopMoneyOcr(unittest.TestCase):
    def test_extract_money_accepts_plain_digits(self):
        self.assertEqual(_extract_money_from_ocr_texts(["285"]), 285)

    def test_extract_money_ignores_unrelated_text_and_uses_later_digits(self):
        self.assertEqual(_extract_money_from_ocr_texts(["Refres", "285"]), 285)

    def test_extract_money_normalizes_common_digit_confusions(self):
        self.assertEqual(_extract_money_from_ocr_texts(["G10 "]), 610)

    def test_extract_money_returns_none_for_non_numeric_text(self):
        self.assertIsNone(_extract_money_from_ocr_texts(["Refres"]))

    @mock.patch("tasks.mirror.in_shop.ocr.run")
    @mock.patch("tasks.mirror.in_shop.auto")
    def test_retry_money_ocr_with_scaled_crop_uses_enlarged_crop(self, auto_mock, ocr_run_mock):
        auto_mock.screenshot = Image.new("RGB", (20, 20), color="black")
        ocr_run_mock.return_value = types.SimpleNamespace(txts=["610"])

        result = _retry_money_ocr_with_scaled_crop((2, 2, 8, 8), scale=2)

        self.assertEqual(result, ["610"])
        enlarged_crop = ocr_run_mock.call_args.args[0]
        self.assertEqual(enlarged_crop.size, (12, 12))


if __name__ == "__main__":
    unittest.main()

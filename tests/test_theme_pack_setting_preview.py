import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import QApplication

from app.theme_pack_setting_interface import (
    THEME_PACK_PREVIEW_SIZE,
    ThemePackImageLabel,
    ThemePackSettingDialog,
    load_theme_pack_preview,
)


def get_qapp():
    return QApplication.instance() or QApplication([])


def test_preview_cache_preserves_alpha(tmp_path):
    get_qapp()
    source = QImage(THEME_PACK_PREVIEW_SIZE, QImage.Format.Format_ARGB32)
    source.fill(Qt.GlobalColor.transparent)
    source.setPixelColor(75, 136, QColor("#ff0000"))
    image_path = tmp_path / "transparent.png"
    assert source.save(str(image_path))

    load_theme_pack_preview.cache_clear()
    preview = load_theme_pack_preview(str(image_path))
    cached = load_theme_pack_preview(str(image_path))

    assert preview is cached
    assert preview.hasAlphaChannel()
    assert preview.toImage().pixelColor(0, 0).alpha() == 0
    assert load_theme_pack_preview.cache_info().hits == 1


def test_image_label_uses_checkerboard_for_transparent_pixels(tmp_path):
    get_qapp()
    source = QImage(THEME_PACK_PREVIEW_SIZE, QImage.Format.Format_ARGB32)
    source.fill(QColor("#ff0000"))
    source.setPixelColor(0, 0, QColor(0, 0, 0, 0))
    image_path = tmp_path / "transparent-corner.png"
    assert source.save(str(image_path))

    label = ThemePackImageLabel()
    label.setPixmap(load_theme_pack_preview(str(image_path)))
    rendered = QImage(label.size(), QImage.Format.Format_ARGB32)
    rendered.fill(Qt.GlobalColor.transparent)
    label.render(rendered)

    assert rendered.pixelColor(0, 0).alpha() == 255
    assert rendered.pixelColor(0, 0) != QColor("#ff0000")
    assert rendered.pixelColor(75, 136) == QColor("#ff0000")


def test_dialog_defers_card_widget_creation_until_event_loop_runs():
    get_qapp()
    config = {
        "preferred_thresholds": 0,
        "theme_pack_list": {"forgot": 0, "gambl": 0},
        "theme_pack_list_hard": {"line": -5},
        "theme_pack_list_cn": {"遗忘": 0, "赌徒": 0},
        "theme_pack_list_hard_cn": {"号线": -5},
    }
    dialog = ThemePackSettingDialog(None, config, "test-theme-pack.yaml")

    assert not dialog.normal_cards
    assert not dialog.hard_cards
    assert len(dialog._pending_cards) == 3
    assert not dialog.save_button.isEnabled()

    dialog._card_load_timer.stop()
    dialog._load_theme_pack_batch()

    assert len(dialog.normal_cards) == 2
    assert len(dialog.hard_cards) == 1
    assert not dialog._pending_cards
    assert dialog.save_button.isEnabled()

    dialog.close()

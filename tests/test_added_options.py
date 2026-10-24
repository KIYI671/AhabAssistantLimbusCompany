"""Optional shops and portable icon protection; never capture or click the game."""

import ast
import importlib.util
import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import Mock, patch

import numpy as np
import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture
def tmp_path():
    with TemporaryDirectory(prefix="aalc-added-options-", dir=ROOT / "tests") as directory:
        path = Path(directory).resolve()
        assert path.is_relative_to((ROOT / "tests").resolve())
        yield path


def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


actions = load("added_ego_actions", "tasks/battle/optional_actions.py")
schema = load("added_options_schema", "module/config/config_typing.py")
icons = load("added_protected_icons", "utils/protected_gifts.py")








def test_disabled_ego_does_not_probe_menu():
    auto = Mock()
    control = actions.TurnEgoAction(auto, 1440, actions.BattleOptions(), Mock(), None)
    assert control.perform() is False
    auto.find_element.assert_not_called()


def test_retired_prechecks_cannot_be_enabled_by_legacy_team_data():
    key = "auto_corrosion_direct"
    team = schema.TeamSetting(**{key: True})
    assert key not in team.model_dump()
    assert key not in schema.ConfigModel.model_fields
    assert key not in actions.BattleOptions.__dataclass_fields__
    assert not hasattr(actions.TurnEgoAction, "_already_corroded")
    assert not hasattr(actions.TurnEgoAction, "corrosion_bypass")


def art(path):
    pixels = np.random.default_rng(54).integers(0, 255, (80, 80, 4), dtype=np.uint8)
    pixels[:, :, 3] = 255
    image = Image.fromarray(pixels, "RGBA")
    image.save(path)
    return image


def test_import_copies_image_and_survives_original_deletion(tmp_path):
    source = tmp_path / "针线.png"
    art(source)
    imported = Path(icons.import_gift_image(source, tmp_path / "assets"))
    assert imported.read_bytes() == source.read_bytes()
    assert Path(icons.import_gift_image(source, tmp_path / "assets")) == imported
    source.unlink()
    assert imported.is_file()


def test_matching_protects_only_the_requested_cell(tmp_path):
    path = tmp_path / "gift.png"
    image = art(path)
    screenshot = Image.new("RGB", (1920, 1080), (20, 20, 20))
    screenshot.paste(image.convert("RGB"), (260, 260))
    matcher = icons.ProtectedGiftMatcher([str(path)])
    assert matcher.match(screenshot, (300, 300)) == str(path)
    assert matcher.match(screenshot, (400, 300)) is None
    assert matcher.match(screenshot, (1000, 300)) is None


NEEDLE_CAPTURE = ROOT / "tests/fixtures/gift_protection/needle-imported.png"
OTHER_GIFT = ROOT / "tests/fixtures/gift_protection/grand-welcome.png"


def gift_scene(height=1080, icon_width=214, origin=(500, 300)):
    with Image.open(NEEDLE_CAPTURE) as source:
        icon = source.convert("RGB")
    if icon_width != icon.width:
        icon = icon.resize((icon_width, round(icon_width * icon.height / icon.width)), Image.Resampling.LANCZOS)
    screen = Image.new("RGB", (round(height * 16 / 9), height), (24, 24, 24))
    screen.paste(icon, origin)
    return screen, (origin[0] + icon.width / 2, origin[1] + icon.height / 2)


@pytest.mark.parametrize("height,icon_width", [(1080, 214), (1080, 140), (1080, 150),
                                              (720, 107), (1440, 214), (1440, 285)])
def test_imported_needle_actual_art_matches_at_native_and_game_sizes(height, icon_width):
    screen, center = gift_scene(height, icon_width)
    matcher = icons.ProtectedGiftMatcher([str(NEEDLE_CAPTURE)])
    assert matcher.match(screen, center) == str(NEEDLE_CAPTURE)
    assert matcher.last_scan["score"] >= matcher.threshold


@pytest.mark.parametrize("offset", [(0, 0), (50, 50), (-50, -50), (70, 66)])
def test_full_template_is_kept_for_click_and_badge_offsets(offset):
    # The previous fixed crop lost the far half of the icon when a list
    # candidate was an edge/badge rather than its centre.
    screen, center = gift_scene(icon_width=140)
    matcher = icons.ProtectedGiftMatcher([str(NEEDLE_CAPTURE)])
    point = (center[0] + offset[0], center[1] + offset[1])
    assert matcher.match(screen, point) == str(NEEDLE_CAPTURE)


@pytest.mark.parametrize("origin", [(0, 0), (1706, 878)])
def test_native_needle_at_screenshot_edge(origin):
    screen, center = gift_scene(origin=origin)
    matcher = icons.ProtectedGiftMatcher([str(NEEDLE_CAPTURE)])
    assert matcher.match(screen, center) == str(NEEDLE_CAPTURE)


def test_adjacent_card_and_empty_space_are_not_protected():
    screen, center = gift_scene(icon_width=140)
    with Image.open(OTHER_GIFT) as source:
        other = source.convert("RGB").resize((140, 140), Image.Resampling.LANCZOS)
    screen.paste(other, (643, 300))
    matcher = icons.ProtectedGiftMatcher([str(NEEDLE_CAPTURE)])
    assert matcher.match(screen, center) == str(NEEDLE_CAPTURE)
    assert matcher.match(screen, (713, 370)) is None
    assert matcher.match(screen, (900, 370)) is None
    assert matcher.last_scan["score"] is None or matcher.last_scan["score"] < matcher.threshold


def test_a_higher_peak_outside_candidate_does_not_hide_local_match():
    screen, center = gift_scene(icon_width=140)
    # A second identical icon must not make the local search return a peak
    # belonging to another grid cell and then reject the correct candidate.
    with Image.open(NEEDLE_CAPTURE) as source:
        screen.paste(source.convert("RGB"), (650, 300))
    matcher = icons.ProtectedGiftMatcher([str(NEEDLE_CAPTURE)])
    assert matcher.match(screen, center) == str(NEEDLE_CAPTURE)


def test_transparent_art_matches_over_a_different_background(tmp_path):
    with Image.open(NEEDLE_CAPTURE) as source:
        icon = source.convert("RGBA")
    alpha = np.full((icon.height, icon.width), 255, dtype=np.uint8)
    alpha[:45, :45] = 0
    icon.putalpha(Image.fromarray(alpha))
    path = tmp_path / "transparent-needle.png"
    icon.save(path)
    screen = Image.new("RGB", (1920, 1080), (35, 90, 45))
    screen.paste(icon, (500, 300), icon)
    matcher = icons.ProtectedGiftMatcher([str(path)])
    assert matcher.match(screen, (607, 401)) == str(path)


def test_shop_filter_and_sale_use_the_real_needle_matcher():
    screen, center = gift_scene(icon_width=140)
    other = (center[0] + 143, center[1])
    auto = Mock(screenshot=screen)
    shop, auto, _ = make_shop(auto, protect_gift_images=True,
                             protected_gift_images=[str(NEEDLE_CAPTURE)])
    assert shop._filter_protected_gifts([center, other]) == [other]
    auto.find_element.return_value = [center, other]
    assert shop._unprotected_sale("unwanted") == other
    shop.protect_gift_images = False
    assert shop._filter_protected_gifts([center, other]) == [center, other]


def test_invalid_or_tiny_import_is_rejected(tmp_path):
    path = tmp_path / "tiny.png"
    Image.new("RGB", (3, 3)).save(path)
    with pytest.raises(ValueError):
        icons.import_gift_image(path, tmp_path / "assets")


def shop_class(auto):
    tree = ast.parse((ROOT / "tasks/mirror/in_shop.py").read_text(encoding="utf-8"))
    nodes = [node for node in tree.body if isinstance(node, ast.ClassDef)]
    namespace = dict(auto=auto, cfg=SimpleNamespace(set_win_size=1440, mouse_action_interval=0),
                     TeamSetting=object, log=Mock(), all_systems={i: str(i) for i in range(10)},
                     ProtectedGiftMatcher=icons.ProtectedGiftMatcher, sleep=lambda _: None,
                     retry=lambda: True, fusion_result=[], must_be_abandoned=["ordinary.png"])
    exec(compile(ast.Module(body=nodes, type_ignores=[]), "offline_shop", "exec"), namespace)
    return namespace["Shop"], namespace


def make_shop(auto=None, **settings):
    auto = auto or Mock()
    cls, namespace = shop_class(auto)
    shop = cls(schema.TeamSetting(**settings))
    return shop, auto, namespace


def test_protection_filter_keeps_unmatched_materials_and_fails_closed_on_missing_files():
    shop, auto, _ = make_shop(protect_gift_images=True, protected_gift_images=["needle.png"])
    shop._gift_matcher = Mock()
    shop._gift_matcher.match.side_effect = ["needle.png", None]
    points = [(100, 100), (300, 100)]
    assert shop._filter_protected_gifts(points) == [(300, 100)]
    shop._gift_matcher.match.side_effect = FileNotFoundError("missing reference")
    assert shop._filter_protected_gifts(points) == []
    shop.protect_gift_images = False
    assert shop._filter_protected_gifts(points) is points


def test_sale_search_skips_protected_first_match_but_can_sell_next():
    shop, auto, _ = make_shop(protect_gift_images=True, protected_gift_images=["needle.png"])
    auto.find_element.return_value = [(100, 100), (300, 100)]
    shop._gift_matcher = Mock()
    shop._gift_matcher.match.side_effect = ["needle.png", None]
    assert shop._unprotected_sale("unwanted") == (300, 100)


def test_automatic_recipe_selection_is_not_allowed_to_bypass_image_protection():
    shop, auto, _ = make_shop(protect_gift_images=True, protected_gift_images=["needle.png"])
    shop.fuse_system_gifts()
    auto.mouse_click.assert_not_called()
    auto.click_element.assert_not_called()


def test_failed_first_fusion_stage_prevents_switching_to_other_fusion_modes():
    shop, auto, namespace = make_shop(shop_strategy=2, stop_fusion_on_failure=True)
    shop.enter_fuse = Mock(return_value=True)
    shop.fuse_useless_gifts_aggressive = Mock(side_effect=namespace["FusionAttemptStopped"])
    shop.fuse_useless_gifts = Mock()
    shop.fuse_system_gifts = Mock()
    shop.fuse_gift()
    shop.fuse_useless_gifts_aggressive.assert_called_once()
    shop.fuse_useless_gifts.assert_not_called()
    shop.fuse_system_gifts.assert_not_called()


def test_failure_after_one_success_still_stops_the_current_shop():
    shop, auto, namespace = make_shop(stop_fusion_on_failure=True)

    def partial():
        shop._fusion_successes += 1
        shop._stop_failed_fusion()

    assert shop._run_fusion_stage(partial) is False
    assert shop._fusion_successes == 1


def test_successful_stage_can_continue_and_disabled_option_keeps_original_behavior():
    shop, auto, _ = make_shop(stop_fusion_on_failure=True)

    def success():
        shop._fusion_successes += 1

    assert shop._run_fusion_stage(success)
    assert shop._run_fusion_stage(lambda: None) is False
    shop.stop_fusion_on_failure = False
    assert shop._run_fusion_stage(lambda: None)


def test_actual_empty_aggressive_scan_stops_without_clicking_materials():
    shop, auto, namespace = make_shop(shop_strategy=2, stop_fusion_on_failure=True)
    auto.find_element.side_effect = lambda target, **kw: [] if "fuse_label" in target else None
    auto.take_screenshot.return_value = object()
    assert shop._run_fusion_stage(shop.fuse_useless_gifts_aggressive) is False
    auto.mouse_click.assert_not_called()


def test_actual_aggressive_material_selection_applies_protection_before_clicks():
    shop, auto, _ = make_shop(shop_strategy=2, protect_gift_images=True,
                             protected_gift_images=["needle.png"], stop_fusion_on_failure=True)
    auto.find_element.side_effect = lambda target, **kw: [(100, 200)] if "fuse_label" in target else None
    auto.take_screenshot.return_value = object()
    shop._gift_matcher = Mock()
    shop._gift_matcher.match.return_value = "needle.png"
    assert shop._run_fusion_stage(shop.fuse_useless_gifts_aggressive) is False
    assert shop._gift_matcher.match.call_count == 10
    auto.mouse_click.assert_not_called()


def test_aggressive_fusion_without_any_result_has_a_bounded_failed_attempt():
    shop, auto, _ = make_shop(shop_strategy=2, stop_fusion_on_failure=True)
    auto.find_element.side_effect = lambda target, **kw: (
        [(100, 200)] if "fuse_label" in target else
        True if "fuse_90%" in target or "fusion_level_IV_gift" in target else None
    )
    auto.take_screenshot.return_value = object()
    auto.click_element.return_value = False
    assert shop._run_fusion_stage(shop.fuse_useless_gifts_aggressive) is False
    assert shop._fusion_successes == 0
    assert auto.take_screenshot.call_count <= 20


def test_actual_sale_loop_never_selects_a_protected_item():
    shop, auto, _ = make_shop(protect_gift_images=True, protected_gift_images=["needle.png"])
    shop.shop_sell_list = ["burn"]
    sold = []
    auto.find_element.side_effect = lambda target, **kw: (
        ([(100, 100)] if sold else [(100, 100), (300, 100)])
        if "enhance_gifts" in target or target == "ordinary.png" else None
    )
    auto.take_screenshot.return_value = object()
    auto.mouse_click.side_effect = lambda x, y: sold.append((x, y))
    auto.click_element.return_value = False
    shop._gift_matcher = Mock()
    shop._gift_matcher.match.side_effect = lambda picture, point: "needle.png" if point[0] == 100 else None
    shop.sell_gifts()
    assert sold == [(300, 100)]






def test_ui_import_remove_and_save_protection_without_touching_formation(tmp_path):
    from PySide6.QtWidgets import QApplication

    from app.rabbit_options import GiftLockOptions

    application = QApplication.instance() or QApplication([])
    widget = GiftLockOptions()
    path = tmp_path / "needle.png"
    art(path)
    copied = icons.import_gift_image(path, tmp_path / "assets")
    try:
        with patch("app.rabbit_options.QFileDialog.getOpenFileNames", return_value=([str(path)], "")), \
                patch("app.rabbit_options.import_gift_image", return_value=copied):
            widget._choose_protection_images()
        widget.checks["gift_lock_enabled"].setChecked(True)
        values = widget.settings()
        assert values["gift_lock_images"] == [copied]
        team = schema.TeamSetting(**values)
        widget.load_settings(team)
        assert widget.settings() == values
        widget.checks["gift_lock_enabled"].setChecked(False)
        assert widget.settings()["gift_lock_images"] == [copied]
        widget._remove_protection_image(copied)
        assert widget.settings()["gift_lock_images"] == []
        assert team.chosen_sinners == [0] * 12
    finally:
        widget.close()
        widget.deleteLater()
        application.processEvents()

from types import SimpleNamespace

from tasks.mirror import mirror as mirror_module


def test_theme_pack_floor_detection_is_retryable_and_idempotent(monkeypatch):
    dungeon = mirror_module.Mirror.__new__(mirror_module.Mirror)
    dungeon.floor = 0
    dungeon.normal_to_hard_floor = 2
    dungeon.hard_mode = False
    refreshed_floors = []
    dungeon.mirror_map = SimpleNamespace(hard_mode=False, refresh_floor=refreshed_floors.append)

    monkeypatch.setattr(mirror_module, "sleep", lambda _: None)
    monkeypatch.setattr(mirror_module.auto, "click_element", lambda *args, **kwargs: True)
    monkeypatch.setattr(mirror_module.auto, "mouse_action_with_pos", lambda *args, **kwargs: None)
    monkeypatch.setattr(mirror_module.auto, "find_element", lambda *args, **kwargs: None)

    assert dungeon.get_which_floor("mirror/theme_pack/theme_pack_setting_assets.png") is False
    assert dungeon.floor == 0

    def find_floor(target, *args, **kwargs):
        if target.endswith("to_window_assets.png"):
            return 1200, 600
        if target.endswith("not_passed_floor.png"):
            return [(0, 0)] * 3
        return None

    monkeypatch.setattr(mirror_module.auto, "find_element", find_floor)

    assert dungeon.get_which_floor("mirror/theme_pack/theme_pack_setting_assets.png") is True
    assert dungeon.get_which_floor("mirror/theme_pack/theme_pack_setting_assets.png") is True
    assert dungeon.floor == 2
    assert dungeon.hard_mode is True
    assert refreshed_floors == [2, 2]

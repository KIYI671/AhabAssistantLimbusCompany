import importlib

import pytest

in_shop = importlib.import_module("tasks.mirror.in_shop")
select_theme_pack = importlib.import_module("tasks.mirror.select_theme_pack")


class _ConfirmationAuto:
    def __init__(self, confirm_visible):
        self._confirm_visible = iter(confirm_visible)
        self.find_calls = 0

    def find_element(self, path):
        assert path == "mirror/shop/power_up_confirm_assets.png"
        self.find_calls += 1
        return next(self._confirm_visible)


class _ThemePackAuto:
    def __init__(self, states):
        self._states = states
        self._index = -1

    def take_screenshot(self):
        self._index += 1
        return object()

    def find_element(self, path):
        legend_visible, theme_pack_visible = self._states[self._index]
        if path == "mirror/road_in_mir/legend_assets.png":
            return legend_visible
        if path == "mirror/theme_pack/feature_theme_pack_assets.png":
            return theme_pack_visible
        raise AssertionError(path)


class _ThemePackReadyAuto:
    def __init__(self, states, expected_asset):
        self._states = states
        self._expected_asset = expected_asset
        self._index = -1

    def take_screenshot(self):
        self._index += 1
        return object()

    def find_element(self, path):
        assert path == self._expected_asset
        return self._states[self._index][0]

    def find_image_with_multiple_targets(self, path, threshold):
        assert path == "mirror/theme_pack/theme_pack_features.png"
        assert threshold == 0.8
        return list(self._states[self._index][1])


def test_power_up_wait_returns_as_soon_as_confirmation_closes(monkeypatch):
    fake_auto = _ConfirmationAuto([True, False])
    monkeypatch.setattr(in_shop, "auto", fake_auto)
    monkeypatch.setattr(in_shop, "retry", lambda: None)
    shop = object.__new__(in_shop.Shop)

    assert shop._wait_for_power_up_confirmation(timeout=1.0) is True
    assert fake_auto.find_calls == 2


def test_power_up_wait_stops_when_connection_retry_fails(monkeypatch):
    monkeypatch.setattr(in_shop, "retry", lambda: False)
    shop = object.__new__(in_shop.Shop)

    with pytest.raises(in_shop.Shop.RestartGame):
        shop._wait_for_power_up_confirmation(timeout=1.0)


def test_shop_refresh_wait_uses_scaled_grid_and_fast_local_polling(monkeypatch):
    calls = []

    class _ShopRefreshAuto:
        def wait_until_region_stable(self, crop, **kwargs):
            calls.append((crop, kwargs))
            return True

    initial_sample = object()
    monkeypatch.setattr(in_shop, "auto", _ShopRefreshAuto())
    monkeypatch.setattr(in_shop.cfg, "set_win_size", 720)
    shop = object.__new__(in_shop.Shop)

    assert shop._wait_for_shop_refresh(initial_sample) is True
    assert calls == [
        (
            (540.0, 150.0, 1150.0, 500.0),
            {
                "timeout": 3.0,
                "poll_interval": 0.25,
                "stable_samples": 2,
                "pixel_delta_threshold": 12,
                "max_changed_ratio": 0.02,
                "initial_sample": initial_sample,
                "require_change": True,
            },
        )
    ]


def test_theme_pack_wait_returns_when_selection_screen_disappears(monkeypatch):
    fake_auto = _ThemePackAuto([(False, True), (False, False)])
    monkeypatch.setattr(select_theme_pack, "auto", fake_auto)

    assert select_theme_pack._wait_for_theme_pack_transition(timeout=1.0) is True
    assert fake_auto._index == 1


def test_theme_pack_wait_accepts_map_ready_state(monkeypatch):
    fake_auto = _ThemePackAuto([(True, True)])
    monkeypatch.setattr(select_theme_pack, "auto", fake_auto)

    assert select_theme_pack._wait_for_theme_pack_transition(timeout=1.0) is True
    assert fake_auto._index == 0


def test_theme_pack_ready_waits_until_positions_stop_moving(monkeypatch):
    expected_asset = "mirror/theme_pack/hard_assets.png"
    fake_auto = _ThemePackReadyAuto(
        [
            (True, [(100, 100), (300, 100)]),
            (True, [(120, 100), (320, 100)]),
            (True, [(121, 101), (321, 101)]),
        ],
        expected_asset,
    )
    monkeypatch.setattr(select_theme_pack, "auto", fake_auto)

    assert select_theme_pack._wait_for_theme_pack_ready(expected_asset, timeout=1.0) is True
    assert fake_auto._index == 2


def test_theme_pack_ready_requires_new_difficulty_indicator(monkeypatch):
    expected_asset = "mirror/theme_pack/normal_assets.png"
    fake_auto = _ThemePackReadyAuto(
        [
            (False, [(100, 100)]),
            (True, [(100, 100)]),
            (True, [(100, 100)]),
        ],
        expected_asset,
    )
    monkeypatch.setattr(select_theme_pack, "auto", fake_auto)

    assert select_theme_pack._wait_for_theme_pack_ready(expected_asset, timeout=1.0) is True
    assert fake_auto._index == 2

import importlib

mirror_module = importlib.import_module("tasks.mirror.mirror")


class _RewardAuto:
    def __init__(self, statistics_visible=True, reward_click_succeeds=True):
        self.statistics_visible = statistics_visible
        self.reward_click_succeeds = reward_click_succeeds
        self.find_calls = []
        self.click_calls = []
        self.coordinate_clicks = []

    def find_element(self, path, **kwargs):
        self.find_calls.append((path, kwargs))
        return (93, 203) if self.statistics_visible else None

    def click_element(self, path, **kwargs):
        self.click_calls.append((path, kwargs))
        return self.reward_click_succeeds

    def mouse_click(self, x, y):
        self.coordinate_clicks.append((x, y))

class _LoadingAuto:
    def __init__(self, visible_asset=None):
        self.visible_asset = visible_asset
        self.find_calls = []

    def find_element(self, path, **kwargs):
        self.find_calls.append((path, kwargs))
        return (100, 100) if path == self.visible_asset else None


def _handler():
    return object.__new__(mirror_module.Mirror)


def test_battle_statistics_uses_global_search_and_result_threshold(monkeypatch):
    fake_auto = _RewardAuto()
    monkeypatch.setattr(mirror_module, "auto", fake_auto)

    assert _handler()._finish_battle_statistics() is True
    assert fake_auto.find_calls == [
        (
            "mirror/claim_reward/battle_statistics_assets.png",
            {
                "threshold": mirror_module.Mirror.BATTLE_STATISTICS_THRESHOLD,
                "model": "aggressive",
            },
        )
    ]
    assert fake_auto.click_calls == [
        (
            "mirror/claim_reward/claim_rewards_assets.png",
            {
                "threshold": mirror_module.Mirror.CLAIM_REWARDS_RESULT_THRESHOLD,
                "model": "aggressive",
            },
        )
    ]


def test_battle_statistics_keeps_coordinate_fallback(monkeypatch):
    fake_auto = _RewardAuto(reward_click_succeeds=False)
    monkeypatch.setattr(mirror_module, "auto", fake_auto)
    monkeypatch.setattr(mirror_module.ImageUtils, "load_image", lambda _path: object())
    monkeypatch.setattr(mirror_module.ImageUtils, "get_bbox", lambda _image: (100, 200, 300, 400))

    assert _handler()._finish_battle_statistics() is True
    assert fake_auto.coordinate_clicks == [(200.0, 300.0)]


def test_battle_statistics_absence_does_not_click(monkeypatch):
    fake_auto = _RewardAuto(statistics_visible=False)
    monkeypatch.setattr(mirror_module, "auto", fake_auto)

    assert _handler()._finish_battle_statistics() is False
    assert fake_auto.click_calls == []
    assert fake_auto.coordinate_clicks == []


def test_claim_forfeit_uses_state_specific_threshold(monkeypatch):
    fake_auto = _RewardAuto()
    monkeypatch.setattr(mirror_module, "auto", fake_auto)

    assert _handler()._click_claim_forfeit() is True
    assert fake_auto.click_calls == [
        (
            "mirror/claim_reward/claim_forfeit_assets.png",
            {
                "threshold": mirror_module.Mirror.CLAIM_FORFEIT_THRESHOLD,
                "model": "normal",
                "take_screenshot": True,
            },
        )
    ]


def test_reward_loading_pauses_until_monotonic_timeout(monkeypatch):
    fake_auto = _LoadingAuto("base/waiting_assets.png")
    now = 10.0
    monkeypatch.setattr(mirror_module, "auto", fake_auto)
    monkeypatch.setattr(mirror_module.time, "monotonic", lambda: now)

    handler = _handler()
    assert handler._reward_loading_state(None) == (True, 10.0, False)

    now = 99.9
    assert handler._reward_loading_state(10.0) == (True, 10.0, False)

    now = 100.0
    assert handler._reward_loading_state(10.0) == (True, 10.0, True)
    assert fake_auto.find_calls[0] == (
        "base/waiting_assets.png",
        {
            "threshold": mirror_module.Mirror.REWARD_LOADING_THRESHOLD,
            "model": "normal",
        },
    )


def test_reward_loading_accepts_second_asset_and_resets_when_absent(monkeypatch):
    fake_auto = _LoadingAuto("base/waiting_2_assets.png")
    monkeypatch.setattr(mirror_module, "auto", fake_auto)
    monkeypatch.setattr(mirror_module.time, "monotonic", lambda: 20.0)

    assert _handler()._reward_loading_state(None) == (True, 20.0, False)
    assert [path for path, _kwargs in fake_auto.find_calls] == [
        "base/waiting_assets.png",
        "base/waiting_2_assets.png",
    ]

    fake_auto.visible_asset = None
    assert _handler()._reward_loading_state(20.0) == (False, None, False)

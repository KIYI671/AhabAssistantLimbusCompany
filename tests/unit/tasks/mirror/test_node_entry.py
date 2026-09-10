import importlib

search_road = importlib.import_module("tasks.mirror.search_road")


class _NodeEntryAuto:
    def __init__(self, successful_position=None):
        self.successful_position = successful_position
        self.current_position = None
        self.clicked_positions = []
        self.screenshot_intervals = []
        self.bus_fallback_calls = 0
        self.clock = 0.0

    def mouse_click(self, x, y):
        self.current_position = (x, y)
        self.clicked_positions.append(self.current_position)

    def take_screenshot(self, interval=None):
        self.screenshot_intervals.append(interval)
        self.clock += interval
        return object()

    def click_element(self, path):
        if path == "mirror/road_in_mir/enter_assets.png":
            return self.current_position == self.successful_position
        if path == "mirror/mybus_default_distance.png":
            self.bus_fallback_calls += 1
            return False
        raise AssertionError(path)


class _CandidateAuto:
    def __init__(self, bus_positions):
        self.bus_positions = iter(bus_positions)
        self.current_bus_position = None
        self.screenshot_intervals = []

    def take_screenshot(self, interval=None):
        self.screenshot_intervals.append(interval)
        self.current_bus_position = next(self.bus_positions)
        return object()

    def find_element(self, path):
        assert path == "mirror/mybus_default_distance.png"
        return self.current_bus_position


def _prepare_map(monkeypatch, successful_position):
    fake_auto = _NodeEntryAuto(successful_position)
    monkeypatch.setattr(search_road, "auto", fake_auto)
    monkeypatch.setattr(search_road.time, "monotonic", lambda: fake_auto.clock)
    mirror_map = search_road.MirrorMap()
    mirror_map.floor_map = ["D", "M"]
    candidates = [("U", (10, 10)), ("M", (20, 20)), ("D", (30, 30))]
    monkeypatch.setattr(mirror_map, "_get_next_positions", lambda _direction: candidates)
    return mirror_map, fake_auto


def test_planned_direction_enters_without_trying_other_nodes(monkeypatch):
    mirror_map, fake_auto = _prepare_map(monkeypatch, successful_position=(10, 10))

    assert mirror_map.enter_next_node("U") is True
    assert fake_auto.clicked_positions == [(10, 10)]
    assert fake_auto.screenshot_intervals == [0.15]
    assert mirror_map.floor_map == ["D", "M"]


def test_alternate_direction_clears_stale_route_cache(monkeypatch):
    mirror_map, fake_auto = _prepare_map(monkeypatch, successful_position=(20, 20))

    assert mirror_map.enter_next_node("U") is True
    assert fake_auto.clicked_positions == [(10, 10), (20, 20)]
    assert fake_auto.screenshot_intervals == [0.15] * 12
    assert mirror_map.floor_map == []


def test_all_candidates_fail_before_preserving_bus_and_caller_fallback(monkeypatch):
    mirror_map, fake_auto = _prepare_map(monkeypatch, successful_position=None)

    assert mirror_map.enter_next_node("U") is False
    assert fake_auto.clicked_positions == [(10, 10), (20, 20), (30, 30)]
    assert fake_auto.screenshot_intervals == [0.15] * 32
    assert fake_auto.bus_fallback_calls == 1
    assert mirror_map.floor_map == ["D", "M"]


def test_candidate_positions_use_fast_fresh_frames_and_preferred_direction_first(monkeypatch):
    fake_auto = _CandidateAuto([None, (704, 396)])
    monkeypatch.setattr(search_road, "auto", fake_auto)
    monkeypatch.setattr(search_road.cfg, "set_win_size", 1080)
    mirror_map = search_road.MirrorMap()

    assert mirror_map._get_next_positions("U") == [
        ("U", (1079.0, 96.0)),
        ("M", (1079.0, 433.5)),
        ("D", (1079.0, 733.5)),
    ]
    assert fake_auto.screenshot_intervals == [0.15, 0.15]

"""回归测试：狂气换体的葛朗台模式（下一点体力恢复时间超过 5 分 20 秒才换体）。

旧实现用 ``s.split(":")`` 后取 ``l[0][-2:]`` 当分钟数，只有当 OCR 恰好把分钟读成两位
（``05:32``）时才解析成功；实战日志里的常见结果（``Enkephalinrecovered in5:55``、
``...inD5:41``、``...in 5:44``）都会让 ``int()`` 抛异常，再被 ``except`` 吞掉返回 False，
而 False 在等待循环里等于“还没到时机”，于是换体流程会无限等待（实测卡了 3 分半仍未换体）。
另外 ``minute >= 5 and seconds >= 20`` 也不是“超过 5 分 20 秒”（``6:05`` 会被判为不合格）。

这里用实测日志里的 OCR 原文覆盖解析与等待行为。
"""

import pytest

from tasks.base import make_enkephalin_module as enkephalin_module

LUNACY_ASSET = "enkephalin/lunacy_assets.png"
# 实测：1080 画布上 lunacy_assets 的匹配中心
LUNACY_CENTER = (825, 437)
# 一次等待循环里允许的识别次数上限，超出说明等待没有正常结束
MAX_READS = 12


class LoopDetected(RuntimeError):
    """等待循环没有结束。"""


class FakeClock:
    """让等待循环的时间可控：每读一次时间前进 1 秒。"""

    def __init__(self):
        self.now = 0.0

    def time(self):
        self.now += 1.0
        return self.now

    def sleep(self, seconds):
        self.now += seconds


class FakeDevice:
    """只提供 get_the_timing 需要的两个识别接口，按脚本返回 OCR 结果。"""

    def __init__(self, readings):
        self.readings = list(readings)
        self.read_count = 0

    def find_element(self, target, *args, **kwargs):
        return LUNACY_CENTER if target == LUNACY_ASSET else None

    def find_text_element(self, target, my_crop=None, only_text=False, **kwargs):
        # 恢复时间必须限定在狂气图标下方的区域里按纯文本识别，否则会读到界面其它数字
        assert my_crop is not None and only_text, "体力恢复时间必须在指定区域内按纯文本识别"
        self.read_count += 1
        if self.read_count > MAX_READS:
            raise LoopDetected("葛朗台模式等待没有结束")
        return self.readings[min(self.read_count - 1, len(self.readings) - 1)]


@pytest.fixture
def patch_loop(monkeypatch):
    """固定等待循环的时间与休眠，避免测试真的等待。"""

    def _patch(readings):
        device = FakeDevice(readings)
        clock = FakeClock()
        monkeypatch.setattr(enkephalin_module, "auto", device)
        monkeypatch.setattr(enkephalin_module, "time", clock)
        monkeypatch.setattr(enkephalin_module, "sleep", clock.sleep)
        return device

    return _patch


# 实测日志（2026-09-19 / 2026-09-20 两次狂气换体）里的 OCR 原文 -> 下一点体力恢复秒数
REAL_OCR_READINGS = [
    (("Enkephalinrecovered in05:32",), 5 * 60 + 32),
    (("Enkephalinrecoveredin5:55",), 5 * 60 + 55),
    (("Enkephalinrecovered in5:48",), 5 * 60 + 48),
    (("Enkephalinrecovered inD5:35",), 5 * 60 + 35),
    (("一", "EnkephalinrecoveredinD5:41"), 5 * 60 + 41),
    (("1", "Enkephalin recovered in1:04"), 64),
    (("Enkephalin recovered in D2:18",), 2 * 60 + 18),
    (("Enkephalinrecovered in02:14",), 2 * 60 + 14),
    (("Enkephalinrecovered inD0:58",), 58),
    (("Enkephalin recovered in D0:07",), 7),
    (("EnkephalinrecoveredinD0:02",), 2),
]


@pytest.mark.parametrize("ocr_result,expected", REAL_OCR_READINGS)
def test_get_the_timing_parses_real_ocr_results(patch_loop, ocr_result, expected):
    patch_loop([ocr_result])

    assert enkephalin_module.get_the_timing() == expected


@pytest.mark.parametrize(
    "ocr_result",
    [
        False,  # 该区域没有识别到任何文本
        ("Enkephalin recovered in",),
        ("一",),
        ("Enkephalin recovered in MAX",),
    ],
)
def test_get_the_timing_returns_none_when_unreadable(patch_loop, ocr_result):
    patch_loop([ocr_result])

    assert enkephalin_module.get_the_timing() is None


def test_grandet_mode_waits_until_recovery_time_is_high_enough(patch_loop):
    """实测失败场景：恢复时间从 2:18 倒数到重新计时后变高，此时才应该换体。"""
    device = patch_loop(
        [
            ("EnkephalinrecoveredinD2:18",),
            ("Enkephalinrecovered inD2:08",),
            ("Enkephalinrecovered in5:55",),
            ("Enkephalinrecovered in5:48",),
        ]
    )

    enkephalin_module.wait_for_grandet_mode()

    # 读到 5:55 时就应该结束等待，不该继续读到后面的 5:48
    assert device.read_count == 3


def test_grandet_mode_accepts_recovery_time_above_five_twenty(patch_loop):
    """阈值是“超过 5 分 20 秒”：6:05 这种分钟数已达标、秒数不达 20 的时间也算达标。"""
    patch_loop([("Enkephalinrecovered in6:05",)])

    enkephalin_module.wait_for_grandet_mode()


def test_grandet_mode_keeps_waiting_below_threshold(patch_loop):
    """5:19 未达标，要等到重新计时（5:21）后再换体。"""
    device = patch_loop(
        [
            ("Enkephalinrecovered in5:19",),
            ("Enkephalinrecovered in0:01",),
            ("Enkephalinrecovered in5:21",),
        ]
    )

    enkephalin_module.wait_for_grandet_mode()

    assert device.read_count == 3


def test_grandet_mode_gives_up_when_timing_never_readable(patch_loop, monkeypatch):
    """恢复时间一直识别不出来时不能无限等待（旧实现在这里会一直卡住）。"""
    monkeypatch.setattr(enkephalin_module, "GRANDET_MAX_WAIT_SECONDS", 10)
    device = patch_loop([False])

    enkephalin_module.wait_for_grandet_mode()

    assert device.read_count <= MAX_READS

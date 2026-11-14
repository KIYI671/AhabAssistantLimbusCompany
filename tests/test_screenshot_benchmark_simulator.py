"""模拟器（含 PlayCover）下截图测试必须可用。

线上问题：设置里的「截图测试」在 PlayCover 模式下总是失败。

原因：screenshot_benchmark() 无条件先检查桌面窗口句柄——
    screen.handle.init_handle()
    if screen.handle.hwnd == 0: return False, 0.0
而模拟器没有桌面窗口，hwnd 恒为 0，于是在真正截图前就直接返回失败。
截图本身（ADB / MaaTools）其实是好的。

顺带修复：此前即使 take_screenshot() 返回 None 也会计入耗时并报成功。
"""

from unittest.mock import MagicMock, patch

from module.automation.screenshot import ScreenShot


def test_benchmark_works_in_simulator_without_window_handle():
    """模拟器模式不该依赖窗口句柄。"""
    fake_image = MagicMock()
    with patch("module.automation.screenshot.cfg") as cfg, \
         patch("module.automation.screenshot.screen") as screen, \
         patch.object(ScreenShot, "take_screenshot", return_value=fake_image) as shot:
        cfg.simulator = True
        screen.handle.hwnd = 0  # 模拟器下没有窗口句柄

        ok, elapsed = ScreenShot.screenshot_benchmark(test_time=3)

    assert ok is True, "模拟器模式下截图测试应成功"
    assert shot.call_count == 3
    assert elapsed >= 0


def test_benchmark_still_requires_window_on_desktop():
    """桌面版仍需确认窗口存在，缺失时应明确失败。"""
    with patch("module.automation.screenshot.cfg") as cfg, \
         patch("module.automation.screenshot.screen") as screen, \
         patch.object(ScreenShot, "take_screenshot") as shot:
        cfg.simulator = False
        screen.handle.hwnd = 0

        ok, elapsed = ScreenShot.screenshot_benchmark(test_time=3)

    assert ok is False
    assert elapsed == 0.0
    shot.assert_not_called()


def test_benchmark_fails_when_screenshot_returns_none():
    """截图返回 None 时不能算成功（此前会静默通过）。"""
    with patch("module.automation.screenshot.cfg") as cfg, \
         patch("module.automation.screenshot.screen") as screen, \
         patch.object(ScreenShot, "take_screenshot", return_value=None):
        cfg.simulator = True

        ok, elapsed = ScreenShot.screenshot_benchmark(test_time=3)

    assert ok is False, "拿不到画面时应报失败"
    assert elapsed == 0.0

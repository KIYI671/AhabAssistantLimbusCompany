"""PlayCover 触摸坐标越界时必须夹取，载荷不合法只能按输入失败上报。

TUCH 载荷里的坐标是 u16：拖拽终点越过屏幕边缘（负数）会让打包抛 struct.error，
原来既没有夹取、`_run` 也不兜这类异常，整条手势直接把任务打断（实机复现：
``mouse_drag_down(200, 520, reverse=-2)`` 终点 y=-80）。这里锁定夹取与失败上报。
"""

import struct
import threading

import pytest

from module.automation.input_handlers.macos.playcover_control import (
    _MAGIC_TUCH,
    _PHASE_MOVE,
    MaaToolsError,
    PlayCoverControl,
)


def _control() -> PlayCoverControl:
    ctrl = object.__new__(PlayCoverControl)  # 不建立真实连接
    ctrl._device_size = (3840, 2160)
    return ctrl


def test_canvas_to_device_clamps_out_of_canvas_points():
    ctrl = _control()
    canvas_w, canvas_h = ctrl._canvas_size()
    device_w, device_h = 3840, 2160

    assert ctrl.canvas_to_device(-80, -200) == (0, 0)
    assert ctrl.canvas_to_device(canvas_w + 500, canvas_h + 500) == (device_w, device_h)
    # 画布内的点照常换算：四角与中点仍是边界/中点
    assert ctrl.canvas_to_device(0, 0) == (0, 0)
    assert ctrl.canvas_to_device(canvas_w, canvas_h) == (device_w, device_h)
    assert ctrl.canvas_to_device(canvas_w // 2, canvas_h // 2) == (device_w // 2, device_h // 2)


def test_touch_payload_stays_in_u16_range():
    ctrl = _control()
    frames = []
    ctrl._send_frame = lambda payload: frames.append(payload)
    ctrl._run = lambda action, func: func()

    ctrl._touch(_PHASE_MOVE, -80, 5000)  # 越过屏幕左上/下方
    ctrl._touch(_PHASE_MOVE, 100, 200)

    assert len(frames) == 2
    for payload in frames:
        assert payload[:4] == _MAGIC_TUCH
        x, y = struct.unpack(">HH", payload[5:9])
        assert 0 <= x <= 65535
        assert 0 <= y <= 65535


@pytest.mark.parametrize("error", [struct.error("bad"), ValueError("bad")])
def test_run_reports_bad_payload_as_input_failure(error):
    ctrl = _control()
    ctrl._io_lock = threading.RLock()
    ctrl._sock = object()  # 视为已连接，不再重连

    def _raise():
        raise error

    with pytest.raises(MaaToolsError):
        ctrl._run("触摸", _raise)

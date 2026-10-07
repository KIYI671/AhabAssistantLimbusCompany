"""为共享 Linux 手势提供经过授权的 Wayland 鼠标和键盘操作。"""

import time

from module.game_and_screen import screen

from .wayland_portal import portal_input


class PortalBackend:
    def __init__(self):
        self._position = None

    def prepare(self, monitors):
        portal_input.prepare(monitors)
        self._position = None

    def position(self):
        # XWayland 指针位置只用于操作后尽力恢复，不用于定位游戏目标。
        return screen.handle.get_pointer_position()

    def moveTo(self, x, y, duration=0):
        target = (int(x), int(y))
        origin = self._position
        steps = max(1, min(60, int(duration / 0.02))) if origin is not None and duration > 0 else 1
        for step in range(1, steps + 1):
            point = target if steps == 1 else (
                round(origin[0] + (target[0] - origin[0]) * step / steps),
                round(origin[1] + (target[1] - origin[1]) * step / steps),
            )
            portal_input.move(*point)
            self._position = point
            if duration > 0:
                time.sleep(duration / steps)

    def mouseDown(self):
        portal_input.button(True)

    def mouseUp(self):
        time.sleep(0.02)
        portal_input.button(False)

    def click(self, x, y):
        self.moveTo(x, y)
        time.sleep(0.05)
        try:
            self.mouseDown()
            time.sleep(0.02)
        finally:
            self.mouseUp()
        time.sleep(0.05)

    def scroll(self, direction):
        portal_input.scroll(direction)

    def press(self, key):
        portal_input.hotkey(key)

    def hotkey(self, *keys):
        portal_input.hotkey(*keys)

    def typewrite(self, text):
        portal_input.type_text(text)


portal_backend = PortalBackend()

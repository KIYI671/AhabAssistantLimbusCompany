"""PlayCover (MaaTools) 设备控制。

通过 PlayCover 内嵌暴露的 MaaTools TCP 服务操作 iOS 版 Limbus Company。

协议实现见 hguandl/PlayTools 的 ``MaaTools`` 分支（随社区分支 hguandl/PlayCover
分发，协议版本 4），可用命令：``SCRN``/``BGR\\x01`` 截图、``SIZE`` 尺寸、
``RECT`` 窗口矩形、``BNDL`` 包名、``VERN`` 版本、``TUCH`` 触摸、``TERM`` 退出，
没有键盘/文本指令；Enter/P/ESC 改走 ``macos_keyboard``：游戏本体在 PlayTools 注入的
进程里直接读硬件键盘，用 ``CGEventPostToPid`` 把按键投递给该进程即可（不需要窗口焦点），
其余按键与文本仍走触摸兜底；
- 连接后客户端先发 4 字节魔数 ``MAA\\0``，服务端回 ``OKAY``；
- 之后每条命令 = 2 字节大端长度 + 载荷；载荷前 4 字节为命令魔数；
- 截图实际尺寸 = 游戏窗口像素（PlayCover 按设备型号/缩放渲染，可能带 2x
  或任意缩放，如 4K 设备窗口实测 2956x1662）。本类统一把截图缩放到
  ``set_win_size`` 的 16:9 画布（1920x1080 等，即设备点空间）再交给上层
  模板匹配，坐标因此都以该画布为准；
- 触摸 TUCH 按设备原生像素发送：服务端把 u16 坐标除以 nativeScale 落到
  设备点，因此发 TUCH 前把画布坐标按 SIZE 命令返回的设备原生尺寸放大
  （4K 设备即 x2，1080p 设备即 x1）；
- 触摸：TUCH + phase(0 down/1 move/3 up) + u16 大端 x/y + contact；
- 截图使用 BGR 命令（vImage 路径，自上而下，无翻转歧义）：
  返回 u32 宽 + u32 高 + u32 长度 + BGR888 数据。

MaaTools 服务由 PlayCover 中该游戏设置里的 MaaTools 开关启用（PlayTools 的
``PlaySettings.maaTools`` / ``maaToolsPort``，端口默认 1717，随应用设置保存）；
服务就绪后游戏窗口标题会出现 ``[localhost:端口]``。
"""

import random
import socket
import struct
import threading
from time import sleep, time

import cv2
import numpy as np
from PIL import Image

from module.config import cfg
from module.logger import log

from .. import AbstractInput
from ..scroll_swipe import build_scroll_swipe_plan
from . import macos_keyboard

PLAYCOVER_SIMULATOR_TYPE = 20
"""config.yaml 中 simulator_type 的值：PlayCover (MaaTools)。"""

DEFAULT_PORT = 1717
CONNECT_TIMEOUT = 5.0
OP_TIMEOUT = 15.0
RECONNECT_LIMIT = 3

# 命令魔数（与 MaaTools.swift 一致）
_MAGIC_MAA = b"\x4d\x41\x41\x00"  # MAA\0
_MAGIC_TERM = b"TERM"
_MAGIC_TUCH = b"TUCH"
_MAGIC_SIZE = b"SIZE"
_MAGIC_BGR = b"BGR\x01"

_PHASE_DOWN = 0
_PHASE_MOVE = 1
_PHASE_UP = 3

# 双指捏合（触摸端模拟滚轮缩放）的几何参数，单位 = 画布宽度的比例。
_PINCH_WIDE_RATIO = 0.30
_PINCH_NARROW_RATIO = 0.10
_PINCH_STEPS = 16
_PINCH_STEP_INTERVAL = 0.02

# 编队列表滚动参数，单位 = 1080p 画布像素，随 set_win_size 缩放。
_TEAM_SCROLL_POINT_SPACING_AT_1080P = 8
_TEAM_SCROLL_MAX_STEPS = 40
_TEAM_SCROLL_STEP_INTERVAL = 0.03
_TEAM_SCROLL_SETTLE_DURATION = 0.3
_TEAM_SCROLL_SETTLE_STEP = 0.05


class MaaToolsError(RuntimeError):
    """与 MaaTools 服务通信失败"""


class PlayCoverControl(AbstractInput):
    """PlayCover (MaaTools) 输入/截图设备。

    与 MumuControl/SimulatorControl 一致：普通类 + 类属性 connection_device。
    ``clean_connect()`` 置空后再次 ``PlayCoverControl()`` 会重新走 __init__
    并注册新连接（不要使用 SingletonMeta，否则重建时 __init__ 不会执行）。
    MaaTools 服务绑定在 PlayCover 游戏窗口侧，游戏必须已启动并注入
    MaaTools（窗口标题带 ``[localhost:port]``）才能连接。
    本类不负责拉起游戏/模拟器，``start_game`` 仅等待服务就绪并给出指引。
    """

    connection_device: "PlayCoverControl | None" = None
    _connection_lock = threading.RLock()

    supports_keyboard = True
    """MaaTools 协议没有键盘指令，但游戏本体直接读硬件键盘：按键经 ``macos_keyboard``
    用 CGEventPostToPid 注入游戏进程，不需要窗口焦点（见该模块说明）。"""

    keyboard_keys = frozenset(macos_keyboard.KEYCODES)
    """只保证这些键（enter/p/esc）送得到游戏；其余键（方向键等）仍走触摸兜底。"""

    def supports_key(self, key: str) -> bool:
        """按键能否送达游戏：仅 ``keyboard_keys``、有辅助功能权限且能定位游戏进程，否则触摸兜底。"""
        if key not in self.keyboard_keys or not macos_keyboard.available():
            return False
        return macos_keyboard.game_pid(self.host, self.port) is not None

    @classmethod
    def get_connection(cls) -> "PlayCoverControl":
        """返回唯一连接；不存在时新建（与 MumuControl/SimulatorControl 一致）。"""
        with cls._connection_lock:
            if cls.connection_device is None:
                cls()
            return cls.connection_device

    @classmethod
    def clean_connect(cls) -> None:
        with cls._connection_lock:
            if cls.connection_device is None:
                return
            try:
                cls.connection_device._close()
            except Exception as e:
                log.debug(f"清理 PlayCover 连接失败: {e}")
            cls.connection_device = None

    def __init__(self) -> None:
        super().__init__()
        with PlayCoverControl._connection_lock:
            if PlayCoverControl.connection_device is None:
                self.host = str(cfg.simulator_host or "127.0.0.1")
                port = int(cfg.simulator_port or 0)
                self.port = port if port > 0 else DEFAULT_PORT
                self._sock: socket.socket | None = None
                self._io_lock = threading.RLock()
                # 设备原生像素尺寸（SIZE 命令返回，如 3840x2160）。TUCH 按该
                # 空间发送（服务端会除以 nativeScale），截图则统一缩放为
                # set_win_size 画布；点击坐标需画布 -> 设备像素映射。None=未查询。
                self._device_size: tuple[int, int] | None = None
                PlayCoverControl.connection_device = self
                log.info(f"PlayCover (MaaTools) 控制器就绪: {self.host}:{self.port}")
                # AALC 启动（导入期建连接）就预热按键注入，见 macos_keyboard.warm_up：
                # 游戏没启动时跳过，下次 init_game 重建连接时会再试一次。
                macos_keyboard.warm_up_in_background(self.host, self.port)

    # ---------- 底层连接 ----------

    def _connect(self) -> None:
        sock = socket.create_connection((self.host, self.port), timeout=CONNECT_TIMEOUT)
        sock.settimeout(OP_TIMEOUT)
        sock.sendall(_MAGIC_MAA)
        reply = self._recv_exact(sock, 4)
        if reply != b"OKAY":
            sock.close()
            raise MaaToolsError(f"MaaTools 握手失败: 期望 OKAY, 收到 {reply!r}")
        self._sock = sock
        self._device_size = None  # 连接重建后重新查询
        log.debug(f"已连接 MaaTools 服务 {self.host}:{self.port}")

    def _close(self) -> None:
        sock, self._sock = self._sock, None
        if sock is not None:
            try:
                sock.close()
            except OSError:
                pass

    @staticmethod
    def _recv_exact(sock: socket.socket, length: int) -> bytes:
        chunks = bytearray()
        while len(chunks) < length:
            chunk = sock.recv(length - len(chunks))
            if not chunk:
                raise MaaToolsError("MaaTools 连接被服务端关闭")
            chunks.extend(chunk)
        return bytes(chunks)

    def _send_frame(self, payload: bytes) -> None:
        frame = struct.pack(">H", len(payload)) + payload
        self._sock.sendall(frame)

    def _ensure_connected(self) -> None:
        if self._sock is not None:
            return
        for attempt in range(1, RECONNECT_LIMIT + 1):
            try:
                self._connect()
                return
            except OSError as e:
                log.warning(f"连接 MaaTools 服务失败(第 {attempt}/{RECONNECT_LIMIT} 次): {e}")
                sleep(1.0 * attempt)
        raise MaaToolsError(f"无法连接 MaaTools 服务 {self.host}:{self.port}，请确认游戏已在 PlayCover 中启动且启用 MaaTools")

    def _run(self, action: str, func):
        """执行协议操作：断线自动重连一次后重试。"""
        try:
            with self._io_lock:
                self._ensure_connected()
                try:
                    return func()
                except (OSError, MaaToolsError) as e:
                    log.debug(f"{action}失败({e})，尝试重连后重试")
                    self._close()
                    self._ensure_connected()
                    return func()
        except (OSError, MaaToolsError, ValueError, struct.error) as e:
            # 参数/载荷本身不合法（如坐标超量程）时不该重连，直接按输入失败上报。
            raise MaaToolsError(f"{action}失败: {e}") from e

    # ---------- 设备能力 ----------

    def check_game_alive(self) -> bool:
        """MaaTools 端口可握手即代表游戏窗口在运行。"""
        try:
            probe = socket.create_connection((self.host, self.port), timeout=2.0)
        except OSError:
            return False
        try:
            probe.sendall(_MAGIC_MAA)
            return self._recv_exact(probe, 4) == b"OKAY"
        except Exception:
            return False
        finally:
            probe.close()

    def start_game(self) -> None:
        """等待 MaaTools 服务就绪。

        AALC 不负责在 macOS 上拉起 PlayCover 游戏：请先在 PlayCover 中
        手动启动 Limbus Company，窗口标题出现 [localhost:端口] 后即可。
        """
        deadline = time() + max(1, int(cfg.start_emulator_timeout))
        waited = 0.0
        while time() < deadline:
            if self.check_game_alive():
                log.info("检测到 PlayCover 中的游戏已启动 (MaaTools 服务在线)")
                return
            if waited > 0 and int(waited) % 10 == 0:
                log.info(f"等待游戏启动（PlayCover + MaaTools）... {int(waited)}s")
            sleep(1)
            waited += 1
        raise MaaToolsError(
            "等待游戏启动超时：请在 PlayCover 中手动启动 Limbus Company，"
            f"并确认其已启用 MaaTools（窗口标题显示 [localhost:{self.port}]）"
        )

    def close_current_app(self) -> None:
        """向 MaaTools 发送 TERM，关闭当前游戏进程。"""

        def _term():
            self._send_frame(_MAGIC_TERM)

        try:
            self._run("关闭游戏", _term)
        except MaaToolsError as e:
            log.error(f"关闭游戏失败: {e}")

    def close_simulator(self) -> None:
        log.info("PlayCover 无独立模拟器进程；如需结束游戏请使用“退出游戏”动作")

    def _query_device_size(self) -> tuple[int, int]:
        """查询设备原生像素尺寸（SIZE 命令，u16 宽 + u16 高）。"""

        def _ask():
            self._send_frame(_MAGIC_SIZE)
            reply = self._recv_exact(self._sock, 4)
            width, height = struct.unpack(">HH", reply)
            if width == 0 or height == 0:
                raise MaaToolsError(f"MaaTools 返回非法屏幕尺寸: {reply!r}")
            return width, height

        width, height = self._run("查询屏幕尺寸", _ask)
        self._device_size = (width, height)
        log.debug(f"MaaTools 设备原生像素尺寸: {width}x{height}")
        return width, height

    def _device_pixel_size(self) -> tuple[int, int]:
        """设备原生像素尺寸；未查询时先查询（断线重建后缓存自动失效）。"""
        if self._device_size is None:
            self._query_device_size()
        assert self._device_size is not None
        return self._device_size

    @staticmethod
    def _canvas_size() -> tuple[int, int]:
        """set_win_size 对应的 16:9 画布尺寸（如 1080 -> (1920, 1080)）。

        上层模板匹配、裁切与坐标均以该画布为基准（与 Windows/模拟器一致）。
        """
        win_size = max(int(cfg.set_win_size or 0), 1)
        return win_size * 16 // 9, win_size

    def screenshot(self) -> Image.Image:
        """截取游戏画面（BGR 命令，窗口实际像素）。

        返回前把窗口实际像素统一缩放到 ``set_win_size`` 的 16:9 画布，
        供上层按固定分辨率做模板匹配；触摸坐标由画布映射到设备原生像素
        （SIZE 命令尺寸）后发送（见 ``_touch``）。
        """

        def _capture():
            self._send_frame(_MAGIC_BGR)
            header = self._recv_exact(self._sock, 12)
            width, height, length = struct.unpack(">III", header)
            if width == 0 or height == 0 or length == 0:
                raise MaaToolsError("MaaTools 截图返回空数据")
            raw = self._recv_exact(self._sock, length)
            expected = 3 * width * height
            if len(raw) < expected:
                raise MaaToolsError(f"截图数据不完整: {len(raw)}/{expected}")
            return width, height, raw[:expected]

        width, height, raw = self._run("截图", _capture)
        array = np.frombuffer(raw, dtype=np.uint8).reshape(height, width, 3)
        rgb = cv2.cvtColor(array, cv2.COLOR_BGR2RGB)
        canvas_w, canvas_h = self._canvas_size()
        if (width, height) != (canvas_w, canvas_h):
            interpolation = cv2.INTER_AREA if width > canvas_w else cv2.INTER_LINEAR
            rgb = cv2.resize(rgb, (canvas_w, canvas_h), interpolation=interpolation)
        return Image.fromarray(rgb)

    # ---------- 坐标换算（逻辑画布 <-> 设备原生像素） ----------
    # 所有 MaaTools 坐标操作统一经 canvas_to_device/device_to_canvas 换算：
    # 截图/模板匹配等业务坐标以 set_win_size 16:9 逻辑画布为准（1080p 等），
    # TUCH 等线上协议按设备原生像素收发（服务端会除以 nativeScale）。

    def canvas_to_device(self, x: float, y: float) -> tuple[int, int]:
        """逻辑画布坐标 -> 设备原生像素坐标。

        画布 = set_win_size 的 16:9 帧(等价设备点空间); 设备原生像素由
        SIZE 命令给出(4K 设备 + cfg=1080 即 ×2, 原生 1080p 设备即 ×1)。
        越界坐标（拖拽终点越过屏幕边缘）夹到画布范围内：TUCH 坐标是 u16，
        负数会让整条手势在打包时抛错、把任务打断。
        """
        canvas_w, canvas_h = self._canvas_size()
        clamped_x = min(max(x, 0), canvas_w)
        clamped_y = min(max(y, 0), canvas_h)
        device_w, device_h = self._device_pixel_size()
        return (
            int(round(clamped_x * device_w / canvas_w)),
            int(round(clamped_y * device_h / canvas_h)),
        )

    def device_to_canvas(self, x: float, y: float) -> tuple[int, int]:
        """设备原生像素坐标 -> 逻辑画布坐标（canvas_to_device 的逆变换）。"""
        canvas_w, canvas_h = self._canvas_size()
        device_w, device_h = self._device_pixel_size()
        return (
            int(round(x * canvas_w / device_w)),
            int(round(y * canvas_h / device_h)),
        )

    # ---------- 触摸原语 ----------

    def _touch(self, phase: int, x: int, y: int, contact: int = 0) -> None:
        # 上层坐标为逻辑画布坐标, TUCH 需设备原生像素
        x, y = self.canvas_to_device(x, y)

        def _send():
            payload = (
                _MAGIC_TUCH
                + bytes([phase])
                + struct.pack(">HH", int(x), int(y))
                + bytes([contact])
            )
            self._send_frame(payload)

        self._run(f"触摸 phase={phase}", _send)

    def _touch_down(self, x, y, contact=0):
        self._touch(_PHASE_DOWN, x, y, contact)

    def _touch_move(self, x, y, contact=0):
        self._touch(_PHASE_MOVE, x, y, contact)

    def _touch_up(self, x, y, contact=0):
        self._touch(_PHASE_UP, x, y, contact)

    @staticmethod
    def _sleep_step(seconds: float) -> None:
        # 服务端按连接顺序逐条处理触摸，最小节奏 10ms 左右即可
        sleep(max(seconds, 0.005))

    # ---------- AbstractInput 接口（坐标 = 截图像素空间，恒等映射） ----------

    def mouse_click(self, x, y, times=1, move_back=False) -> bool:
        log.debug(f"点击位置:({x},{y})")
        for _ in range(max(1, int(times))):
            self._touch_down(x, y)
            self._touch_up(x, y)
            self._sleep_step(0.03)
        self.wait_pause()
        return True

    def mouse_click_blank(self, coordinate=(1, 1), times=1, move_back=False) -> bool:
        log.debug("点击（1，1）空白位置")
        x = coordinate[0] + random.randint(0, 10)
        y = coordinate[1] + random.randint(0, 10)
        for _ in range(max(1, int(times))):
            self.mouse_click(x, y)
        self.wait_pause()
        return True

    def mouse_drag(self, x, y, drag_time=0.2, dx=0, dy=0, move_back=True) -> None:
        """从 (x, y) 匀速拖动到 (x+dx, y+dy)，终点停留后抬起。"""
        end_x, end_y = x + dx, y + dy
        self._touch_down(x, y)
        steps = max(4, int((drag_time or 0.2) * 100))
        for step in range(1, steps + 1):
            ratio = step / steps
            self._touch_move(x + dx * ratio, y + dy * ratio)
            self._sleep_step(0.01)
        # 终点短暂停留，模拟按住效果
        hold = max(0.1, (drag_time or 0.2) * 0.3)
        self._sleep_step(hold)
        self._touch_up(end_x, end_y)

    def mouse_drag_down(self, x, y, reverse=1, move_back=True) -> None:
        scale = cfg.set_win_size / 1080
        self.mouse_drag(x, y, 0.4, 0, int(300 * scale * reverse))

    def mouse_swipe_for_scroll(self, x, y, duration=0.3, dx=0, dy=0, move_back=True) -> None:
        """快速滑动并立即抬起（规避长按判定）。"""
        plan = build_scroll_swipe_plan(x, y, dx, dy, duration)
        self._touch_down(x, y)
        elapsed = 0.0
        for point, move_duration in plan[1:]:
            elapsed += move_duration
            self._touch_move(*point)
            self._sleep_step(0.005)
        # 等待剩余滑动时间（duration 较长时间需要放慢）
        remaining = duration - elapsed
        if remaining > 0.01:
            self._sleep_step(min(remaining, 0.05))
        self._touch_up(x + dx, y + dy)

    def mouse_swipe_for_team_scroll(self, x, y, duration=0.3, dx=0, dy=0, move_back=True) -> None:
        """滚动编队列表：逐点慢速拖动 + 静止尾段。

        编队列表要按行滚动来定位队伍，而普通 ``mouse_swipe_for_scroll`` 只发 3 个
        触摸点：游戏会丢掉这些事件，列表几乎不动，或者滚动量随机（误差足以差一行，
        定位因此漂移）。这里以固定间隔逐点上报，让游戏逐帧跟手，滚动量可重复；
        松手前保持静止，让游戏把速度判定归零，避免惯性把位移冲成未知行数。
        """
        distance = (dx * dx + dy * dy) ** 0.5
        if distance == 0:
            return
        scale = cfg.set_win_size / 1080
        spacing = max(_TEAM_SCROLL_POINT_SPACING_AT_1080P * scale, 1.0)
        steps = min(max(int(distance / spacing), 1), _TEAM_SCROLL_MAX_STEPS)
        end_x, end_y = x + dx, y + dy

        self._touch_down(x, y)
        for step in range(1, steps + 1):
            ratio = step / steps
            self._touch_move(x + dx * ratio, y + dy * ratio)
            self._sleep_step(_TEAM_SCROLL_STEP_INTERVAL)
        # 静止尾段：反复上报终点，让游戏把速度判定归零，松手后不再惯性滚动。
        for _ in range(int(_TEAM_SCROLL_SETTLE_DURATION / _TEAM_SCROLL_SETTLE_STEP)):
            self._sleep_step(_TEAM_SCROLL_SETTLE_STEP)
            self._touch_move(end_x, end_y)
        self._touch_up(end_x, end_y)

    def mouse_scroll(self, direction: int = -3) -> bool:
        """触摸端没有滚轮：用双指捏合模拟镜牢地图缩放。

        协议依据 PlayTools ``MaaTools.swift`` 的 ``toucherDispatch``：TUCH 载荷末字节是
        contact 编号，``touchContexts[contact]`` 为每个 contact 维护独立的触摸 id，
        同时发 contact 0/1 即真正的双指手势。语义与 PC 滚轮一致（见 ``Input.mouse_scroll``）：
        ``direction <= 0`` 缩小 / 远离界面 = 双指靠拢，正数放大 = 双指分开。
        """
        canvas_w, canvas_h = self._canvas_size()
        center_x, center_y = canvas_w / 2, canvas_h / 2
        wide = canvas_w * _PINCH_WIDE_RATIO
        narrow = canvas_w * _PINCH_NARROW_RATIO
        start_gap, end_gap = (wide, narrow) if direction <= 0 else (narrow, wide)

        self._touch(_PHASE_DOWN, center_x - start_gap / 2, center_y, contact=0)
        self._touch(_PHASE_DOWN, center_x + start_gap / 2, center_y, contact=1)
        for index in range(1, _PINCH_STEPS + 1):
            gap = start_gap + (end_gap - start_gap) * index / _PINCH_STEPS
            self._touch(_PHASE_MOVE, center_x - gap / 2, center_y, contact=0)
            self._touch(_PHASE_MOVE, center_x + gap / 2, center_y, contact=1)
            self._sleep_step(_PINCH_STEP_INTERVAL)
        self._touch(_PHASE_UP, center_x - end_gap / 2, center_y, contact=0)
        self._touch(_PHASE_UP, center_x + end_gap / 2, center_y, contact=1)
        return True

    def mouse_to_blank(self, coordinate=(1, 1), move_back=False) -> None:
        # 触摸设备没有“鼠标移开”的概念
        return

    def mouse_drag_link(self, position: list, drag_time=0.15, move_back=False) -> None:
        """沿折线逐点拖动（拉链），最后抬起。

        段与段之间按距离插值补点：拉链是"按住连续划过"的手势，只发顶点会被游戏当成
        瞬移而整条丢弃（实机实测：只发顶点 → 卡行/守备行画面零变化、回合不开始；
        每段插值约 20 个中间点后 → 拉链生效、回合正常开始）。
        ``drag_time`` 视作每段的目标耗时，实际节奏 = drag_time / 该段补点数。
        """
        if not position:
            return
        points = [(int(round(pos[0])), int(round(pos[1]))) for pos in position]
        step_len = 10  # 画布像素：约每 10px 补一个中间点
        log.debug(f"开始拉链，{len(points)} 个顶点: {points}")
        self._touch_down(*points[0])
        sent = 1
        for start, end in zip(points, points[1:]):
            dist = max(abs(end[0] - start[0]), abs(end[1] - start[1]))
            steps = max(2, int(dist / step_len))
            step_sleep = max(0.006, (drag_time or 0.15) / steps)
            for index in range(1, steps + 1):
                self._touch_move(
                    start[0] + (end[0] - start[0]) * index / steps,
                    start[1] + (end[1] - start[1]) * index / steps,
                )
                self._sleep_step(step_sleep)
                sent += 1
        self._touch_up(*points[-1])
        log.debug(f"拉链结束：共发出 {sent} 个触摸点")

    def key_press(self, key: str):
        """向游戏进程注入一次按键（Enter/P/ESC）。

        MaaTools 协议没有键盘指令，但游戏直接读硬件键盘：经 ``macos_keyboard`` 用
        CGEventPostToPid 注入即可（游戏不必在前台）。不支持的键或缺少辅助功能权限时
        返回 False，由调用方走触摸兜底；调用前可用 ``supports_key`` 判断。
        """
        if key not in self.keyboard_keys:
            log.warning(
                f"PlayCover 不支持按键 {key}（仅 {sorted(self.keyboard_keys)}），该操作改用触摸兜底"
            )
            return False
        return macos_keyboard.press(key, self.host, self.port)

    def input_text(self, text: str):
        log.warning("PlayCover (MaaTools) 协议不支持文本输入，跳过: %s", text)

"""
自适应节流器 (Adaptive Throttle)

取代固定截图/点击间隔，根据操作实际耗时动态调整等待时间：
- 低负载时快速执行（间隔自动缩短）
- 高负载时自动降速（避免操作堆积）

设计原则：
- 零依赖（仅 Python stdlib）
- 线程安全（单例 Automation 内使用）
- 向后兼容：cfg 中仍保留 screenshot_interval / mouse_action_interval，
  仅当 AdaptiveThrottle 启用时才会覆盖固定值。
"""

import time
from dataclasses import dataclass, field
from typing import List


@dataclass
class ThrottleConfig:
    """节流配置

    Attributes:
        enabled: 是否启用自适应节流（默认 True）
        min_interval_ms: 最小操作间隔（毫秒），低负载时用此值
        max_interval_ms: 最大操作间隔（毫秒），高负载时退让至此
        window_size: 滑动窗口大小，用于计算平均耗时
    """
    enabled: bool = True
    min_interval_ms: int = 30
    max_interval_ms: int = 150
    window_size: int = 20

    def __post_init__(self):
        if self.min_interval_ms < 5:
            self.min_interval_ms = 5
        if self.max_interval_ms < self.min_interval_ms:
            self.max_interval_ms = self.min_interval_ms
        if self.window_size < 2:
            self.window_size = 2


class AdaptiveThrottle:
    """自适应节流器

    通过滑动窗口记录操作耗时，动态调整等待时间：
    - 操作快（<10ms）→ 按 min_interval 执行
    - 操作慢（>30ms）→ 自动延长间隔，最多到 max_interval
    """

    def __init__(self, config: ThrottleConfig | None = None):
        self._config = config or ThrottleConfig()
        self._recent_durations: List[float] = []
        self._last_operation_time: float = 0.0

    @property
    def config(self) -> ThrottleConfig:
        return self._config

    def wait(self) -> None:
        """自适应等待：根据当前负载决定等待时长"""
        if not self._config.enabled:
            return

        now = time.time()
        wait_ms = self._calculate_wait_ms()
        elapsed_ms = (now - self._last_operation_time) * 1000

        if elapsed_ms < wait_ms:
            actual_wait = (wait_ms - elapsed_ms) / 1000.0
            if actual_wait > 0:
                time.sleep(actual_wait)

        self._last_operation_time = time.time()

    def record_operation_duration(self, duration_seconds: float) -> None:
        """记录一次操作的耗时，用于滑动窗口计算"""
        self._recent_durations.append(duration_seconds)
        if len(self._recent_durations) > self._config.window_size:
            self._recent_durations = self._recent_durations[-self._config.window_size:]

    def _calculate_wait_ms(self) -> float:
        """计算期望等待时间（毫秒）"""
        if not self._config.enabled:
            return 0.0

        load_factor = self._calculate_load_factor()
        base = self._config.min_interval_ms
        extra = int(max(0, (load_factor - 0.3) * 80))
        return float(min(base + extra, self._config.max_interval_ms))

    def _calculate_load_factor(self) -> float:
        """计算系统负载因子（0~1）"""
        if len(self._recent_durations) < self._config.window_size:
            return 0.3  # 数据不足，默认低负载

        avg_duration = sum(self._recent_durations) / len(self._recent_durations)
        return min(avg_duration / 25.0, 1.0)

    def reset(self) -> None:
        """重置节流器状态"""
        self._recent_durations.clear()
        self._last_operation_time = 0.0

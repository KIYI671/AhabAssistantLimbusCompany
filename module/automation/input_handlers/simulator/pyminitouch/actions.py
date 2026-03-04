import time
import math
from contextlib import contextmanager

from . import config
from .connection import MNTConnection, MNTServer
from module.logger import log
from .. import insert_swipe


class CommandBuilder(object):
    """Build command str for minitouch.

    You can use this, to custom actions as you wish::

        with safe_connection(_DEVICE_ID) as connection:
            builder = CommandBuilder()
            builder.down(0, 400, 400, 50)
            builder.commit()
            builder.move(0, 500, 500, 50)
            builder.commit()
            builder.move(0, 800, 400, 50)
            builder.commit()
            builder.up(0)
            builder.commit()
            builder.publish(connection)

    use `d.connection` to get `connection` from device
    """

    # TODO (x, y) can not beyond the screen size
    def __init__(self):
        self._content = ""
        self._delay = 0

    def append(self, new_content):
        self._content += new_content + "\n"

    def commit(self):
        """add minitouch command: 'c\n'"""
        self.append("c")

    def wait(self, ms):
        """add minitouch command: 'w <ms>\n'"""
        self.append("w {}".format(ms))
        self._delay += ms

    def up(self, contact_id):
        """add minitouch command: 'u <contact_id>\n'"""
        self.append("u {}".format(contact_id))

    def down(self, contact_id, x, y, pressure):
        """add minitouch command: 'd <contact_id> <x> <y> <pressure>\n'"""
        self.append("d {} {} {} {}".format(contact_id, x, y, pressure))

    def move(self, contact_id, x, y, pressure):
        """add minitouch command: 'm <contact_id> <x> <y> <pressure>\n'"""
        self.append("m {} {} {} {}".format(contact_id, x, y, pressure))

    def publish(self, connection):
        """apply current commands (_content), to your device"""
        self.commit()
        final_content = self._content
        try:
            connection.send(final_content)
        except Exception as e:
            # 发送失败时记录错误并尝试断开连接，让上层重新初始化 minitouch
            log.error("minitouch publish failed, len=%s, err=%s", len(final_content), e)
            try:
                connection.disconnect()
            except Exception:
                pass
            # 向上抛出，让调用方决定是否重试整个手势
            raise
        time.sleep(self._delay / 1000 + config.DEFAULT_DELAY)
        self.reset()

    def reset(self):
        """clear current commands (_content)"""
        self._content = ""
        self._delay = 0


class MNTDevice(object):
    """minitouch device object

    Sample::

        device = MNTDevice(_DEVICE_ID)

        # It's also very important to note that the maximum X and Y coordinates may, but usually do not, match the display size.
        # so you need to calculate position by yourself, and you can get maximum X and Y by this way:
        print('max x: ', device.connection.max_x)
        print('max y: ', device.connection.max_y)

        # single-tap
        device.tap([(400, 600)])
        # multi-tap
        device.tap([(400, 400), (600, 600)])
        # set the pressure, default == 100
        device.tap([(400, 600)], pressure=50)

        # long-time-tap
        # for long-click, you should control time delay by yourself
        # because minitouch return nothing when actions done
        # we will never know the time when it finished
        device.tap([(400, 600)], duration=1000)
        time.sleep(1)

        # swipe
        device.swipe([(100, 100), (500, 500)])
        # of course, with duration and pressure
        device.swipe([(100, 100), (400, 400), (200, 400)], duration=500, pressure=50)

        # extra functions ( their names start with 'ext_' )
        device.ext_smooth_swipe([(100, 100), (400, 400), (200, 400)], duration=500, pressure=50, part=20)

        # stop minitouch
        # when it was stopped, minitouch can do nothing for device, including release.
        device.stop()
    """

    def __init__(self, device_id):
        self.device_id = device_id
        self.server = None
        self.connection = None
        self.start()
        self.real_width = 0
        self.real_height = 0

    def reset(self):
        self.stop()
        self.start()

    def start(self):
        # prepare for connection
        try:
            self.server = MNTServer(self.device_id)
        except AssertionError:
            import adbutils

            adbutils.adb.kill_server()
            self.start()
        except:
            self.start()
        # real connection
        self.connection = MNTConnection(self.server.port)

    def stop(self):
        self.connection.disconnect()
        self.server.stop()

    def tap(self, points, pressure=100, duration=None, no_up=None):
        """
        tap on screen, with pressure/duration

        :param points: list, looks like [(x1, y1), (x2, y2)]
        :param pressure: default == 100
        :param duration:
        :param no_up: if true, do not append 'up' at the end
        :return:
        """
        points = [list(map(int, each_point)) for each_point in points]

        _builder = CommandBuilder()
        for point_id, each_point in enumerate(points):
            x, y = each_point
            _builder.down(point_id, x, y, pressure)
        _builder.commit()

        # apply duration
        if duration:
            _builder.wait(duration)
            _builder.commit()

        # need release?
        if not no_up:
            for each_id in range(len(points)):
                _builder.up(each_id)

        _builder.publish(self.connection)

    def swipe(self, points, pressure=100, duration=None, no_down=None, no_up=None):
        """
        swipe between points, one by one

        :param points: [(400, 500), (500, 500)]
        :param pressure: default == 100
        :param duration:
        :param no_down: will not 'down' at the beginning
        :param no_up: will not 'up' at the end
        :return:
        """

        def transform_xy(x, y):
            """
            将屏幕像素坐标转换为 Minitouch 逻辑坐标
            """
            if self.real_width == 0 or self.real_height == 0:
                # Fallback if resolution fetching failed
                return x, y
            target_x = int((x / self.real_width) * int(self.connection.max_x))
            target_y = int((y / self.real_height) * int(self.connection.max_y))

            return target_x, target_y

        points = [list(map(int, each_point)) for each_point in points]

        _builder = CommandBuilder()
        point_id = 0

        # tap the first point
        if not no_down:
            x, y = points.pop(0)
            if int(self.connection.max_x) > 1440:
                x, y = transform_xy(x, y)
            _builder.down(point_id, x, y, pressure)
            _builder.publish(self.connection)

        # start swiping
        for each_point in points:
            x, y = each_point
            if int(self.connection.max_x) > 1440:
                x, y = transform_xy(x, y)
            _builder.move(point_id, x, y, pressure)

            # add delay between points
            if duration:
                _builder.wait(duration)
            _builder.commit()

        _builder.publish(self.connection)

        # release
        if not no_up:
            _builder.up(point_id)
            _builder.publish(self.connection)

    def up(self, contact_id: int = 0):
        """
        仅抬起当前指定触点，不再移动

        :param contact_id: 触点 id，默认 0
        """
        _builder = CommandBuilder()
        _builder.up(contact_id)
        _builder.publish(self.connection)

    # extra functions' name starts with 'ext_'
    def ext_smooth_swipe(
        self, points, pressure=100, duration=None, part=None, no_down=None, no_up=None
    ):
        """
        smoothly swipe between points, one by one
        it will split distance between points into pieces

        before::

            points == [(100, 100), (500, 500)]
            part == 8

        after::

            points == [(100, 100), (150, 150), (200, 200), ... , (500, 500)]

        :param points:
        :param pressure:
        :param duration:
        :param part: default to 10
        :param no_down: will not 'down' at the beginning
        :param no_up: will not 'up' at the end
        :return:
        """
        if not part:
            part = 10

        points = [list(map(int, each_point)) for each_point in points]

        all_points = []

        for each_index in range(len(points) - 1):
            p0 = points[each_index]
            p3 = points[each_index + 1]

            # 使用 simulator.insert_swipe 中的三次贝塞尔轨迹生成中间点
            x0, y0 = p0
            x3, y3 = p3
            dx = x3 - x0
            dy = y3 - y0
            length = math.hypot(dx, dy)
            if length == 0:
                continue

            # 通过 part 近似控制插值点数量：距离越长或 part 越大，speed 越小，点越多
            speed = max(int(length / part), 1)

            segment_points = insert_swipe(p0, p3, speed=speed, min_distance=1)

            if not all_points:
                all_points.extend(segment_points)
            else:
                # 避免重复连接点
                all_points.extend(segment_points[1:])

        if not all_points:
            return

        # 确保最终点与原始路径的终点一致，并统一使用 tuple 以便可哈希/去重
        last_target = tuple(points[-1])
        all_points = [tuple(p) for p in all_points]
        if all_points[-1] != last_target:
            all_points.append(last_target)

        total = len(all_points)
        unique = len(set(all_points))
        head = all_points[:10]
        tail = all_points[-10:] if total > 10 else []

        # 统计连续重复点数量
        consecutive_dups = 0
        for idx in range(1, total):
            if all_points[idx] == all_points[idx - 1]:
                consecutive_dups += 1

        self.swipe(
            all_points,
            pressure=pressure,
            duration=duration,
            no_down=no_down,
            no_up=no_up,
        )


@contextmanager
def safe_device(device_id):
    """use MNTDevice safely"""
    _device = MNTDevice(device_id)
    try:
        yield _device
    finally:
        time.sleep(config.DEFAULT_DELAY)
        _device.stop()

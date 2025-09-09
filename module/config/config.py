import atexit
import copy
import sys
import threading

from ruamel.yaml import YAML

from module.logger import log
from utils.singletonmeta import SingletonMeta


class Config(metaclass=SingletonMeta):

    def __init__(self, version_path, example_path, config_path):
        self.yaml = YAML()
        # 并发与延迟写控制
        self._lock = threading.RLock()
        self._save_timer = None
        self._save_interval = 1.0  # 秒：在此时间窗口内的多次修改合并为一次写盘
        self._pending_save = False
        # 后台写盘线程
        self._writer_event = threading.Event()
        self._writer_thread = threading.Thread(target=self._writer_loop, name="ConfigWriter", daemon=True)
        self._writer_thread.start()

        # 加载版本信息
        self.version = self._load_version(version_path)
        # 加载默认配置
        self.config = self._load_default_config(example_path)
        # 获取用户的配置文件路径
        self.config_path = config_path
        # 加载实际配置，此方法会根据实际配置覆盖默认配置
        self._load_config()
        # 进程退出前确保落盘
        atexit.register(self.flush)

    def _load_version(self, version_path: str) -> str:
        """加载版本信息"""
        try:
            with open(version_path, 'r', encoding='utf-8') as file:
                return file.read().strip()
        except FileNotFoundError:
            sys.exit("版本文件未找到")

    def _load_default_config(self, example_path: str) -> dict:
        """加载默认配置信息"""
        try:
            with open(example_path, 'r', encoding='utf-8') as file:
                return self.yaml.load(file) or {}
        except FileNotFoundError:
            sys.exit("默认配置文件未找到")

    def _load_config(self, path = None) -> None:
        """加载用户配置文件，如未找到则保存默认配置"""
        path = path or self.config_path
        try:
            with open(path, 'r', encoding='utf-8') as file:
                loaded_config = self.yaml.load(file)
                if loaded_config:
                    self._update_config(self.config, loaded_config)
                    self._save_config()
        except FileNotFoundError:
            self._save_config()
        except Exception as e:
            sys.exit(f"配置文件{path}加载错误: {e}")

    def _update_config(self, config: dict, new_config: dict) -> None:
        """递归更新配置信息"""
        for key, value in new_config.items():
            if key in config:
                if isinstance(config[key], dict) and isinstance(value, dict):
                    self._update_config(config[key], value)
                else:
                    config[key] = value
            elif any(sub in key for sub in ("_setting", "_remark_name")):
                config[key] = value

    def _save_config(self) -> None:
        """保存到配置文件（立即写盘）"""
        # 拷贝快照后在锁外写盘，避免长时间持锁
        with self._lock:
            snapshot = copy.deepcopy(self.config)
            path = self.config_path
        y = YAML()
        with open(path, 'w', encoding='utf-8') as file:
            y.dump(snapshot, file)

    def get_value(self, key, default=None):
        """获取配置项的值，如果是可变对象，则返回其拷贝"""
        value = self.config.get(key, default)
        # 如果是可变对象，则返回其拷贝
        if isinstance(value, (list, dict, set)):
            return copy.deepcopy(value)  # 使用深拷贝确保嵌套对象安全
        return value

    def set_value(self, key, value):
        """设置配置项的值并延迟保存"""
        with self._lock:
            if isinstance(value, (list, dict, set)):
                self.config[key] = copy.deepcopy(value)
            else:
                self.config[key] = value

            # 防止 cdk 泄露
            masked_value = "已加密" if key == "mirrorchyan_cdk" else value
            log.DEBUG(f"{key} change to: {masked_value}")  # 增加设置修改的信息

            # 安排一次延迟保存
            self._schedule_save()

    def _schedule_save(self) -> None:
        """在时间窗口内合并多次修改，只触发一次写盘。"""
        with self._lock:
            self._pending_save = True
            # 取消已有的定时器，重新计时
            if self._save_timer is not None:
                try:
                    self._save_timer.cancel()
                except Exception:
                    pass
            self._save_timer = threading.Timer(self._save_interval, self._flush_save)
            self._save_timer.daemon = True
            self._save_timer.start()

    def request_save(self) -> None:
        """公开方法：请求一次延迟保存（不阻塞当前线程）。"""
        self._schedule_save()

    def _flush_save(self) -> None:
        """定时器回调：触发一次后台写盘信号。"""
        with self._lock:
            if not self._pending_save:
                return
            self._pending_save = False
            self._save_timer = None
            self._writer_event.set()

    def flush(self) -> None:
        """立即将挂起的更改写入磁盘。"""
        with self._lock:
            if self._save_timer is not None:
                try:
                    self._save_timer.cancel()
                except Exception:
                    pass
                self._save_timer = None
            pending = self._pending_save
            self._pending_save = False
        if pending:
            self._save_config()

    def _writer_loop(self) -> None:
        """后台写盘线程：收到事件后把当前config写入文件"""
        while True:
            self._writer_event.wait()
            try:
                self._save_config()
            except Exception as e:
                log.ERROR(f"配置保存失败，错误信息：{e}")

            # 等待下一次
            self._writer_event.clear()

    def just_load_config(self, path=None) -> None:
        """仅加载配置文件，不保存"""
        path = path or self.config_path
        try:
            with open(path, 'r', encoding='utf-8') as file:
                loaded_config = self.yaml.load(file)
            if loaded_config:
                self._update_config(self.config, loaded_config)
        except FileNotFoundError:
            self._schedule_save()
        except Exception as e:
            sys.exit(f"配置文件{path}加载错误: {e}")

    def unsaved_set_value(self, key, value) -> None:
        """仅设置配置项的值 不保存"""
        if self.config is None:
            self.just_load_config()
        if isinstance(value, (list, dict, set)):
            self.config[key] = copy.deepcopy(value)
        else:
            self.config[key] = value

        # 防止 cdk 泄露
        if key == "mirrorchyan_cdk":
            value = "已加密"

        log.DEBUG(f"{key} change to: {value}")  # 增加设置修改的信息

    def unsaved_del_key(self, key) -> None:
        """仅删除配置项 不保存"""
        if self.config is None:
            self.just_load_config()
        self.config.pop(key, None)

    def del_key(self, key) -> None:
        """删除配置项并保存"""
        self._load_config()
        self.config.pop(key, None)
        self._schedule_save()

    def __getattr__(self, attr: str):
        """允许通过属性访问配置项的值"""
        if attr in self.config:
            value = self.config[attr]
            if isinstance(value, (list, dict, set)):
                return copy.deepcopy(value)
            return value
        raise AttributeError(f"'{type(self).__name__}' 对象没有属性 ‘{attr}'")


class Theme_pack_list(metaclass=SingletonMeta):

    def __init__(self, example_path, theme_pack_list_path):
        self.yaml = YAML()
        # 加载默认配置
        self.config = self._load_default_config(example_path)
        # 获取用户的配置文件路径
        self.theme_pack_list_path = theme_pack_list_path
        # 加载实际配置，此方法会根据实际配置覆盖默认配置
        self._load_config()

    def _load_version(self, version_path: str) -> str:
        """加载版本信息"""
        try:
            with open(version_path, 'r', encoding='utf-8') as file:
                return file.read().strip()
        except FileNotFoundError:
            sys.exit("主题包名单文件未找到")

    def _load_default_config(self, example_path: str) -> dict:
        """加载默认配置信息"""
        try:
            with open(example_path, 'r', encoding='utf-8') as file:
                return self.yaml.load(file) or {}
        except FileNotFoundError:
            sys.exit("默认主题包配置文件未找到")

    def _load_config(self, path=None) -> None:
        """加载用户配置文件，如未找到则保存默认配置"""
        path = path or self.theme_pack_list_path
        try:
            with open(path, 'r', encoding='utf-8') as file:
                loaded_config = self.yaml.load(file)
                if loaded_config:
                    self._update_config(self.config, loaded_config)
                    self.save_config()
        except FileNotFoundError:
            self.save_config()
        except Exception as e:
            sys.exit(f"配置文件{path}加载错误: {e}")

    def _update_config(self, config: dict, new_config: dict) -> None:
        """更新配置信息"""
        if config == new_config:
            return
        for key, value in new_config.items():
            if isinstance(value, dict):
                for k, v in value.items():
                    config[key][k] = v
            else:
                config[key] = value
        log.DEBUG(f"主题包名单已更新")

    def save_config(self):
        """保存到配置文件"""
        with open(self.theme_pack_list_path, 'w', encoding='utf-8') as file:
            self.yaml.dump(self.config, file)

    def get_value(self, key, default=None):
        """获取配置项的值，如果是可变对象，则返回其拷贝"""
        value = self.config.get(key, default)
        # 如果是可变对象，则返回其拷贝
        if isinstance(value, (list, dict, set)):
            return copy.deepcopy(value)  # 使用深拷贝确保嵌套对象安全
        return value

    def set_value(self, key, value) -> None:
        """设置配置项的值并保存"""
        self._load_config()
        if isinstance(value, (list, dict, set)):
            self.config[key] = copy.deepcopy(value)
        else:
            self.config[key] = value
        self.save_config()

    def __getattr__(self, attr: str):
        """允许通过属性访问配置项的值"""
        if attr in self.config:
            value = self.config[attr]
            if isinstance(value, (list, dict, set)):
                return copy.deepcopy(value)
            return value
        raise AttributeError(f"'{type(self).__name__}' 对象没有属性 ‘{attr}'")

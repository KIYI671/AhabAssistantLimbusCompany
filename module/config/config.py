import atexit
import copy
import shutil
import sys
import threading
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel
from ruamel.yaml import YAML

from module.logger import log
from utils.singletonmeta import SingletonMeta

from .config_typing import ConfigModel, TeamSetting


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
        self.config = ConfigModel()
        # 获取用户的配置文件路径
        self.config_path = Path(config_path)
        # 保存含有注释的yaml文件的路径
        self.example_path = Path(example_path)

        # 加载实际配置，此方法会根据实际配置覆盖默认配置
        self._load_config()
        log.debug(f"配置文件已加载，版本号：{self.version}, 配置版本: {self.get_value('config_version', '未知')}")
        # 进程退出前确保落盘
        atexit.register(self.flush)

    def _old_version_cfg_upgrade(self, saved_version: int, loaded_config: dict) -> None:
        """旧版本配置升级处理

        本身不进行保存文件操作
        """
        log.info("检测到旧版本配置文件，正在进行升级...")

        # 镜牢历史数据格式转换
        if saved_version < 1768403022:
            team_num = len(self.get_value("teams_be_select", []))

            def _calculate_time_history(time_list: list[float], count: int) -> list[float]:
                """从每局都记录转换为只记录三种平均值"""
                if count == 0:
                    return [0.0, 0.0, 0.0]
                if len(time_list) == 3 and count != 3:
                    return time_list  # 已经是新格式，直接返回
                elif len(time_list) == 3 and count == 3:
                    # 判断是否是巧合
                    if time_list[0] == time_list[1] == time_list[2]:
                        return time_list
                total_avr = 0
                five_avr = 0
                ten_avr = 0
                for index in range(-1, -len(time_list) - 1, -1):
                    total_avr += time_list[index]
                    if index >= -5:
                        five_avr += time_list[index]
                    if index >= -10:
                        ten_avr += time_list[index]
                total_avr /= count
                five_avr /= min(5, count)
                ten_avr /= min(10, count)
                new_time_list = [total_avr, five_avr, ten_avr]

                return new_time_list

            try:
                if team_num > 0:
                    for i in range(1, team_num + 1):
                        history_key = f"team{i}_history"
                        history = loaded_config.get(history_key, {})
                        if not history:
                            continue
                        hard_time = history.get("total_mirror_time_hard", [])
                        hard_count = history.get("mirror_hard_count", 0)
                        normal_time = history.get("total_mirror_time_normal", [])
                        normal_count = history.get("mirror_normal_count", 0)

                        hard_time = _calculate_time_history(hard_time, hard_count)
                        normal_time = _calculate_time_history(normal_time, normal_count)
                        history["total_mirror_time_hard"] = hard_time
                        history["mirror_hard_count"] = hard_count
                        history["total_mirror_time_normal"] = normal_time
                        history["mirror_normal_count"] = normal_count
                        loaded_config[history_key] = history
            except Exception as e:
                log.error(f"镜牢历史数据格式转换失败，错误信息：{e}")

        # 旧配置类型转换
        if saved_version < 1771413380:
            if self.get_value("set_win_position", True) is True:
                loaded_config["set_win_position"] = "free"
        if saved_version < 1771965838:
            if self.get_value("background_click", True) is True:
                loaded_config["win_input_type"] = "background"
            else:
                loaded_config["win_input_type"] = "foreground"
        if saved_version < 1775826004:
            teams: dict[str, dict] = {}
            for i in range(1, 21):
                settings: dict | None = loaded_config.get(f"team{i}_setting", None)
                if settings is None:
                    continue
                remark_name: str | None = loaded_config.get(f"team{i}_remark_name", None)
                history: dict = loaded_config.get(f"team{i}_history", {})

                settings.update(history)
                settings["remark_name"] = remark_name
                teams[f"{i}"] = TeamSetting(**settings).model_dump()
            loaded_config["teams"] = teams
            if loaded_config.get("timezone", "None") == "None":
                loaded_config["timezone"] = None

        log.info("配置升级完成")

    def _load_version(self, version_path: str) -> str:
        """加载版本信息"""
        try:
            with open(version_path, "r", encoding="utf-8") as file:
                return file.read().strip()
        except FileNotFoundError:
            sys.exit("版本文件未找到")

    def _load_default_config(self, example_path: str | Path | None = None) -> dict:
        """加载默认配置信息"""
        if example_path is None:
            example_path = self.example_path
        else:
            self.example_path = Path(example_path)
        try:
            with open(example_path, "r", encoding="utf-8") as file:
                return self.yaml.load(file) or {}
        except FileNotFoundError:
            sys.exit("默认配置文件未找到")

    def _load_config(self, path: str | Path | None = None) -> None:
        """加载用户配置文件，如未找到则保存默认配置"""
        if isinstance(path, str):
            path = Path(path)
        path = path or self.config_path
        try:
            if not path.exists():
                self._save_config()
                return
            with open(path, "r", encoding="utf-8") as file:
                shutil.copy(path, path.with_suffix(".yaml.bak"))
                loaded_config: dict = self.yaml.load(file)
                if loaded_config is None:
                    log.error("读取到的设置文件为空, 请确认是否因为罕见情况丢失了数据")
                    loaded_config = ConfigModel().model_dump()
                if loaded_config.get("save_count", 0) >= 5:
                    shutil.copy(path, path.with_suffix(".yaml.old"))  # 保留5次启动前的配置文件

                if loaded_config.get("config_version", 0) < self.config.config_version:
                    saved_version = loaded_config.get("config_version", 0)
                    loaded_config["config_version"] = self.config.config_version
                    self._old_version_cfg_upgrade(saved_version, loaded_config)
                # 使用更新后的配置初始化 Config 对象
                self.config = ConfigModel(**loaded_config)
                # 成功加载后保存当前文件为备份
                shutil.copy(path, path.with_suffix(".yaml.backup"))
                self.config.save_count += 1
                if self.config.save_count > 5:
                    self.config.save_count = 0
                self._save_config()
        except FileNotFoundError:
            self._save_config()
        except Exception as e:
            log.error(f"配置文件{path}加载错误: {e}", exc_info=True)
            sys.exit(f"配置文件{path}加载错误: {e}")

    def _save_config(self) -> None:
        """保存到配置文件（立即写盘）"""
        # 拷贝快照后在锁外写盘，避免长时间持锁
        with self._lock:
            snapshot = self.config.model_dump()
        example_yaml = self._load_default_config()
        # 从快照更新到yaml对象，保持注释不变
        example_yaml.update(snapshot)

        with open(self.config_path, "w", encoding="utf-8") as file:
            self.yaml.dump(example_yaml, file)

    def get_value(self, key: str, default: Any = None, *, config_obj: Optional[BaseModel] = None) -> Any:
        """获取配置项的值, 如果是可变对象，则返回其指针"""
        if config_obj is not None:
            value = getattr(config_obj, key, default)
        else:
            value = getattr(self.config, key, default)
        return value

    def set_value(self, key: str, value: Any, *, config_obj: Optional[BaseModel | dict] = None) -> None:
        """设置配置项的值并延迟保存"""
        with self._lock:
            self.unsaved_set_value(key, value, config_obj=config_obj, stacklevel=3)

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

    def save(self, instant: bool = False) -> None:
        """公开方法：请求一次保存

        Args:
            instant (bool): 是否立即保存（跳过延迟机制, 但会阻塞线程）
        """
        if instant:
            self._save_config()
        else:
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
                log.error(f"配置保存失败，错误信息：{e}")

            # 等待下一次
            self._writer_event.clear()

    def just_load_config(self, path: Optional[Path | str] = None) -> None:
        """仅加载配置文件，不保存"""
        path = path or self.config_path
        try:
            with open(path, "r", encoding="utf-8") as file:
                loaded_config = self.yaml.load(file)
            if loaded_config:
                self.config = ConfigModel(**loaded_config)
        except FileNotFoundError:
            self._schedule_save()
        except Exception as e:
            sys.exit(f"配置文件{path}加载错误: {e}")

    def unsaved_set_value(
        self, key: str, value: Any, *, config_obj: Optional[BaseModel | dict] = None, stacklevel: int = 2
    ) -> None:
        """仅设置配置项的值 不保存"""
        if self.config is None:
            self.just_load_config()
        if isinstance(value, (list, dict, set)):
            value = copy.deepcopy(value)
        if isinstance(config_obj, BaseModel):
            setattr(config_obj, key, value)
        elif isinstance(config_obj, dict):
            config_obj[key] = value
        else:
            setattr(self.config, key, value)

        # 防止 cdk 泄露
        if key == "mirrorchyan_cdk":
            value = "已加密"
        if config_obj:
            if isinstance(config_obj, dict):
                value_obj: BaseModel | None | Any = config_obj.get(key, None)
                if isinstance(value_obj, BaseModel):
                    cls = value_obj.__class__.__name__
                else:
                    cls = "None"
                log.debug(f"{cls}::{key} change to: {value}", stacklevel=stacklevel)
            else:
                log.debug(f"{config_obj.__class__.__name__}::{key} change to: {value}", stacklevel=stacklevel)
        else:
            log.debug(f"{key} change to: {value}", stacklevel=stacklevel)  # 增加设置修改的信息

    def unsaved_del_key(self, key: str, *, config_obj: Optional[BaseModel | dict] = None) -> None:
        """仅删除配置项 不保存"""
        if self.config is None:
            self.just_load_config()
        if isinstance(config_obj, BaseModel):
            delattr(config_obj, key)
        elif isinstance(config_obj, dict):
            if key in config_obj:
                del config_obj[key]
        else:
            delattr(self.config, key)

    def del_key(self, key: str, *, config_obj: Optional[BaseModel | dict] = None) -> None:
        """删除配置项并保存"""
        self.unsaved_del_key(key, config_obj=config_obj)
        self._schedule_save()

    def __getitem__(self, key: str):
        """通过键名访问配置项的值"""
        if not hasattr(self.config, key):
            raise KeyError(f"配置项 '{key}' 不存在")
        return self.get_value(key)

    def __setitem__(self, key: str, value: Any):
        """通过键名设置配置项的值

        **注意该方法不请求保存**"""
        self.unsaved_set_value(key, value)

    def __getattr__(self, name):
        """允许通过属性访问配置项的值"""
        if hasattr(self.config, name):
            return self.get_value(name)
        raise AttributeError(f"'{type(self).__name__}' 对象没有属性 ‘{name}'")


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
            with open(version_path, "r", encoding="utf-8") as file:
                return file.read().strip()
        except FileNotFoundError:
            sys.exit("主题包名单文件未找到")

    def _load_default_config(self, example_path: str) -> dict:
        """加载默认配置信息"""
        try:
            with open(example_path, "r", encoding="utf-8") as file:
                return self.yaml.load(file) or {}
        except FileNotFoundError:
            sys.exit("默认主题包配置文件未找到")

    def _load_config(self, path=None) -> None:
        """加载用户配置文件，如未找到则保存默认配置"""
        path = path or self.theme_pack_list_path
        try:
            with open(path, "r", encoding="utf-8") as file:
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
        log.debug("主题包名单已更新")

    def save_config(self):
        """保存到配置文件"""
        with open(self.theme_pack_list_path, "w", encoding="utf-8") as file:
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

    def __getitem__(self, key: str):
        """通过键名访问配置项的值"""
        return self.get_value(key)

    def __setitem__(self, key: str, value: Any):
        """通过键名设置配置项的值"""
        self.set_value(key, value)

    def __getattr__(self, attr: str):
        """允许通过属性访问配置项的值"""
        if attr in self.config:
            value = self.config[attr]
            if isinstance(value, (list, dict, set)):
                return copy.deepcopy(value)
            return value
        raise AttributeError(f"'{type(self).__name__}' 对象没有属性 ‘{attr}'")

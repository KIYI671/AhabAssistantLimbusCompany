import atexit
import copy
import sys
import threading
from pathlib import Path
from time import localtime, strftime, time
from typing import Any, Optional

import numpy as np
from pydantic import BaseModel, ValidationError
from ruamel.yaml import YAML, YAMLError

from module.after_completion_types import (
    LEGACY_AFTER_COMPLETION_TO_CONFIG,
    POWER_ACTION_NONE,
    serialize_after_actions,
    serialize_power_action,
)
from module.logger import log
from utils.singletonmeta import SingletonMeta

from .config_typing import ConfigModel, TeamSetting


class Config(metaclass=SingletonMeta):
    def __init__(self, version_path, example_path, config_path, backup_path: str = "config_backup"):
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

        self.backup_path = Path(backup_path)

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
        if saved_version < 1772205660:
            # 迁移旧版结束后动作配置，按字段独立迁移，避免覆盖用户已设置的新字段
            # 映射表统一由 module.after_completion_types 维护；config 层只负责迁移与落盘。
            legacy_value = int(self.get_value("after_completion", 0) or 0)
            legacy_actions, legacy_power = LEGACY_AFTER_COMPLETION_TO_CONFIG.get(legacy_value, ((), POWER_ACTION_NONE))
            migrated = False

            # 仅在 actions 字段缺失或类型错误时补写
            current_actions = self.get_value("after_completion_actions")
            if not isinstance(current_actions, list):
                # 配置文件保持字符串协议，不直接持久化内部 Enum。
                loaded_config["after_completion_actions"] = serialize_after_actions(legacy_actions)
                migrated = True

            # 仅在 power_action 字段缺失或类型错误时补写（与 actions 独立判断）
            current_power = self.get_value("after_completion_power_action")
            if not isinstance(current_power, str):
                loaded_config["after_completion_power_action"] = serialize_power_action(legacy_power)
                migrated = True

            if migrated:
                log.info(f"已将旧版结束后操作配置迁移为组合动作（legacy={legacy_value}）")
        if saved_version < 1775826004:
            teams: dict[str, dict] = {}
            for i in range(1, 21):
                settings: dict | None = loaded_config.get(f"team{i}_setting", None)
                if settings is None:
                    continue
                remark_name: str | None = loaded_config.get(f"team{i}_remark_name", None)
                history: dict = loaded_config.get(f"team{i}_history", {}) or {}

                settings.update(history)
                settings["remark_name"] = remark_name
                teams[f"{i}"] = settings
            loaded_config["teams"] = teams
        if saved_version < 1779444115:
            current_config_path = Path("config.yaml")
            suffixes = [".yaml.bak", ".yaml.backup", ".yaml.old"]
            for suffix in suffixes:
                file = current_config_path.with_suffix(suffix)
                if file.exists():
                    try:
                        file.unlink()
                    except Exception as e:
                        log.error(f"删除旧备份文件 {file} 失败: {e}")
        if saved_version < 1779550000:
            task_order = loaded_config.get("task_order")
            if not isinstance(task_order, list) or not task_order:
                loaded_config["task_order"] = ["daily_task", "get_reward", "buy_enkephalin", "mirror"]

        if saved_version < 1778889600:
            teams = loaded_config.get("teams", {}) or {}
            for team_key, settings in list(teams.items()):
                teams[team_key] = migrate_legacy_team_setting_data(settings)
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
                if self.backup_path.exists():
                    backup_files = [f for f in self.backup_path.iterdir() if f.is_file() and f.suffix == ".yaml"]
                    if backup_files:
                        backup_files.sort(key=lambda f: f.stat().st_birthtime, reverse=True)
                        log.info("配置文件不存在，存在备份配置，尝试从备份文件恢复配置")
                        self._load_config(backup_files[0])
                        return
                self._save_config()
                return
            with open(path, "r", encoding="utf-8") as file:
                loaded_config: dict = self.yaml.load(file)
                if loaded_config is None:
                    log.error("读取到的设置文件为空, 请确认是否因为罕见情况丢失了数据")
                    if self.backup_path.exists():
                        backup_files = [f for f in self.backup_path.iterdir() if f.is_file() and f.suffix == ".yaml"]
                    else:
                        backup_files = []
                    if backup_files:
                        backup_files.sort(key=lambda f: f.stat().st_birthtime, reverse=True)
                        with open(backup_files[0], "r", encoding="utf-8") as backup_file:
                            loaded_config = self.yaml.load(backup_file) or {}
                        if loaded_config:
                            log.info(f"已从最新的备份文件 {backup_files[0].name} 恢复配置")
                        else:
                            log.error(
                                f"最新的备份文件 {backup_files[0].name} 无法读取到有效配置，请自行通过 {self.backup_path.name} 文件夹下其他文件恢复数据"
                            )
                            loaded_config = ConfigModel().model_dump()
                    else:
                        loaded_config = ConfigModel().model_dump()
                if not isinstance(loaded_config.get("config_version", 0), int):
                    raise TypeError("配置文件版本号不是 int 类型")
                if loaded_config.get("config_version", 0) < self.config.config_version:
                    saved_version = loaded_config.get("config_version", 0)
                    loaded_config["config_version"] = self.config.config_version
                    self._old_version_cfg_upgrade(saved_version, loaded_config)
                # 使用更新后的配置初始化 Config 对象
                self.config = ConfigModel(**loaded_config)
                queue_in_loaded_config = loaded_config.get("teams_active_queue")
                if queue_in_loaded_config is None:
                    normalized_queue = self._normalize_team_queue(self.migrate_legacy_team_queue())
                else:
                    normalized_queue = self._normalize_team_queue(queue_in_loaded_config)
                self._sync_legacy_team_state(normalized_queue)
                # 成功加载后保存当前文件为备份
                self.backup_config()
                self._save_config()
        except FileNotFoundError:
            if self.backup_path.exists():
                backup_files = [f for f in self.backup_path.iterdir() if f.is_file() and f.suffix == ".yaml"]
                if backup_files:
                    backup_files.sort(key=lambda f: f.stat().st_birthtime, reverse=True)
                    log.info("配置文件不存在，尝试从备份文件恢复配置")
                    self._load_config(backup_files[0])
                    return
            self._save_config()
        except (ValidationError, ValueError, TypeError) as e:
            if path == self.config_path:
                log.error("配置文件数据非法，尝试使用备份文件恢复配置")
                if self.backup_path.exists():
                    backup_files = [f for f in self.backup_path.iterdir() if f.is_file() and f.suffix == ".yaml"]
                    if not backup_files:
                        log.error("备份目录下没有可用的备份文件，无法恢复配置")
                        raise
                    backup_files.sort(key=lambda f: f.stat().st_birthtime, reverse=True)
                    for i, backup_file in enumerate(backup_files):
                        try:
                            self._load_config(backup_file)
                            if i > 0:
                                log.info(f"已从较早的备份文件 {backup_file.name} 恢复配置")
                            break
                        except (ValidationError, ValueError, TypeError):
                            if i < len(backup_files) - 1:
                                log.info(f"备份文件 {backup_file.name} 恢复失败，尝试下一个备份文件")
                            else:
                                log.error("所有备份文件均无法恢复配置")
                                raise
                else:
                    log.error("备份目录不存在，无法恢复配置")
                    raise
            else:
                log.error(f"配置文件 {path} 数据非法，错误信息：{e}", exc_info=True)
                raise
        except YAMLError as e:
            log.error(f"配置文件 {path} 解析错误: {e}", exc_info=True)
            if path == self.config_path:
                log.error("配置文件解析错误，尝试使用备份文件恢复配置")
                if self.backup_path.exists():
                    backup_files = [f for f in self.backup_path.iterdir() if f.is_file() and f.suffix == ".yaml"]
                    if not backup_files:
                        log.error("备份目录下没有可用的备份文件，无法恢复配置")
                        raise
                    backup_files.sort(key=lambda f: f.stat().st_birthtime, reverse=True)
                    for i, backup_file in enumerate(backup_files):
                        try:
                            self._load_config(backup_file)
                            if i > 0:
                                log.info(f"已从较早的备份文件 {backup_file.name} 恢复配置")
                            break
                        except YAMLError:
                            if i < len(backup_files) - 1:
                                log.info(f"备份文件 {backup_file.name} 恢复失败，尝试下一个备份文件")
                            else:
                                log.error("所有备份文件均无法恢复配置")
                                raise
                else:
                    log.error("备份目录不存在，无法恢复配置")
                    raise
            else:
                raise
        except Exception as e:
            log.error(f"配置文件{path}加载错误: {e}", exc_info=True)
            raise

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
            try:
                value = getattr(self.config, key, default)
            except:
                value = default
        return value

    def get_team_numbers(self) -> list[int]:
        """获取所有已配置的队伍编号，返回排序后的列表"""
        teams = self.get_value("teams", {}) or {}
        team_numbers: list[int] = []
        for team_key in teams:
            try:
                team_num = int(team_key)
            except (TypeError, ValueError):
                continue
            if team_num > 0:
                team_numbers.append(team_num)
        return sorted(team_numbers)

    def _normalize_team_queue(self, queue: list[int]) -> list[int]:
        """去重并过滤无效队伍编号，返回干净的队列"""
        valid_team_numbers = set(self.get_team_numbers())
        normalized_queue: list[int] = []
        seen: set[int] = set()
        for team_num in queue or []:
            if type(team_num) is not int:
                continue
            if team_num not in valid_team_numbers or team_num in seen:
                continue
            normalized_queue.append(team_num)
            seen.add(team_num)
        return normalized_queue

    def migrate_legacy_team_queue(self) -> list[int]:
        """从旧的 teams_order/teams_be_select 迁移出队列顺序"""
        team_numbers = self.get_team_numbers()
        if not team_numbers:
            return []

        teams_order = self.get_value("teams_order", []) or []
        order_pairs: list[tuple[int, int]] = []
        used_orders: set[int] = set()
        for team_num in team_numbers:
            order_index = team_num - 1
            if order_index >= len(teams_order):
                continue
            order = teams_order[order_index]
            if not isinstance(order, int) or order <= 0 or order in used_orders:
                continue
            order_pairs.append((order, team_num))
            used_orders.add(order)

        teams_be_select = self.get_value("teams_be_select", []) or []
        migrated_queue = [team_num for _, team_num in sorted(order_pairs)]
        queued_team_numbers = set(migrated_queue)
        for team_num in team_numbers:
            select_index = team_num - 1
            if select_index >= len(teams_be_select):
                continue
            if teams_be_select[select_index] is not True or team_num in queued_team_numbers:
                continue
            migrated_queue.append(team_num)
        return migrated_queue

    def _sync_legacy_team_state(self, queue: list[int]) -> None:
        """将队列状态写回 teams_be_select / teams_order 等旧字段"""
        max_team_num = max(self.get_team_numbers(), default=0)
        teams_be_select = [False] * max_team_num
        teams_order = [0] * max_team_num
        for order, team_num in enumerate(queue, start=1):
            if team_num <= 0 or team_num > max_team_num:
                continue
            teams_be_select[team_num - 1] = True
            teams_order[team_num - 1] = order

        self.unsaved_set_value("teams_active_queue", queue)
        self.unsaved_set_value("teams_be_select", teams_be_select)
        self.unsaved_set_value("teams_order", teams_order)
        self.unsaved_set_value("teams_be_select_num", len(queue))

    def normalize_and_sync_team_state(self, persist: bool = True) -> None:
        """归一化队伍队列并同步到旧字段，persist=True 时写入磁盘"""
        queue = self.get_value("teams_active_queue")
        if queue is None:
            queue = self._normalize_team_queue(self.migrate_legacy_team_queue())
        else:
            queue = self._normalize_team_queue(queue)
        self._sync_legacy_team_state(queue)
        if persist:
            self.save()

    def reindex_team_queue(self, old_to_new: dict[int, int]) -> None:
        """根据 old_to_new 映射重新索引队列（队伍编号压缩后调用）"""
        queue = []
        for team_num in self.get_value("teams_active_queue", []) or []:
            new_team_num = old_to_new.get(team_num)
            if isinstance(new_team_num, int):
                queue.append(new_team_num)
        self._sync_legacy_team_state(self._normalize_team_queue(queue))
        self.save()

    def rotate_team_queue(self) -> None:
        """将队首队伍轮转到队尾"""
        queue = self._normalize_team_queue(self.get_value("teams_active_queue", []))
        if len(queue) > 1:
            queue = queue[1:] + queue[:1]
        self._sync_legacy_team_state(queue)
        self.save()

    def remove_team_from_queue(self, team_num: int) -> None:
        """从队列中移除指定队伍"""
        queue = [value for value in self.get_value("teams_active_queue", []) or [] if value != team_num]
        self._sync_legacy_team_state(self._normalize_team_queue(queue))
        self.save()

    def set_team_enabled(self, team_num: int, enabled: bool) -> None:
        """启用/禁用指定队伍（将其加入或移出队列）"""
        queue = self._normalize_team_queue(self.get_value("teams_active_queue", []))
        if enabled:
            if team_num not in queue:
                queue.append(team_num)
        else:
            queue = [value for value in queue if value != team_num]
        self._sync_legacy_team_state(self._normalize_team_queue(queue))
        self.save()

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
                queue_in_loaded_config = loaded_config.get("teams_active_queue")
                if queue_in_loaded_config is None:
                    normalized_queue = self._normalize_team_queue(self.migrate_legacy_team_queue())
                else:
                    normalized_queue = self._normalize_team_queue(queue_in_loaded_config)
                self._sync_legacy_team_state(normalized_queue)
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

    def backup_config(self) -> None:
        """备份当前配置到备份目录"""
        if not self.backup_path.exists():
            self.backup_path.mkdir(parents=True, exist_ok=True)
        now_time = localtime(time())
        files = [f for f in self.backup_path.iterdir() if f.is_file() and f.suffix == ".yaml"]
        if files:
            files.sort(key=lambda f: f.stat().st_birthtime)
            # 确保上次保存的文件日期不同于今天，避免重复备份
            latest_time = localtime(files[-1].stat().st_birthtime)
            if latest_time.tm_mday != now_time.tm_mday:
                backup_file = self.backup_path / f"config_{strftime('%Y%m%d_%H%M%S', now_time)}.yaml"
                with open(backup_file, "w", encoding="utf-8") as f:
                    self.yaml.dump(self.config.model_dump(), f)
            # 删除旧备份文件，保留最近的10个
            files = [f for f in self.backup_path.iterdir() if f.is_file() and f.suffix == ".yaml"]
            files.sort(key=lambda f: f.stat().st_birthtime)
            while len(files) > 10:
                try:
                    files[0].unlink()
                    files.pop(0)
                except Exception as e:
                    log.error(f"删除旧备份文件 {files[0]} 失败: {e}")
                    break
        else:
            backup_file = self.backup_path / f"config_{strftime('%Y%m%d_%H%M%S', now_time)}.yaml"
            with open(backup_file, "w", encoding="utf-8") as f:
                self.yaml.dump(self.config.model_dump(), f)

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


def migrate_legacy_team_setting_data(data: dict) -> dict:
    """Return team setting data with legacy starlight fields folded into opening_bonus."""
    migrated = dict(data)

    if migrated.get("choose_opening_bonus", False):
        opening_bonus = np.array(migrated.get("opening_bonus"), dtype=int)
        opening_bonus_level = np.array(migrated.get("opening_bonus_level"), dtype=int)
        migrated["opening_bonus"] = (opening_bonus * (opening_bonus_level + 1)).tolist()
    else:
        migrated["opening_bonus"] = TeamSetting().opening_bonus.copy()

    return migrated


class Theme_pack_list(metaclass=SingletonMeta):
    def __init__(self, example_path, theme_pack_list_path, theme_pack_weight_path):
        self.yaml = YAML()
        # 读取默认配置作为同步模板
        default_config = self._load_default_config(example_path)
        # 获取用户的配置文件路径
        self.theme_pack_list_path = theme_pack_list_path
        self.theme_pack_weight_path = Path(theme_pack_weight_path)
        # 先同步全局和队伍配置文件，再从全局配置文件加载 self.config
        self._sync_team_weight_configs(default_config)
        loaded_config = self.load_config(self.theme_pack_list_path)
        self.config = copy.deepcopy(loaded_config) if loaded_config else copy.deepcopy(default_config)

    def build_setting_key(self, hard_switch: bool, language: str | None) -> list[str]:
        """构建配置项键名列表。开启困难模式时同时返回普通和困难键。"""
        suffix = "_cn" if language == "zh_cn" else ""
        normal_key = f"theme_pack_list{suffix}"
        hard_key = f"theme_pack_list_hard{suffix}"
        if hard_switch:
            return [normal_key, hard_key]
        return [normal_key]

    def build_team_weight_path(self, team_num: int) -> str:
        """构建特定队伍的权重配置文件路径"""
        return str(Path(self.theme_pack_weight_path) / f"theme_pack_weight_team_{team_num}.yaml")

    def delete_team_weight_config(self, team_num: int) -> None:
        """删除指定队伍的自定义主题包权重配置文件。"""
        if team_num < 1:
            return

        path = Path(self.build_team_weight_path(team_num))
        if path.exists():
            path.unlink()

    def set_team_weight_config_from_team(self, target_team_num: int, source_team_num: int) -> None:
        """将 source 队伍的自定义主题包权重配置写入到 target 队伍。"""
        if target_team_num < 1 or source_team_num < 1:
            return
        if target_team_num == source_team_num:
            return

        source_path = Path(self.build_team_weight_path(source_team_num))
        target_path = Path(self.build_team_weight_path(target_team_num))

        if not source_path.exists():
            return

        with open(source_path, "r", encoding="utf-8") as file:
            source_config = self.yaml.load(file) or {}
        self.save_config(path=str(target_path), config_data=source_config)

    def create_team_weight_config(self, team_num: int) -> None:
        """创建指定队伍的自定义主题包权重配置文件（若不存在）。"""
        if team_num < 1:
            return

        target_path = Path(self.build_team_weight_path(team_num))
        if target_path.exists():
            return

        self.save_config(path=str(target_path), config_data=copy.deepcopy(self.config))

    def _sync_team_weight_configs(self, default_config: dict) -> None:
        """初始化时同步全局与已存在的队伍主题包权重配置。"""
        global_loaded_config = self.load_config(self.theme_pack_list_path)
        if global_loaded_config is None:
            self.save_config(path=self.theme_pack_list_path, config_data=default_config)
            global_loaded_config = copy.deepcopy(default_config)

        if global_loaded_config:
            merged_global_config = copy.deepcopy(default_config)
            self._update_config(merged_global_config, global_loaded_config)
            if merged_global_config != global_loaded_config:
                self.save_config(path=self.theme_pack_list_path, config_data=merged_global_config)

        if not self.theme_pack_weight_path.exists():
            return

        for team_weight_path in sorted(
            self.theme_pack_weight_path.glob("theme_pack_weight_team_*.yaml"), key=lambda item: item.name
        ):
            loaded_config = self.load_config(str(team_weight_path))
            if not loaded_config:
                continue

            merged_config = copy.deepcopy(default_config)
            self._update_config(merged_config, loaded_config)
            if merged_config != loaded_config:
                self.save_config(path=str(team_weight_path), config_data=merged_config)

    def get_effective_theme_pack_list(
        self, hard_switch: bool, language: str | None, team_num: int, use_custom_theme_pack_weight: bool
    ) -> tuple[dict]:
        """获取当前生效的主题包名单，考虑难度、语言、队伍和是否启用自定义权重等因素"""
        setting_keys = self.build_setting_key(hard_switch, language)
        theme_pack_list = {}
        for key in setting_keys:
            theme_pack_list.update(self.config.get(key, {}))
        if not use_custom_theme_pack_weight:
            log.debug("未启用自定义权重，返回默认主题包名单")
            return theme_pack_list

        custom_path = self.build_team_weight_path(team_num)
        loaded_data = self.load_config(custom_path)
        if loaded_data is None:
            log.debug(f"自定义文件不存在或读取失败，回退默认配置。path={custom_path}")
            return theme_pack_list

        effective_list = {}
        for key in setting_keys:
            effective_list.update(loaded_data.get(key, self.config.get(key, {})))
        log.debug(f"已加载自定义权重。path={custom_path}, keys={setting_keys}, count={len(effective_list)}")
        return effective_list

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

    def load_config(self, path: str):
        """纯加载函数：从 path 读取并返回配置内容"""
        try:
            with open(path, "r", encoding="utf-8") as file:
                return self.yaml.load(file) or {}
        except FileNotFoundError:
            return None
        except Exception as e:
            sys.exit(f"配置文件{path}加载错误: {e}")

    def _update_config(self, config: dict, new_config: dict) -> None:
        """更新配置信息"""
        if config == new_config:
            return
        for key, value in new_config.items():
            if isinstance(value, dict):
                if key not in config:
                    config[key] = {}
                for k, v in value.items():
                    config[key][k] = v
            else:
                config[key] = value
        log.debug("主题包名单已更新")

    def save_config(self, path, config_data):
        """保存配置到指定路径，config_data是要保存的配置内容，path是保存路径"""
        config_data = self.config if config_data is None else config_data

        # 确保父目录存在,如果不存在则自动创建
        Path(path).parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", encoding="utf-8") as file:
            self.yaml.dump(config_data, file)

    def get_value(self, key, default=None):
        """获取配置项的值，如果是可变对象，则返回其拷贝"""
        value = self.config.get(key, default)
        # 如果是可变对象，则返回其拷贝
        if isinstance(value, (list, dict, set)):
            return copy.deepcopy(value)  # 使用深拷贝确保嵌套对象安全
        return value

    def set_value(self, key, value) -> None:
        """设置配置项的值并保存"""
        if isinstance(value, (list, dict, set)):
            self.config[key] = copy.deepcopy(value)
        else:
            self.config[key] = value
        self.save_config(path=self.theme_pack_list_path, config_data=self.config)

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

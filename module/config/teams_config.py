import copy
import shutil
from pathlib import Path
from time import localtime, strftime, time
from typing import Any

from pydantic import BaseModel, Field, PrivateAttr, ValidationError
from ruamel.yaml import YAML

from module.logger import log

from .config_typing import TeamSetting
from .share_code_codec import decode_team_setting, encode_team_setting


MAX_TEAM_COUNT = 20
TEAMS_CONFIG_UPGRADE_VERSION = 1783296000


def migrate_legacy_team_setting_data(data: dict) -> dict:
    """将旧版星光字段折叠为新版 opening_bonus。"""
    migrated = dict(data)

    if migrated.get("choose_opening_bonus", False):
        opening_bonus = migrated.get("opening_bonus", [])
        opening_bonus_level = migrated.get("opening_bonus_level", [])
        migrated["opening_bonus"] = [
            int(value) * (int(opening_bonus_level[index]) + 1)
            for index, value in enumerate(opening_bonus)
            if index < len(opening_bonus_level)
        ]
    else:
        migrated["opening_bonus"] = TeamSetting().opening_bonus.copy()

    return migrated


class TeamConfig(BaseModel):
    """队伍配置集合及队伍 YAML 文件读写入口。"""

    teams: dict[int, TeamSetting] = Field(default_factory=dict)

    _yaml: YAML = PrivateAttr()
    _team_config_path: Path = PrivateAttr()
    _theme_pack_example_path: Path = PrivateAttr()
    _backup_path: Path = PrivateAttr()
    _default_theme_pack_weight: dict = PrivateAttr(default_factory=dict)

    def __init__(
        self,
        team_config_path: str | Path,
        theme_pack_example_path: str | Path,
        backup_path: str | Path = "team_config_backup",
        teams: dict[int, TeamSetting] | None = None,
    ):
        super().__init__(teams=teams or {})
        for team_num in self.teams:
            self._validate_team_num(team_num)
        self._yaml = YAML()
        self._team_config_path = Path(team_config_path)
        self._theme_pack_example_path = Path(theme_pack_example_path)
        self._backup_path = Path(backup_path)
        self._default_theme_pack_weight = self._load_default_theme_pack_weight()
        self._team_config_path.mkdir(parents=True, exist_ok=True)

    @property
    def team_config_path(self) -> Path:
        return self._team_config_path

    @property
    def theme_pack_example_path(self) -> Path:
        return self._theme_pack_example_path

    @property
    def backup_path(self) -> Path:
        return self._backup_path

    @property
    def default_theme_pack_weight(self) -> dict:
        return self._default_theme_pack_weight

    def _validate_team_num(self, team_num: int) -> int:
        if type(team_num) is not int or team_num < 1 or team_num > MAX_TEAM_COUNT:
            raise ValueError(f"队伍编号必须在 1..{MAX_TEAM_COUNT} 范围内: {team_num}")
        return team_num

    def build_team_path(self, team_num: int) -> Path:
        team_num = self._validate_team_num(team_num)
        return self._team_config_path / f"team_{team_num}.yaml"

    def _load_default_theme_pack_weight(self) -> dict:
        try:
            with open(self._theme_pack_example_path, "r", encoding="utf-8") as file:
                return self._yaml.load(file) or {}
        except FileNotFoundError:
            log.error(f"默认主题包权重文件不存在: {self._theme_pack_example_path}")
            return {}

    def _build_default_team_setting(self, team_num: int) -> TeamSetting:
        team_num = self._validate_team_num(team_num)
        team_setting = TeamSetting()
        team_setting.team_number = team_num
        team_setting.theme_pack_weight = copy.deepcopy(self._default_theme_pack_weight)
        return team_setting

    def _load_raw_team_file(self, team_num: int) -> dict | None:
        team_num = self._validate_team_num(team_num)
        path = self.build_team_path(team_num)
        if not path.exists():
            return None
        with open(path, "r", encoding="utf-8") as file:
            data = self._yaml.load(file)
        return data if isinstance(data, dict) else None

    def _merge_theme_pack_defaults(self, weight: dict | None) -> dict:
        merged = copy.deepcopy(self._default_theme_pack_weight)
        if not isinstance(weight, dict):
            return merged

        for key, value in weight.items():
            if isinstance(value, dict) and isinstance(merged.get(key), dict):
                merged[key].update(value)
            else:
                merged[key] = copy.deepcopy(value)
        return merged

    def _normalize_team_data(self, team_num: int, data: dict | None) -> TeamSetting:
        team_num = self._validate_team_num(team_num)
        if not data:
            return self._build_default_team_setting(team_num)

        if isinstance(data.get("team_setting"), dict):
            team_data = copy.deepcopy(data["team_setting"])
        else:
            team_data = copy.deepcopy(data)

        embedded_weight = team_data.get("theme_pack_weight")
        legacy_weight = data.get("theme_pack_weight")
        if not embedded_weight and legacy_weight is not None:
            team_data["theme_pack_weight"] = legacy_weight

        team_data["team_number"] = team_num
        team_data["theme_pack_weight"] = self._merge_theme_pack_defaults(team_data.get("theme_pack_weight"))

        try:
            return TeamSetting(**team_data)
        except ValidationError as e:
            log.error(f"队伍 {team_num} 配置校验失败，使用默认队伍配置恢复: {e}")
            recovered = self._build_default_team_setting(team_num)
            recovered.theme_pack_weight = self._merge_theme_pack_defaults(team_data.get("theme_pack_weight"))
            return recovered

    def _serialize_team(self, team_setting: TeamSetting) -> dict:
        return {"team_setting": team_setting.model_dump()}

    def _save_team_file(self, team_num: int, team_setting: TeamSetting) -> None:
        path = self.build_team_path(team_num)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as file:
            self._yaml.dump(self._serialize_team(team_setting), file)

    def _extract_team_setting_data(self, data: dict) -> dict:
        if isinstance(data.get("team_setting"), dict):
            team_data = dict(data["team_setting"])
            if "theme_pack_weight" not in team_data and isinstance(data.get("theme_pack_weight"), dict):
                team_data["theme_pack_weight"] = data["theme_pack_weight"]
            return team_data
        return data

    def load_team(self, team_num: int) -> TeamSetting:
        team_num = self._validate_team_num(team_num)
        if team_num in self.teams:
            return self.teams[team_num]

        raw_data = self._load_raw_team_file(team_num)
        team_setting = self._normalize_team_data(team_num, raw_data)

        serialized = self._serialize_team(team_setting)
        if raw_data != serialized:
            self.save_team(team_num, team_setting)
        else:
            self.teams[team_num] = team_setting
        return team_setting

    def get_team(self, team_num: int) -> TeamSetting:
        """从已加载到内存的队伍集合中读取队伍配置。"""
        team_num = self._validate_team_num(team_num)
        return self.teams[team_num]

    def save_team(self, team_num: int, team_setting: TeamSetting | dict) -> None:
        team_num = self._validate_team_num(team_num)
        if isinstance(team_setting, dict):
            team_setting = self._normalize_team_data(team_num, {"team_setting": team_setting})

        team_setting.team_number = team_num
        team_setting.theme_pack_weight = self._merge_theme_pack_defaults(team_setting.theme_pack_weight)

        self._save_team_file(team_num, team_setting)
        self.teams[team_num] = team_setting

    def ensure_team(self, team_num: int) -> TeamSetting:
        return self.load_team(team_num)

    def _load_teams_config(
        self,
        max_team_count: int = MAX_TEAM_COUNT,
        saved_version: int | None = None,
        loaded_config: dict | None = None,
        legacy_theme_pack_weight_path: str | Path | None = None,
    ) -> None:
        if saved_version is not None and loaded_config is not None:
            self._old_version_teams_config_upgrade(saved_version, loaded_config, legacy_theme_pack_weight_path)
        for team_num in range(1, max_team_count + 1):
            self.load_team(team_num)
        self.backup_teams_config()

    def update_team_config(self, team_num: int, team_setting: TeamSetting) -> TeamSetting:
        self.save_team(team_num, team_setting)
        return self.load_team(team_num)

    def reset_team(self, team_num: int, reset_weight: bool = True) -> TeamSetting:
        current_weight = None
        if not reset_weight:
            current_weight = self.get_team_theme_pack_weight(team_num)

        team_setting = self._build_default_team_setting(team_num)
        if current_weight is not None:
            team_setting.theme_pack_weight = current_weight
        self.save_team(team_num, team_setting)
        return team_setting

    def copy_team(self, team_num: int) -> dict:
        return self.load_team(team_num).model_dump()

    def copy_team_share_code(self, team_num: int) -> str:
        return encode_team_setting(self.copy_team(team_num), team_num)

    def paste_team(self, team_num: int, data: dict) -> TeamSetting:
        team_setting = self._normalize_team_data(team_num, {"team_setting": self._extract_team_setting_data(data)})
        self.save_team(team_num, team_setting)
        return team_setting

    def paste_team_share_code(self, team_num: int, text: str) -> TeamSetting:
        if not text.strip():
            raise ValueError("队伍配置为空")
        return self.paste_team(team_num, decode_team_setting(text))

    def get_team_theme_pack_weight(self, team_num: int) -> dict:
        return copy.deepcopy(self.load_team(team_num).theme_pack_weight)

    def save_team_theme_pack_weight(self, team_num: int, weight: dict) -> None:
        team_setting = self.load_team(team_num)
        team_setting.theme_pack_weight = self._merge_theme_pack_defaults(weight)
        self.save_team(team_num, team_setting)

    def reset_team_theme_pack_weight(self, team_num: int) -> dict:
        weight = copy.deepcopy(self._default_theme_pack_weight)
        self.save_team_theme_pack_weight(team_num, weight)
        return weight

    def sync_team_theme_pack_weight(self, team_num: int) -> dict:
        team_setting = self.load_team(team_num)
        merged_weight = self._merge_theme_pack_defaults(team_setting.theme_pack_weight)
        if merged_weight != team_setting.theme_pack_weight:
            team_setting.theme_pack_weight = merged_weight
            self.save_team(team_num, team_setting)
        return copy.deepcopy(merged_weight)

    def _old_version_teams_config_upgrade(
        self,
        saved_version: int,
        loaded_config: dict,
        legacy_theme_pack_weight_path: str | Path | None = None,
    ) -> None:
        """旧版本队伍配置升级处理。

        只处理旧配置文件到新队伍 YAML 文件的迁移，不加载队伍到内存。
        """
        if saved_version >= TEAMS_CONFIG_UPGRADE_VERSION:
            return

        migrated = False
        if saved_version < 1768403022:
            self._migrate_legacy_mirror_history(loaded_config)
            migrated = True
        if saved_version < 1775826004:
            self._migrate_legacy_team_fields_to_teams(loaded_config)
            migrated = True
        if saved_version < 1778889600:
            self._migrate_legacy_team_setting_schema(loaded_config)
            migrated = True

        old_to_new_team_nums = self._migrate_config_teams_to_team_files(loaded_config)
        config_migrated_team_nums = set(old_to_new_team_nums.values()) if old_to_new_team_nums is not None else set()
        if old_to_new_team_nums:
            self._remap_legacy_team_queue(loaded_config, old_to_new_team_nums)
            migrated = True
        if config_migrated_team_nums:
            migrated = True
        if legacy_theme_pack_weight_path is not None:
            if self._migrate_legacy_team_weight_files(
                legacy_theme_pack_weight_path,
                config_migrated_team_nums,
                old_to_new_team_nums,
            ):
                migrated = True
        if migrated:
            log.info(f"队伍配置升级完成，旧配置版本: {saved_version}")

    def _migrate_legacy_mirror_history(self, loaded_config: dict) -> None:
        def _calculate_time_history(time_list: list[float], count: int) -> list[float]:
            if count == 0:
                return [0.0, 0.0, 0.0]
            if len(time_list) == 3 and count != 3:
                return time_list
            if len(time_list) == 3 and count == 3 and time_list[0] == time_list[1] == time_list[2]:
                return time_list

            total_avr = 0.0
            five_avr = 0.0
            ten_avr = 0.0
            for index in range(-1, -len(time_list) - 1, -1):
                total_avr += time_list[index]
                if index >= -5:
                    five_avr += time_list[index]
                if index >= -10:
                    ten_avr += time_list[index]
            total_avr /= count
            five_avr /= min(5, count)
            ten_avr /= min(10, count)
            return [total_avr, five_avr, ten_avr]

        team_count = len(loaded_config.get("teams_be_select", []) or [])
        for team_num in range(1, team_count + 1):
            history_key = f"team{team_num}_history"
            history = loaded_config.get(history_key, {}) or {}
            if not isinstance(history, dict):
                continue

            hard_count = history.get("mirror_hard_count", 0)
            normal_count = history.get("mirror_normal_count", 0)
            history["total_mirror_time_hard"] = _calculate_time_history(
                history.get("total_mirror_time_hard", []),
                hard_count,
            )
            history["mirror_hard_count"] = hard_count
            history["total_mirror_time_normal"] = _calculate_time_history(
                history.get("total_mirror_time_normal", []),
                normal_count,
            )
            history["mirror_normal_count"] = normal_count
            loaded_config[history_key] = history

    def _migrate_legacy_team_fields_to_teams(self, loaded_config: dict) -> None:
        teams: dict[str, dict] = {}
        for team_num in range(1, MAX_TEAM_COUNT + 1):
            settings = loaded_config.get(f"team{team_num}_setting")
            if not isinstance(settings, dict):
                continue

            team_data = copy.deepcopy(settings)
            history = loaded_config.get(f"team{team_num}_history", {}) or {}
            if isinstance(history, dict):
                team_data.update(history)
            team_data["remark_name"] = loaded_config.get(f"team{team_num}_remark_name")
            teams[str(team_num)] = team_data
        loaded_config["teams"] = teams

    def _migrate_legacy_team_setting_schema(self, loaded_config: dict) -> None:
        teams = loaded_config.get("teams", {}) or {}
        if not isinstance(teams, dict):
            return
        for team_key, settings in list(teams.items()):
            if isinstance(settings, dict):
                teams[team_key] = migrate_legacy_team_setting_data(settings)

    def _migrate_legacy_team_alias(self, settings: dict) -> dict:
        migrated_settings = copy.deepcopy(settings)
        if "alias" not in migrated_settings and isinstance(migrated_settings.get("remark_name"), str):
            migrated_settings["alias"] = migrated_settings["remark_name"]
        return migrated_settings

    def _migrate_config_teams_to_team_files(self, loaded_config: dict) -> dict[int, int] | None:
        teams = loaded_config.get("teams")
        if not isinstance(teams, dict):
            return None

        old_to_new_team_nums: dict[int, int] = {}
        used_new_team_nums: dict[int, int] = {}
        discarded_conflicts: list[tuple[int, int, int]] = []
        for team_key, settings in teams.items():
            try:
                old_team_num = int(team_key)
            except (TypeError, ValueError):
                continue
            if old_team_num < 1 or old_team_num > MAX_TEAM_COUNT or not isinstance(settings, dict):
                continue

            settings = self._migrate_legacy_team_alias(settings)
            new_team_num = settings.get("team_number", old_team_num)
            if type(new_team_num) is not int or new_team_num < 1 or new_team_num > MAX_TEAM_COUNT:
                new_team_num = old_team_num
            if new_team_num in used_new_team_nums:
                discarded_conflicts.append((old_team_num, used_new_team_nums[new_team_num], new_team_num))
                continue
            used_new_team_nums[new_team_num] = old_team_num
            old_to_new_team_nums[old_team_num] = new_team_num

            existing = self._load_raw_team_file(new_team_num)
            if existing:
                team_setting = self._normalize_team_data(new_team_num, existing)
                serialized = self._serialize_team(team_setting)
                if existing != serialized:
                    self._save_team_file(new_team_num, team_setting)
                continue

            team_setting = self._normalize_team_data(new_team_num, {"team_setting": settings})
            self._save_team_file(new_team_num, team_setting)
        if discarded_conflicts:
            details = "；".join(
                f"旧队伍配置 {discarded_old_team_num} 与旧队伍配置 {kept_old_team_num} "
                f"均映射到编队 {target_team_num}，已丢弃旧队伍配置 {discarded_old_team_num}"
                for discarded_old_team_num, kept_old_team_num, target_team_num in discarded_conflicts
            )
            log.warning(f"旧队伍配置迁移发现编队号冲突：{details}")
        return old_to_new_team_nums

    def _remap_legacy_team_queue(self, loaded_config: dict, old_to_new_team_nums: dict[int, int]) -> None:
        def _map_queue(queue: list[int]) -> list[int]:
            mapped_queue: list[int] = []
            seen: set[int] = set()
            for old_team_num in queue:
                if type(old_team_num) is not int:
                    continue
                new_team_num = old_to_new_team_nums.get(old_team_num)
                if new_team_num is None or new_team_num in seen:
                    continue
                mapped_queue.append(new_team_num)
                seen.add(new_team_num)
            return mapped_queue

        active_queue = loaded_config.get("teams_active_queue")
        if isinstance(active_queue, list):
            loaded_config["teams_active_queue"] = _map_queue(active_queue)
            return

        teams_order = loaded_config.get("teams_order", []) or []
        order_pairs: list[tuple[int, int]] = []
        used_orders: set[int] = set()
        for old_team_num in old_to_new_team_nums:
            order_index = old_team_num - 1
            if order_index >= len(teams_order):
                continue
            order = teams_order[order_index]
            if not isinstance(order, int) or order <= 0 or order in used_orders:
                continue
            order_pairs.append((order, old_team_num))
            used_orders.add(order)

        teams_be_select = loaded_config.get("teams_be_select", []) or []
        queue = [old_team_num for _, old_team_num in sorted(order_pairs)]
        queued_team_nums = set(queue)
        for old_team_num in old_to_new_team_nums:
            select_index = old_team_num - 1
            if select_index >= len(teams_be_select):
                continue
            if teams_be_select[select_index] is not True or old_team_num in queued_team_nums:
                continue
            queue.append(old_team_num)
        loaded_config["teams_active_queue"] = _map_queue(queue)

    def _migrate_legacy_team_weight_files(
        self,
        legacy_weight_path: str | Path,
        overwrite_team_nums: set[int] | None = None,
        old_to_new_team_nums: dict[int, int] | None = None,
    ) -> bool:
        """迁移旧版独立队伍主题包权重文件到对应的 TeamSetting。

        旧版权重文件位于 legacy_weight_path/theme_pack_weight_team_N.yaml。
        新版权重内嵌保存到 team_config/team_N.yaml 的
        team_setting.theme_pack_weight。若目标队伍已经有内嵌权重或旧格式顶层权重，
        说明该队伍已迁移或被用户配置过，此函数不会覆盖。
        """
        legacy_path = Path(legacy_weight_path)
        if not legacy_path.exists():
            return False

        overwrite_team_nums = overwrite_team_nums or set()
        migrated = False
        for weight_path in sorted(legacy_path.glob("theme_pack_weight_team_*.yaml"), key=lambda item: item.name):
            try:
                old_team_num = int(weight_path.stem.removeprefix("theme_pack_weight_team_"))
            except ValueError:
                continue
            if old_team_num < 1 or old_team_num > MAX_TEAM_COUNT:
                continue
            if old_to_new_team_nums is not None:
                team_num = old_to_new_team_nums.get(old_team_num)
                if team_num is None:
                    continue
            else:
                team_num = old_team_num
            if team_num < 1 or team_num > MAX_TEAM_COUNT:
                continue

            with open(weight_path, "r", encoding="utf-8") as file:
                weight_data: Any = self._yaml.load(file) or {}
            if not isinstance(weight_data, dict):
                continue

            raw_team_data = self._load_raw_team_file(team_num)
            if isinstance(raw_team_data, dict):
                # 避免用旧独立权重文件覆盖已经存在的队伍权重。
                embedded_weight = (raw_team_data.get("team_setting") or {}).get("theme_pack_weight")
                legacy_team_weight = raw_team_data.get("theme_pack_weight")
                if (embedded_weight or legacy_team_weight) and team_num not in overwrite_team_nums:
                    continue

            if isinstance(raw_team_data, dict):
                team_setting = self._normalize_team_data(team_num, raw_team_data)
            else:
                team_setting = self._build_default_team_setting(team_num)
            team_setting.theme_pack_weight = self._merge_theme_pack_defaults(weight_data)
            self._save_team_file(team_num, team_setting)
            log.info(f"已迁移旧主题包权重: {weight_path} -> team_config/team_{team_num}.yaml")
            backup_path = self._archive_legacy_team_weight_file(weight_path)
            log.info(f"已归档旧主题包权重文件: {weight_path} -> {backup_path}")
            migrated = True
        return migrated

    def _archive_legacy_team_weight_file(self, weight_path: Path) -> Path:
        """将已迁移的旧主题包权重文件移动到备份目录。"""
        backup_root = self._backup_path.parent if self._backup_path.name == "teams_config" else self._backup_path
        backup_dir = backup_root / "theme_pack_weight"
        backup_dir.mkdir(parents=True, exist_ok=True)

        target_path = backup_dir / weight_path.name
        if target_path.exists():
            timestamp = strftime("%Y%m%d_%H%M%S", localtime(time()))
            target_path = backup_dir / f"{weight_path.stem}_{timestamp}{weight_path.suffix}"

        shutil.move(str(weight_path), str(target_path))
        return target_path

    def _build_backup_snapshot(self) -> dict:
        return {"teams": {team_num: self.teams[team_num].model_dump() for team_num in sorted(self.teams)}}

    def backup_teams_config(self) -> None:
        """备份当前队伍配置到备份目录。"""
        if not self._backup_path.exists():
            self._backup_path.mkdir(parents=True, exist_ok=True)
        now_time = localtime(time())
        files = [f for f in self._backup_path.iterdir() if f.is_file() and f.suffix == ".yaml"]
        if files:
            files.sort(key=lambda f: f.stat().st_birthtime)
            latest_time = localtime(files[-1].stat().st_birthtime)
            if latest_time.tm_mday != now_time.tm_mday:
                backup_file = self._backup_path / f"teams_config_{strftime('%Y%m%d_%H%M%S', now_time)}.yaml"
                with open(backup_file, "w", encoding="utf-8") as file:
                    self._yaml.dump(self._build_backup_snapshot(), file)

            files = [f for f in self._backup_path.iterdir() if f.is_file() and f.suffix == ".yaml"]
            files.sort(key=lambda f: f.stat().st_birthtime)
            while len(files) > 10:
                try:
                    files[0].unlink()
                    files.pop(0)
                except Exception as e:
                    log.error(f"删除旧队伍配置备份文件 {files[0]} 失败: {e}")
                    break
        else:
            backup_file = self._backup_path / f"teams_config_{strftime('%Y%m%d_%H%M%S', now_time)}.yaml"
            with open(backup_file, "w", encoding="utf-8") as file:
                self._yaml.dump(self._build_backup_snapshot(), file)


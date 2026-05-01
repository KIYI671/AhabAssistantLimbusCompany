import datetime
import re
from pathlib import Path
from typing import Optional

from ruamel.yaml import YAML
from pydantic import ValidationError

from module.config import cfg, theme_list
from module.config.config_typing import TeamSetting
from module.logger import log


def generate_team_export_filename(team_num: int) -> str:
    """生成队伍设置导出文件名"""
    team_setting = cfg.config.teams.get(str(team_num))
    remark_name = team_setting.remark_name if team_setting else None

    date_str = datetime.date.today().isoformat()

    if remark_name:
        safe_name = re.sub(r'[<>:"/\\|?*]', '_', remark_name)
        return f"team_settings_{safe_name}_{date_str}.yaml"
    else:
        return f"team_settings_team_{team_num}_{date_str}.yaml"


def export_team_settings(team_num: int, file_path: str) -> bool:
    """导出队伍设置到 YAML 文件"""
    try:
        team_setting = cfg.config.teams.get(str(team_num))
        if not team_setting:
            log.error(f"队伍 {team_num} 未找到")
            return False

        yaml = YAML()
        export_data = team_setting.model_dump()

        # 从导出中排除统计字段和队伍编号
        stats_fields = ['total_mirror_time_hard', 'mirror_hard_count',
                       'total_mirror_time_normal', 'mirror_normal_count', 'team_number']
        for field in stats_fields:
            export_data.pop(field, None)

        theme_pack_weight_path = theme_list.build_team_weight_path(team_num)
        if Path(theme_pack_weight_path).exists():
            with open(theme_pack_weight_path, 'r', encoding='utf-8') as f:
                theme_pack_data = yaml.load(f)
                if theme_pack_data:
                    export_data['custom_theme_pack_weight'] = theme_pack_data

        with open(file_path, 'w', encoding='utf-8') as f:
            yaml.dump(export_data, f)

        log.info(f"已导出队伍 {team_num} 设置到 {file_path}")
        return True
    except Exception as e:
        log.error(f"导出队伍设置失败: {e}")
        return False


def import_team_settings(file_path: str, team_num: int) -> tuple[Optional[TeamSetting], Optional[dict], list[str]]:
    """从 YAML 文件导入队伍设置

    Args:
        file_path: 要导入的 YAML 文件路径
        team_num: 队伍编号（用于上下文，不用于验证）

    Returns:
        元组 (TeamSetting, theme_pack_weight, missing_fields)
        - TeamSetting: 解析的队伍设置，如果解析失败则为 None
        - theme_pack_weight: 自定义主题包权重字典（如果存在），否则为 None
        - missing_fields: 缺失的必需字段列表，如果所有字段都存在则为空列表
    """
    try:
        yaml = YAML()
        with open(file_path, 'r', encoding='utf-8') as f:
            data = yaml.load(f)

        if not data:
            return None, None, ["文件为空"]

        theme_pack_weight = data.pop('custom_theme_pack_weight', None)

        try:
            team_setting = TeamSetting(**data)
            return team_setting, theme_pack_weight, []
        except ValidationError as e:
            missing_fields = [err['loc'][0] for err in e.errors() if err['type'] == 'missing']
            if missing_fields:
                # 使用 model_construct 为缺失字段创建默认值
                team_setting = TeamSetting.model_construct(**data)
                return team_setting, theme_pack_weight, missing_fields
            else:
                log.error(f"验证错误: {e}")
                return None, None, [str(e)]
    except Exception as e:
        log.error(f"导入队伍设置失败: {e}")
        return None, None, [str(e)]


def apply_team_settings(team_num: int, team_setting: TeamSetting, theme_pack_weight: Optional[dict]) -> None:
    """应用导入的队伍设置到配置"""
    cfg.config.teams[str(team_num)] = team_setting

    if theme_pack_weight:
        theme_pack_weight_path = Path(theme_list.build_team_weight_path(team_num))
        theme_pack_weight_path.parent.mkdir(parents=True, exist_ok=True)

        yaml = YAML()
        with open(theme_pack_weight_path, 'w', encoding='utf-8') as f:
            yaml.dump(theme_pack_weight, f)

        log.info(f"已创建/更新队伍 {team_num} 的主题包权重文件")

    cfg.save()
    log.info(f"已应用队伍 {team_num} 的设置")

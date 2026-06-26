import base64
import datetime
from pathlib import Path

from ruamel.yaml import YAML

from module.config import cfg, theme_list
from module.logger import log
from utils.file_utils import sanitize_filename


def generate_theme_pack_export_filename(team_num: int) -> str:
    """生成主题包权重导出文件名。"""
    team_setting = cfg.config.teams.get(str(team_num))
    remark_name = team_setting.remark_name if team_setting else None
    date_str = datetime.date.today().isoformat()

    if remark_name:
        safe_name = sanitize_filename(remark_name)
        return f"theme_pack_weight_team_{safe_name}_{date_str}.yaml"

    return f"theme_pack_weight_team_{team_num}_{date_str}.yaml"


def export_theme_pack_weight(team_num: int, file_path: str) -> bool:
    """导出主题包权重到 YAML 文件。"""
    try:
        theme_pack_weight_path = theme_list.build_team_weight_path(team_num)

        if not Path(theme_pack_weight_path).exists():
            log.error(f"队伍 {team_num} 的主题包权重文件未找到")
            return False

        yaml = YAML()
        with open(theme_pack_weight_path, "r", encoding="utf-8") as file:
            theme_pack_data = yaml.load(file)

        if not theme_pack_data:
            log.error(f"队伍 {team_num} 的主题包权重文件为空")
            return False

        with open(file_path, "w", encoding="utf-8") as file:
            yaml.dump(theme_pack_data, file)

        log.info(f"已导出队伍 {team_num} 的主题包权重到 {file_path}")
        return True
    except Exception as exc:
        log.error(f"导出主题包权重失败: {exc}")
        return False


def _deep_merge_dicts(existing: dict, import_data: dict) -> dict:
    """深度合并字典，将 import_data 合并到 existing。"""
    result = existing.copy()
    for key, value in import_data.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge_dicts(result[key], value)
        else:
            result[key] = value
    return result


def _load_existing_theme_pack_weight(team_num: int) -> tuple[Path, dict]:
    """加载队伍当前的主题包权重数据。"""
    yaml = YAML()
    target_path = Path(theme_list.build_team_weight_path(team_num))

    if not target_path.exists():
        return target_path, {}

    with open(target_path, "r", encoding="utf-8") as file:
        existing_data = yaml.load(file) or {}

    return target_path, existing_data


def _import_theme_pack_weight_data(
    import_data: object,
    team_num: int,
    *,
    success_message: str | None = None,
    invalid_data_message: str | None = None,
) -> bool:
    """将导入的主题包权重合并到目标队伍并保存。"""
    if not isinstance(import_data, dict):
        log.error(invalid_data_message or f"队伍 {team_num} 的导入数据不是字典")
        return False

    yaml = YAML()
    target_path, existing_data = _load_existing_theme_pack_weight(team_num)
    merged_data = _deep_merge_dicts(existing_data, import_data)

    target_path.parent.mkdir(parents=True, exist_ok=True)
    with open(target_path, "w", encoding="utf-8") as file:
        yaml.dump(merged_data, file)

    if success_message:
        log.info(success_message)

    return True


def import_theme_pack_weight(file_path: str, team_num: int) -> bool:
    """从 YAML 文件导入主题包权重。"""
    try:
        yaml = YAML()
        with open(file_path, "r", encoding="utf-8") as file:
            import_data = yaml.load(file)

        if not import_data:
            log.warning(f"队伍 {team_num} 的导入文件为空")
            return True

        return _import_theme_pack_weight_data(
            import_data,
            team_num,
            success_message=f"已从 {file_path} 导入队伍 {team_num} 的主题包权重",
            invalid_data_message=f"队伍 {team_num} 的导入数据不是字典",
        )
    except Exception as exc:
        log.error(f"导入主题包权重失败: {exc}")
        return False


def export_theme_pack_weight_to_base64(team_num: int) -> str | None:
    """导出主题包权重为 Base64 配置码。"""
    try:
        theme_pack_weight_path = theme_list.build_team_weight_path(team_num)
        if not Path(theme_pack_weight_path).exists():
            log.error(f"队伍 {team_num} 的主题包权重文件未找到")
            return None

        with open(theme_pack_weight_path, "r", encoding="utf-8") as file:
            yaml_content = file.read()

        if not yaml_content.strip():
            log.error(f"队伍 {team_num} 的主题包权重文件为空")
            return None

        encoded = base64.b64encode(yaml_content.encode("utf-8")).decode("ascii")
        log.info(f"已导出队伍 {team_num} 的主题包权重为配置码")
        return encoded
    except Exception as exc:
        log.error(f"导出主题包权重配置码失败: {exc}")
        return None


def import_theme_pack_weight_from_base64(base64_str: str, team_num: int) -> bool:
    """从 Base64 配置码导入主题包权重。"""
    try:
        try:
            yaml_content = base64.b64decode(base64_str).decode("utf-8")
        except (base64.binascii.Error, UnicodeDecodeError) as exc:
            log.error(f"配置码解码失败: {exc}")
            return False

        if not yaml_content.strip():
            log.warning("导入的配置码数据为空")
            return False

        yaml = YAML()
        import_data = yaml.load(yaml_content)
        if not import_data:
            log.warning("解析配置码数据后主题包权重为空")
            return True

        return _import_theme_pack_weight_data(
            import_data,
            team_num,
            success_message=f"已从配置码导入队伍 {team_num} 的主题包权重",
            invalid_data_message=f"队伍 {team_num} 的导入配置码数据不是字典",
        )
    except Exception as exc:
        log.error(f"从配置码导入主题包权重失败: {exc}")
        return False

import base64
import datetime
import re
from pathlib import Path

from ruamel.yaml import YAML

from module.config import cfg, theme_list
from module.logger import log


def generate_theme_pack_export_filename(team_num: int) -> str:
    """生成主题包权重导出文件名

    Args:
        team_num: 队伍编号

    Returns:
        格式为 theme_pack_weight_team_{remark_name}_{date}.yaml 的文件名
        如果没有备注名则为 theme_pack_weight_team_{team_num}_{date}.yaml
    """
    team_setting = cfg.config.teams.get(str(team_num))
    remark_name = team_setting.remark_name if team_setting else None

    date_str = datetime.date.today().isoformat()

    if remark_name:
        safe_name = re.sub(r'[<>:"/\\|?*]', "_", remark_name)
        return f"theme_pack_weight_team_{safe_name}_{date_str}.yaml"
    else:
        return f"theme_pack_weight_team_{team_num}_{date_str}.yaml"


def export_theme_pack_weight(team_num: int, file_path: str) -> bool:
    """导出主题包权重到 YAML 文件

    Args:
        team_num: 队伍编号
        file_path: 导出主题包权重的路径

    Returns:
        成功返回 True，失败返回 False
    """
    try:
        theme_pack_weight_path = theme_list.build_team_weight_path(team_num)

        if not Path(theme_pack_weight_path).exists():
            log.error(f"队伍 {team_num} 的主题包权重文件未找到")
            return False

        yaml = YAML()
        with open(theme_pack_weight_path, "r", encoding="utf-8") as f:
            theme_pack_data = yaml.load(f)

        if not theme_pack_data:
            log.error(f"队伍 {team_num} 的主题包权重文件为空")
            return False

        with open(file_path, "w", encoding="utf-8") as f:
            yaml.dump(theme_pack_data, f)

        log.info(f"已导出队伍 {team_num} 的主题包权重到 {file_path}")
        return True
    except Exception as e:
        log.error(f"导出主题包权重失败: {e}")
        return False


def _deep_merge_dicts(existing: dict, import_data: dict) -> dict:
    """深度合并字典，将 import_data 合并到 existing

    Args:
        existing: 现有字典
        import_data: 要合并的字典

    Returns:
        合并后的字典
    """
    result = existing.copy()
    for key, value in import_data.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge_dicts(result[key], value)
        else:
            result[key] = value
    return result


def import_theme_pack_weight(file_path: str, team_num: int) -> bool:
    """从 YAML 文件导入主题包权重

    Args:
        file_path: 要导入的 YAML 文件路径
        team_num: 队伍编号（用于上下文）

    Returns:
        成功返回 True，失败返回 False
    """
    try:
        yaml = YAML()

        # 加载导入数据
        with open(file_path, "r", encoding="utf-8") as f:
            import_data = yaml.load(f)

        if not import_data:
            log.warning(f"队伍 {team_num} 的导入文件为空")
            return True

        # 加载现有主题包权重或创建空字典
        theme_pack_weight_path = theme_list.build_team_weight_path(team_num)
        target_path = Path(theme_pack_weight_path)

        if target_path.exists():
            with open(theme_pack_weight_path, "r", encoding="utf-8") as f:
                existing_data = yaml.load(f)
                if not existing_data:
                    existing_data = {}
        else:
            existing_data = {}

        # 从导入中合并/替换条目
        if isinstance(import_data, dict):
            existing_data = _deep_merge_dicts(existing_data, import_data)
        else:
            log.error(f"队伍 {team_num} 的导入数据不是字典")
            return False

        # 确保父目录存在
        target_path.parent.mkdir(parents=True, exist_ok=True)

        # 保存回 theme_pack_weight_team_{team_num}.yaml
        with open(theme_pack_weight_path, "w", encoding="utf-8") as f:
            yaml.dump(existing_data, f)

        log.info(f"已从 {file_path} 导入队伍 {team_num} 的主题包权重")
        return True
    except Exception as e:
        log.error(f"导入主题包权重失败: {e}")
        return False


# =============================================================================
# 以下两个函数为新增：配置码（Base64）导入/导出
# 可将队伍的主题包权重 YAML 编码为 Base64 字符串，方便通过剪贴板分享
# =============================================================================


def export_theme_pack_weight_to_base64(team_num: int) -> str | None:
    """导出主题包权重为 Base64 编码字符串

    将队伍的主题包权重 YAML 内容编码为 Base64 字符串，
    方便通过剪贴板分享。

    Args:
        team_num: 队伍编号

    Returns:
        Base64 编码字符串，失败返回 None
    """
    try:
        theme_pack_weight_path = theme_list.build_team_weight_path(team_num)

        if not Path(theme_pack_weight_path).exists():
            log.error(f"队伍 {team_num} 的主题包权重文件未找到")
            return None

        with open(theme_pack_weight_path, "r", encoding="utf-8") as f:
            yaml_content = f.read()

        if not yaml_content.strip():
            log.error(f"队伍 {team_num} 的主题包权重文件为空")
            return None

        # 将 YAML 文本编码为 Base64
        encoded = base64.b64encode(yaml_content.encode("utf-8")).decode("ascii")
        log.info(f"已导出队伍 {team_num} 的主题包权重为 Base64")
        return encoded
    except Exception as e:
        log.error(f"导出主题包权重 Base64 失败: {e}")
        return None


def import_theme_pack_weight_from_base64(base64_str: str, team_num: int) -> bool:
    """从 Base64 编码字符串导入主题包权重

    Args:
        base64_str: Base64 编码的主题包权重数据
        team_num: 队伍编号

    Returns:
        成功返回 True，失败返回 False
    """
    try:
        # 解码 Base64 字符串
        try:
            yaml_content = base64.b64decode(base64_str).decode("utf-8")
        except (base64.binascii.Error, UnicodeDecodeError) as e:
            log.error(f"Base64 解码失败: {e}")
            return False

        if not yaml_content.strip():
            log.warning("导入的 Base64 数据为空")
            return False

        yaml = YAML()
        import_data = yaml.load(yaml_content)

        if not import_data:
            log.warning("解析 Base64 数据后主题包权重为空")
            return True

        # 加载现有主题包权重或创建空字典
        theme_pack_weight_path = theme_list.build_team_weight_path(team_num)
        target_path = Path(theme_pack_weight_path)

        if target_path.exists():
            with open(theme_pack_weight_path, "r", encoding="utf-8") as f:
                existing_data = yaml.load(f)
                if not existing_data:
                    existing_data = {}
        else:
            existing_data = {}

        # 从导入中合并/替换条目
        if isinstance(import_data, dict):
            existing_data = _deep_merge_dicts(existing_data, import_data)
        else:
            log.error(f"队伍 {team_num} 的导入 Base64 数据不是字典")
            return False

        # 确保父目录存在
        target_path.parent.mkdir(parents=True, exist_ok=True)

        # 保存回 theme_pack_weight_team_{team_num}.yaml
        with open(theme_pack_weight_path, "w", encoding="utf-8") as f:
            yaml.dump(existing_data, f)

        log.info(f"已从 Base64 导入队伍 {team_num} 的主题包权重")
        return True
    except Exception as e:
        log.error(f"从 Base64 导入主题包权重失败: {e}")
        return False

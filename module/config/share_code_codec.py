from __future__ import annotations

import base64
import gzip
import re
from copy import deepcopy
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML

from .config_typing import TeamSetting


REPO_ROOT = Path(__file__).resolve().parents[2]
THEME_WEIGHT_MIN = -10
THEME_WEIGHT_MAX = 10
THEME_WEIGHT_OFFSET = 10
THEME_WEIGHT_WIDTH = 5
TEAM_KIND = "T"
WEIGHT_KIND = "W"

STAT_KEYS = {
    "total_mirror_time_hard",
    "mirror_hard_count",
    "total_mirror_time_normal",
    "mirror_normal_count",
}
OMIT_ALWAYS = {"chosen_sinners", "sinners_be_select"}
INT_WIDTHS = {
    "team_system": 4,
    "shop_strategy": 2,
    "fixed_team_use_select": 1,
    "reward_cards_select": 2,
    "after_level_IV_select": 2,
    "shopping_strategy_select": 3,
    "opening_items_select": 3,
    "opening_items_system": 4,
    "second_system_select": 4,
    "second_system_setting": 1,
    "skill_replacement_select": 2,
    "skill_replacement_mode": 2,
    "max_keyword_refresh": 3,
    "max_normal_refresh": 3,
}
OBSERVE_SYSTEMS = (
    "burn",
    "bleed",
    "tremor",
    "rupture",
    "sinking",
    "poise",
    "charge",
    "slash",
    "pierce",
    "blunt",
    "general",
)
OBSERVE_PATTERN = re.compile(r"^([a-z]+)_(\d+)_(\d+)_(\d+)$")


def encode_theme_pack_weight(weight: dict[str, Any]) -> str:
    """编码主题卡包权重；输入/输出对接 TeamConfig 的裸 weight dict。"""
    version = re.sub(
        r"[^0-9A-Za-z_.-]+",
        "_",
        (REPO_ROOT / "assets" / "config" / "version.txt").read_text(encoding="utf-8").strip(),
    ).strip("_") or "UNKNOWN_VERSION"
    yaml = YAML(typ="safe")
    merged = deepcopy(yaml.load((REPO_ROOT / "theme_pack_list.yaml").read_text(encoding="utf-8")) or {})

    # 合并默认主题卡包权重，保证旧配置缺少的新 key 也按固定顺序参与编码。
    stack = [(merged, weight if isinstance(weight, dict) else {})]
    while stack:
        dst, src = stack.pop()
        for key, value in src.items():
            if isinstance(value, dict) and isinstance(dst.get(key), dict):
                stack.append((dst[key], value))
            else:
                dst[key] = deepcopy(value)

    # 按默认模板的插入顺序展开权重，每个 -10..10 权重用 5 bit 存储。
    bits: list[int] = []
    stack = [merged]
    values: list[int] = []
    while stack:
        current = stack.pop()
        if isinstance(current, dict):
            for child in reversed(list(current.values())):
                stack.append(child)
        else:
            values.append(int(current))

    for value in values:
        if value < THEME_WEIGHT_MIN or value > THEME_WEIGHT_MAX:
            raise ValueError(f"主题卡包权重超出 [{THEME_WEIGHT_MIN}, {THEME_WEIGHT_MAX}]: {value}")
        packed_value = value + THEME_WEIGHT_OFFSET
        for shift in range(THEME_WEIGHT_WIDTH):
            bits.append((packed_value >> shift) & 1)

    payload = bytearray()
    for offset in range(0, len(bits), 8):
        byte = 0
        for shift, bit in enumerate(bits[offset : offset + 8]):
            byte |= bit << shift
        payload.append(byte)

    compressed = gzip.compress(bytes(payload), compresslevel=9, mtime=0)
    encoded = base64.urlsafe_b64encode(compressed).decode("ascii").rstrip("=")
    return f"{version}:{WEIGHT_KIND}:{encoded}"


def decode_theme_pack_weight(code: str) -> dict[str, Any]:
    """解码主题卡包权重；返回值可直接传给 save_team_theme_pack_weight。"""
    version = re.sub(
        r"[^0-9A-Za-z_.-]+",
        "_",
        (REPO_ROOT / "assets" / "config" / "version.txt").read_text(encoding="utf-8").strip(),
    ).strip("_") or "UNKNOWN_VERSION"
    parts = code.strip().split(":", 2)
    if len(parts) != 3:
        raise ValueError("压缩码格式不正确")
    code_version, kind, payload_text = parts
    if code_version != version:
        raise ValueError(f"版本不匹配: 压缩码={code_version}, 当前={version}")
    if kind != WEIGHT_KIND:
        raise ValueError(f"压缩码类型不匹配: 压缩码={kind}, 期望={WEIGHT_KIND}")

    data = gzip.decompress(base64.urlsafe_b64decode(payload_text + "=" * (-len(payload_text) % 4)))
    yaml = YAML(typ="safe")
    template = yaml.load((REPO_ROOT / "theme_pack_list.yaml").read_text(encoding="utf-8")) or {}

    # 按模板顺序读回 5 bit 权重，并重建为原来的嵌套 dict 形状。
    bit_pos = 0
    restored: dict[str, Any] = {}
    weight_paths: list[list[Any]] = []
    stack = [([], template)]
    while stack:
        path, current = stack.pop()
        if isinstance(current, dict):
            for key, value in reversed(list(current.items())):
                stack.append((path + [key], value))
        else:
            weight_paths.append(path)

    for path in weight_paths:
        packed_value = 0
        for shift in range(THEME_WEIGHT_WIDTH):
            if bit_pos >= len(data) * 8:
                raise ValueError("bitpack 数据过短")
            packed_value |= ((data[bit_pos // 8] >> (bit_pos % 8)) & 1) << shift
            bit_pos += 1
        dst = restored
        for key in path[:-1]:
            dst = dst.setdefault(key, {})
        dst[path[-1]] = packed_value - THEME_WEIGHT_OFFSET
    return restored


def encode_team_setting(team_data: dict[str, Any], slot: int | None = None) -> str:
    """编码完整编队配置；输入对接 TeamConfig.copy_team() 的 model_dump dict。"""
    version = re.sub(
        r"[^0-9A-Za-z_.-]+",
        "_",
        (REPO_ROOT / "assets" / "config" / "version.txt").read_text(encoding="utf-8").strip(),
    ).strip("_") or "UNKNOWN_VERSION"
    yaml = YAML(typ="safe")
    team_setting = TeamSetting(**team_data.get("team_setting", team_data)).model_dump()
    team_slot = int(slot if slot is not None else team_setting.get("team_number", 0))

    # 主题权重先补齐默认模板，再随完整编队一起编码。
    merged_weight = deepcopy(yaml.load((REPO_ROOT / "theme_pack_list.yaml").read_text(encoding="utf-8")) or {})
    stack = [(merged_weight, team_setting.get("theme_pack_weight"))]
    while stack:
        dst, src = stack.pop()
        if not isinstance(src, dict):
            continue
        for key, value in src.items():
            if isinstance(value, dict) and isinstance(dst.get(key), dict):
                stack.append((dst[key], value))
            else:
                dst[key] = deepcopy(value)
    team_setting["theme_pack_weight"] = merged_weight

    bits: list[int] = []

    # 写入目标队伍槽位。
    for shift in range(5):
        bits.append((team_slot >> shift) & 1)

    # 按 TeamSetting 字段顺序编码；chosen_sinners/sinners_be_select 由 sinner_order 反推。
    field_order = [
        key
        for key in TeamSetting.model_fields
        if key not in STAT_KEYS and key != "team_number" and key not in OMIT_ALWAYS
    ]
    for key in field_order:
        value = team_setting[key]
        if isinstance(value, bool):
            bits.append(1 if value else 0)
        elif key in INT_WIDTHS:
            int_value = int(value)
            if int_value < 0 or int_value >= (1 << INT_WIDTHS[key]):
                raise ValueError(f"{key}={int_value} does not fit in {INT_WIDTHS[key]} bits")
            for shift in range(INT_WIDTHS[key]):
                bits.append((int_value >> shift) & 1)
        elif key == "sinner_order":
            ordered_positions = [
                position
                for _, position in sorted((int(order), position) for position, order in enumerate(value) if int(order) > 0)
            ]
            if len(ordered_positions) >= 16:
                raise ValueError("sinner_order 选择数量不能超过 15")
            for shift in range(4):
                bits.append((len(ordered_positions) >> shift) & 1)
            for position in ordered_positions:
                for shift in range(4):
                    bits.append((position >> shift) & 1)
        elif key == "opening_bonus":
            for item in value:
                int_value = int(item)
                if int_value < 0 or int_value >= 4:
                    raise ValueError(f"opening_bonus={int_value} does not fit in 2 bits")
                for shift in range(2):
                    bits.append((int_value >> shift) & 1)
        elif key in ("second_system_action", "ignore_shop"):
            for item in value:
                bits.append(1 if int(item) else 0)
        elif key == "observe_ego_gift_selected":
            if len(value) >= 4:
                raise ValueError("observe_ego_gift_selected 数量不能超过 3")
            for shift in range(2):
                bits.append((len(value) >> shift) & 1)
            for item in value:
                match = OBSERVE_PATTERN.match(item)
                if match and match.group(1) in OBSERVE_SYSTEMS:
                    bits.append(1)
                    parts = [
                        (OBSERVE_SYSTEMS.index(match.group(1)), 4),
                        (int(match.group(2)) - 1, 2),
                        (int(match.group(3)) - 1, 4),
                        (int(match.group(4)) - 1, 3),
                    ]
                    for int_value, width in parts:
                        if int_value < 0 or int_value >= (1 << width):
                            raise ValueError(f"observe_ego_gift_selected={item} 超出编码范围")
                        for shift in range(width):
                            bits.append((int_value >> shift) & 1)
                else:
                    bits.append(0)
                    encoded = item.encode("utf-8")
                    if len(encoded) >= 64:
                        raise ValueError("observe_ego_gift_selected 自定义值过长")
                    for shift in range(6):
                        bits.append((len(encoded) >> shift) & 1)
                    for byte in encoded:
                        for shift in range(8):
                            bits.append((byte >> shift) & 1)
        elif key in ("alias", "team_code"):
            encoded = (value or "").encode("utf-8")
            width = 8 if key == "alias" else 16
            if len(encoded) >= (1 << width):
                raise ValueError(f"{key} 过长")
            for shift in range(width):
                bits.append((len(encoded) >> shift) & 1)
            for byte in encoded:
                for shift in range(8):
                    bits.append((byte >> shift) & 1)
        elif key == "theme_pack_weight":
            stack = [value]
            weights: list[int] = []
            while stack:
                current = stack.pop()
                if isinstance(current, dict):
                    for child in reversed(list(current.values())):
                        stack.append(child)
                else:
                    weights.append(int(current))
            for weight in weights:
                if weight < THEME_WEIGHT_MIN or weight > THEME_WEIGHT_MAX:
                    raise ValueError(f"主题卡包权重超出 [{THEME_WEIGHT_MIN}, {THEME_WEIGHT_MAX}]: {weight}")
                packed_value = weight + THEME_WEIGHT_OFFSET
                for shift in range(THEME_WEIGHT_WIDTH):
                    bits.append((packed_value >> shift) & 1)
        else:
            raise ValueError(f"未支持的字段: {key}")

    payload = bytearray()
    for offset in range(0, len(bits), 8):
        byte = 0
        for shift, bit in enumerate(bits[offset : offset + 8]):
            byte |= bit << shift
        payload.append(byte)

    compressed = gzip.compress(bytes(payload), compresslevel=9, mtime=0)
    encoded = base64.urlsafe_b64encode(compressed).decode("ascii").rstrip("=")
    return f"{version}:{TEAM_KIND}:{encoded}"


def decode_team_setting(code: str) -> dict[str, Any]:
    """解码完整编队配置；返回值可直接传给 TeamConfig.paste_team。"""
    version = re.sub(
        r"[^0-9A-Za-z_.-]+",
        "_",
        (REPO_ROOT / "assets" / "config" / "version.txt").read_text(encoding="utf-8").strip(),
    ).strip("_") or "UNKNOWN_VERSION"
    parts = code.strip().split(":", 2)
    if len(parts) != 3:
        raise ValueError("压缩码格式不正确")
    code_version, kind, payload_text = parts
    if code_version != version:
        raise ValueError(f"版本不匹配: 压缩码={code_version}, 当前={version}")
    if kind != TEAM_KIND:
        raise ValueError(f"压缩码类型不匹配: 压缩码={kind}, 期望={TEAM_KIND}")

    data = gzip.decompress(base64.urlsafe_b64decode(payload_text + "=" * (-len(payload_text) % 4)))
    bit_pos = 0
    restored = TeamSetting().model_dump()
    for key in STAT_KEYS:
        restored.pop(key, None)

    # 先读槽位，再按 TeamSetting 字段顺序还原。
    team_slot = 0
    for shift in range(5):
        if bit_pos >= len(data) * 8:
            raise ValueError("bitpack 数据过短")
        team_slot |= ((data[bit_pos // 8] >> (bit_pos % 8)) & 1) << shift
        bit_pos += 1
    restored["team_number"] = team_slot

    yaml = YAML(typ="safe")
    theme_template = yaml.load((REPO_ROOT / "theme_pack_list.yaml").read_text(encoding="utf-8")) or {}
    default_template = deepcopy(restored)
    default_template["theme_pack_weight"] = theme_template
    field_order = [
        key
        for key in TeamSetting.model_fields
        if key not in STAT_KEYS and key != "team_number" and key not in OMIT_ALWAYS
    ]

    for key in field_order:
        template_value = default_template[key]
        if isinstance(template_value, bool):
            if bit_pos >= len(data) * 8:
                raise ValueError("bitpack 数据过短")
            restored[key] = bool((data[bit_pos // 8] >> (bit_pos % 8)) & 1)
            bit_pos += 1
        elif key in INT_WIDTHS:
            int_value = 0
            for shift in range(INT_WIDTHS[key]):
                if bit_pos >= len(data) * 8:
                    raise ValueError("bitpack 数据过短")
                int_value |= ((data[bit_pos // 8] >> (bit_pos % 8)) & 1) << shift
                bit_pos += 1
            restored[key] = int_value
        elif key == "sinner_order":
            count = 0
            for shift in range(4):
                if bit_pos >= len(data) * 8:
                    raise ValueError("bitpack 数据过短")
                count |= ((data[bit_pos // 8] >> (bit_pos % 8)) & 1) << shift
                bit_pos += 1
            order = [0] * 12
            for selected_order in range(1, count + 1):
                position = 0
                for shift in range(4):
                    if bit_pos >= len(data) * 8:
                        raise ValueError("bitpack 数据过短")
                    position |= ((data[bit_pos // 8] >> (bit_pos % 8)) & 1) << shift
                    bit_pos += 1
                if position >= len(order):
                    raise ValueError(f"罪人位置超出范围: {position}")
                order[position] = selected_order
            restored[key] = order
        elif key == "opening_bonus":
            restored[key] = []
            for _ in range(len(template_value)):
                int_value = 0
                for shift in range(2):
                    if bit_pos >= len(data) * 8:
                        raise ValueError("bitpack 数据过短")
                    int_value |= ((data[bit_pos // 8] >> (bit_pos % 8)) & 1) << shift
                    bit_pos += 1
                restored[key].append(int_value)
        elif key in ("second_system_action", "ignore_shop"):
            restored[key] = []
            for _ in range(len(template_value)):
                if bit_pos >= len(data) * 8:
                    raise ValueError("bitpack 数据过短")
                restored[key].append((data[bit_pos // 8] >> (bit_pos % 8)) & 1)
                bit_pos += 1
        elif key == "observe_ego_gift_selected":
            count = 0
            for shift in range(2):
                if bit_pos >= len(data) * 8:
                    raise ValueError("bitpack 数据过短")
                count |= ((data[bit_pos // 8] >> (bit_pos % 8)) & 1) << shift
                bit_pos += 1
            values = []
            for _ in range(count):
                if bit_pos >= len(data) * 8:
                    raise ValueError("bitpack 数据过短")
                is_structured = (data[bit_pos // 8] >> (bit_pos % 8)) & 1
                bit_pos += 1
                if is_structured:
                    parsed = []
                    for width in (4, 2, 4, 3):
                        int_value = 0
                        for shift in range(width):
                            if bit_pos >= len(data) * 8:
                                raise ValueError("bitpack 数据过短")
                            int_value |= ((data[bit_pos // 8] >> (bit_pos % 8)) & 1) << shift
                            bit_pos += 1
                        parsed.append(int_value)
                    values.append(f"{OBSERVE_SYSTEMS[parsed[0]]}_{parsed[1] + 1}_{parsed[2] + 1}_{parsed[3] + 1}")
                else:
                    length = 0
                    for shift in range(6):
                        if bit_pos >= len(data) * 8:
                            raise ValueError("bitpack 数据过短")
                        length |= ((data[bit_pos // 8] >> (bit_pos % 8)) & 1) << shift
                        bit_pos += 1
                    raw = bytearray()
                    for _ in range(length):
                        byte = 0
                        for shift in range(8):
                            if bit_pos >= len(data) * 8:
                                raise ValueError("bitpack 数据过短")
                            byte |= ((data[bit_pos // 8] >> (bit_pos % 8)) & 1) << shift
                            bit_pos += 1
                        raw.append(byte)
                    values.append(bytes(raw).decode("utf-8"))
            restored[key] = values
        elif key in ("alias", "team_code"):
            width = 8 if key == "alias" else 16
            length = 0
            for shift in range(width):
                if bit_pos >= len(data) * 8:
                    raise ValueError("bitpack 数据过短")
                length |= ((data[bit_pos // 8] >> (bit_pos % 8)) & 1) << shift
                bit_pos += 1
            raw = bytearray()
            for _ in range(length):
                byte = 0
                for shift in range(8):
                    if bit_pos >= len(data) * 8:
                        raise ValueError("bitpack 数据过短")
                    byte |= ((data[bit_pos // 8] >> (bit_pos % 8)) & 1) << shift
                    bit_pos += 1
                raw.append(byte)
            restored[key] = bytes(raw).decode("utf-8")
            if key == "alias" and restored[key] == "":
                restored[key] = None
        elif key == "theme_pack_weight":
            weight = {}
            weight_paths: list[list[Any]] = []
            stack = [([], theme_template)]
            while stack:
                path, current = stack.pop()
                if isinstance(current, dict):
                    for weight_key, weight_value in reversed(list(current.items())):
                        stack.append((path + [weight_key], weight_value))
                else:
                    weight_paths.append(path)
            for path in weight_paths:
                packed_value = 0
                for shift in range(THEME_WEIGHT_WIDTH):
                    if bit_pos >= len(data) * 8:
                        raise ValueError("bitpack 数据过短")
                    packed_value |= ((data[bit_pos // 8] >> (bit_pos % 8)) & 1) << shift
                    bit_pos += 1
                dst = weight
                for weight_key in path[:-1]:
                    dst = dst.setdefault(weight_key, {})
                dst[path[-1]] = packed_value - THEME_WEIGHT_OFFSET
            restored[key] = weight
        else:
            raise ValueError(f"未支持的字段: {key}")

    restored["chosen_sinners"] = [1 if int(order) > 0 else 0 for order in restored["sinner_order"]]
    restored["sinners_be_select"] = sum(restored["chosen_sinners"])
    return restored

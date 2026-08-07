from __future__ import annotations

import ipaddress
import re

_HOSTNAME_LABEL = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?$")


def normalize_adb_host(value: str) -> str:
    """校验并规范化 ADB 目标主机名或 IP 地址。"""
    host = str(value).strip()
    if host.startswith("[") and host.endswith("]"):
        host = host[1:-1].strip()

    if not host:
        raise ValueError("模拟器主机地址不能为空")
    if "://" in host or any(char in host for char in ("/", "\\", "?", "#")):
        raise ValueError("请只填写主机名或 IP 地址，不要包含协议、路径或端口")

    try:
        return ipaddress.ip_address(host).compressed
    except ValueError:
        pass

    if len(host) > 253:
        raise ValueError("模拟器主机名过长")

    hostname = host.rstrip(".")
    if not hostname or any(not _HOSTNAME_LABEL.fullmatch(label) for label in hostname.split(".")):
        raise ValueError("模拟器主机地址格式无效")
    return hostname.lower()


def build_adb_endpoint(host: str, port: int) -> str:
    """构建 adbutils 可使用的 TCP 设备序列号。"""
    normalized_host = normalize_adb_host(host)
    try:
        normalized_port = int(port)
    except (TypeError, ValueError) as exc:
        raise ValueError("模拟器 ADB 端口必须是整数") from exc
    if not 1 <= normalized_port <= 65535:
        raise ValueError("模拟器 ADB 端口必须在 1 到 65535 之间")

    try:
        is_ipv6 = ipaddress.ip_address(normalized_host).version == 6
    except ValueError:
        is_ipv6 = False
    endpoint_host = f"[{normalized_host}]" if is_ipv6 else normalized_host
    return f"{endpoint_host}:{normalized_port}"

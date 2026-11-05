import os

_SHOP_BASE = os.path.join("assets", "images", "default", "share")


def _collect(subdir: str) -> list[str]:
    d = os.path.join(_SHOP_BASE, subdir)
    return [f"{subdir}/{f}" for f in os.listdir(d)] if os.path.isdir(d) else []


must_purchase = _collect("mirror/shop/must_purchase")
must_be_abandoned = _collect("mirror/shop/must_be_abandoned")
fusion_result = _collect("mirror/shop/fusion_result")

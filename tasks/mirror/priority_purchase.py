"""Optional specified-icon purchases, using the original purchase/acquire UI."""

from dataclasses import dataclass
from pathlib import Path
from time import sleep

from module.my_error.my_error import userStopError

COINS = "mirror/shop/shop_coins_assets.png"
PURCHASE = "mirror/shop/purchase_assets.png"
ACQUIRED = "mirror/road_in_mir/ego_gift_get_confirm_assets.png"


@dataclass(frozen=True)
class PurchaseResult:
    count: int = 0
    ready: bool = True


def merchant_region(size, coins):
    # Original stock columns use coins.x + 150 and 300px spacing at 1440.
    # Keep the owned-gift area on the left outside the search rectangle.
    width, height = size
    scale = height / 1440
    return max(0, coins[0] - 100 * scale), coins[1] + 70 * scale, min(width, coins[0] + 1390 * scale), height - 120 * scale


def buy_specified(auto, matcher, attempted, logger, *, pause=sleep):
    """Each icon gets one bounded attempt per stock refresh. Never pay twice."""
    count = 0
    for _ in range(len(matcher.paths)):
        if auto.take_screenshot() is None:
            return PurchaseResult(count)
        coins = auto.find_element(COINS, threshold=.85)
        if not coins:
            logger.debug("饰品指定：未确认商品页，本次不选择图片")
            return PurchaseResult(count)
        if auto.find_element(PURCHASE, threshold=.85) or auto.find_element(ACQUIRED, threshold=.85):
            logger.warning("饰品指定：商品确认窗口尚未关闭，交由商店外层收尾")
            return PurchaseResult(count, ready=False)
        try:
            found = matcher.find_in_region(auto.screenshot, merchant_region(auto.screenshot.size, coins), attempted)
        except userStopError:
            raise
        except Exception as error:
            logger.warning(f"饰品指定：无法读取或匹配图片，继续原购物流程：{error}")
            return PurchaseResult(count)
        if not found:
            return PurchaseResult(count)
        path, point = found
        attempted.add(path)
        logger.info(f"饰品指定：优先尝试购买 {Path(path).name}")
        auto.mouse_click(*point)
        submitted, acquired = False, False
        for _ in range(12):
            pause(.15)
            if auto.take_screenshot() is None:
                continue
            if auto.find_element(ACQUIRED, threshold=.85):
                auto.click_element(ACQUIRED, threshold=.85)
                acquired = True
                count += 1
                logger.info(f"饰品指定：已确认获得 {Path(path).name}")
                break
            if not submitted and auto.find_element(PURCHASE, threshold=.85):
                auto.click_element(PURCHASE, threshold=.85)
                submitted = True
        if not acquired:
            logger.info("饰品指定：未确认获得，可能资金不足或不可购买；本页不重复尝试")
            auto.mouse_click_blank()
        for _ in range(6):
            pause(.15)
            if auto.take_screenshot() is None:
                continue
            if auto.find_element(ACQUIRED, threshold=.85):
                if not acquired:
                    auto.click_element(ACQUIRED, threshold=.85)
                    acquired, count = True, count + 1
                continue
            if auto.find_element(COINS, threshold=.85) and not auto.find_element(PURCHASE, threshold=.85):
                break
        else:
            logger.warning("饰品指定：未确认返回商品页，结束本店购买阶段，交由商店外层收尾")
            return PurchaseResult(count, ready=False)
    return PurchaseResult(count)

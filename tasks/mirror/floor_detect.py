import numpy as np

# 楼层进度条横带 ROI
FLOOR_BAND_ROI = (760, 495, 1860, 590)

# CLEAR 标记连通域面积下限（1440 高度基准像素数；900p 实测约 489px）
FLOOR_CLEAR_MIN_AREA = 300


def clear_badge_mask(roi_rgb):
    """CLEAR 标记掩码：红色字母（R-max(G,B)>=60 且 R>=190）的像素置 255。

    判别目标是金色菱形上的红色字母
    R-max(G,B) 实测 p95≈40，红字母核心可达 190，门限 60 居中间隔充裕。
    """
    r = roi_rgb[:, :, 0].astype(np.int16)
    g = roi_rgb[:, :, 1].astype(np.int16)
    b = roi_rgb[:, :, 2].astype(np.int16)
    red_dom_min, red_r_min = 60, 190
    m = ((r - np.maximum(g, b)) >= red_dom_min) & (r >= red_r_min)
    return m.astype(np.uint8) * 255


# 说明：
# - 卡包界面（主识别点）：未进入的层都是暗菱形，亮色只有已通关 CLEAR 的红字母
#   -> 计数+1=当前层，精确。
# - 地图探索页：当前层的金色"当前位置"菱形不含红字母，红字母掩码同样只数出已通关层；
#   但识别只在卡包界面调用，地图页沿用上一次的结果。

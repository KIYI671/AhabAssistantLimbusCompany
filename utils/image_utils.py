import os
from pathlib import Path

import cv2
import numpy as np
from cv2 import createCLAHE
from PIL import Image

from module.config import cfg
from module.logger import log
from utils.path_manager import path_manager


class ImageUtils:
    @staticmethod
    def load_image(image_path, resize=True, return_path=False):
        """
        加载图片，并根据指定区域裁剪图片。
        :param image_path: 图片文件路径。
        :param resize: 是否根据窗口大小调整图片尺寸。
        :param return_path: 是否返回实际加载到的路径名。
        :return: 图片数组；若 return_path=True，则返回 (图片数组, 路径名)。
        """
        try:
            img_path = None
            selected_path = None
            for path in path_manager.pic_path:
                img_path = os.path.join(f"./assets/images/{path}/{image_path}")
                if os.path.exists(img_path):
                    selected_path = path
                    break
            if img_path is None or not os.path.exists(img_path):
                log.error(f"未找到图片： {image_path} ")
                return (None, None) if return_path else None
            # 使用上下文管理器打开图片文件，确保文件对象及时关闭
            with Image.open(img_path) as img:
                image = ImageUtils._prepare_loaded_image(np.array(img), resize)
                if return_path:
                    return image, selected_path
                return image
        except FileNotFoundError:
            log.error(f"未找到图片： {image_path} ")
            return (None, None) if return_path else None
        except IOError:
            log.error(f"无法读取图片： {image_path}")
            return (None, None) if return_path else None
        except Exception as e:
            log.error(f"加载图片时发生错误： {e}")
            return (None, None) if return_path else None

    @staticmethod
    def check_default_path_exists(image_path):
        """检查图片在默认路径（非 dark）中是否存在。"""
        for path in path_manager.pic_path:
            if path_manager.is_path_dark(path):
                continue
            img_path = os.path.join(f"./assets/images/{path}/{image_path}")
            if os.path.exists(img_path):
                return True, path
        return False, None

    @staticmethod
    def existing_image_paths(image_path):
        """返回当前有效路径中存在该图片的路径列表。"""
        paths = []
        for path in path_manager.pic_path:
            img_path = os.path.join(f"./assets/images/{path}/{image_path}")
            if os.path.exists(img_path):
                paths.append(path)
        if path_manager.current_theme == "dark":
            dark_paths = [path for path in paths if path_manager.is_path_dark(path)]
            if dark_paths:
                paths = dark_paths
        elif path_manager.current_theme == "default":
            paths = [path for path in paths if path_manager.is_path_default(path)]

        if path_manager.current_language == "zh_cn":
            zh_cn_paths = [path for path in paths if path_manager.is_path_zh_cn(path)]
            if zh_cn_paths:
                paths = zh_cn_paths
        elif path_manager.current_language == "en":
            en_paths = [path for path in paths if path.endswith("/en")]
            if en_paths:
                paths = en_paths
            else:
                paths = [path for path in paths if path.endswith("/share")]
        return paths

    @staticmethod
    def load_from_specific_path(image_path, target_path, resize=True):
        """从指定路径加载图片。"""
        img_path = os.path.join(f"./assets/images/{target_path}/{image_path}")
        if not os.path.exists(img_path):
            return None
        try:
            with Image.open(img_path) as img:
                return ImageUtils._prepare_loaded_image(np.array(img), resize)
        except Exception as e:
            log.error(f"从指定路径加载图片失败: {e}")
            return None

    @staticmethod
    def _prepare_loaded_image(image, resize):
        """统一处理磁盘加载出来的模板图片。"""
        channel = image.shape[2] if len(image.shape) > 2 else 1
        if channel > 3:
            image = image[:, :, :3].copy()
        if resize:
            win_size = cfg.set_win_size
            # 如果win_size 为2560*1440，则不变，否则将图片缩放到对应的16：9大小
            if win_size < 1440:
                image = cv2.resize(
                    image,
                    None,
                    fx=win_size / 1440,
                    fy=win_size / 1440,
                    interpolation=cv2.INTER_AREA,
                )
            elif win_size > 1440:
                image = cv2.resize(
                    image,
                    None,
                    fx=win_size / 1440,
                    fy=win_size / 1440,
                    interpolation=cv2.INTER_LINEAR,
                )
        if len(image.shape) == 2:
            return image
        if image.shape[2] == 1:
            return image[:, :, 0]
        return cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)

    @staticmethod
    def image_channel(image):
        """
        通过检查图像数组的维度来确定图像的通道数。
        如果图像是三维数组，则假设第一个维度是高度，第二个维度是宽度，
        第三个维度是通道数。如果图像是二维数组，则认为图像是单通道的。
        :param image: 输入的图像数组，可以是二维或三维数组。
        :return int: 图像的通道数。如果是三维数组，则返回第三维的大小；
                    如果是二维数组，则返回0，表示单通道。
        """
        # 如果图像数组是三维的，则返回第三维的大小作为通道数
        # 否则，返回0，表示图像是单通道的
        return image.shape[2] if len(image.shape) == 3 else 0

    @staticmethod
    def get_bbox(image, threshold=0):
        """
        获取图像中有效区域的边界框。
        如果图像是彩色的（具有3个通道），则首先将其转换为灰度图像，然后计算边界框。
        :param image: numpy数组，表示输入的图像。
        :param threshold: float，定义有效像素的阈值，默认为0。
        :return tuple: (xmin, ymin, xmax, ymax) 表示有效区域的边界框坐标。
        """
        # 检查图像是否有3个通道（RGB），如果有，则转换为灰度图像
        if ImageUtils.image_channel(image) == 3:
            image = np.max(image, axis=2)
        # 计算在x轴方向上有效像素的投影，并找到投影大于阈值的像素列
        x = np.where(np.max(image, axis=0) > threshold)[0]
        # 计算在y轴方向上有效像素的投影，并找到投影大于阈值的像素行
        y = np.where(np.max(image, axis=1) > threshold)[0]
        # 返回有效区域的边界框坐标
        return x[0], y[0], x[-1] + 1, y[-1] + 1

    @staticmethod
    def crop(image, area, copy=True):
        """
        从图像中裁剪出指定区域。
        如果裁剪区域超出图像边界，函数将自动调整裁剪区域，并在超出边界的部分填充黑色。
        :param image: numpy数组，输入的图像。
        :param area: 四元组，指定裁剪区域的左上角和右下角坐标（x1, y1, x2, y2）。
        :param copy: 是否返回图像的一个副本。默认为True。
        :return numpy数组，裁剪后的图像。
        """
        # 将裁剪区域的坐标转换为整数，以适应图像坐标系。
        x1, y1, x2, y2 = map(int, map(round, area))
        # 获取图像的尺寸。
        h, w = image.shape[:2]
        # 计算裁剪区域是否超出图像边界，如果超出，则记录需要填充的尺寸。
        border = np.maximum((0 - y1, y2 - h, 0 - x1, x2 - w), 0)
        # 确保裁剪区域的坐标不小于0。
        x1, y1, x2, y2 = np.maximum((x1, y1, x2, y2), 0)
        # 从图像中裁剪出指定区域。
        image = image[y1:y2, x1:x2]
        # 如果裁剪区域超出了图像边界，对裁剪后的图像进行边框填充。
        if sum(border) > 0:
            image = cv2.copyMakeBorder(image, *border, borderType=cv2.BORDER_CONSTANT, value=(0, 0, 0))
        # 如果需要，返回图像的一个副本。
        if copy:
            image = image.copy()
        return image

    @staticmethod
    def get_grey_normalized_pic(img_array):
        """
        将传入的图片数组转为灰度模式并进行自适应直方图均衡化
        :param img_array: 图片数组
        :return cl1: 经过自适应直方图均衡化处理后的灰度图像
        """
        # 检查输入图像是否为彩色图像，如果是则转换为灰度图像
        if len(img_array.shape) == 3 and img_array.shape[2] == 3:
            img = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        else:
            img = img_array.copy()
        # 创建自适应直方图均衡化对象，设置限制对比度的参数为2.0，划分的网格大小为8x8
        clahe = createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        # 应用自适应直方图均衡化处理，以改善图像的对比度
        cl1 = clahe.apply(img)
        return cl1

    @staticmethod
    def match_template(screenshot, template, bbox, model="clam"):
        try:
            shape = screenshot.shape
            if len(shape) == 2:
                height, width = shape
            elif len(shape) == 3:
                height, width, _ = shape
            if model == "normal":
                if bbox:
                    bbox = (
                        max(bbox[0] - 100, 0),  # 确保左上角 x 坐标不小于 0
                        max(bbox[1] - 100, 0),  # 确保左上角 y 坐标不小于 0
                        min(bbox[2] + 100, width),  # 确保右下角 x 坐标不大于 图片宽
                        min(bbox[3] + 100, height),  # 确保右下角 y 坐标不大于 图片高
                    )
            else:
                if bbox:
                    bbox = (
                        max(bbox[0] - 30, 0),  # 确保左上角 x 坐标不小于 0
                        max(bbox[1] - 30, 0),  # 确保左上角 y 坐标不小于 0
                        min(bbox[2] + 30, width),  # 确保右下角 x 坐标不大于 图片宽
                        min(bbox[3] + 30, height),  # 确保右下角 y 坐标不大于 图片高
                    )
            if bbox is not None and model != "aggressive":
                screenshot_crop = screenshot[bbox[1] : bbox[3], bbox[0] : bbox[2]]
                result = cv2.matchTemplate(screenshot_crop, template, cv2.TM_CCOEFF_NORMED)
                min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
                h, w = template.shape[:2]
                center = (bbox[0] + max_loc[0] + w // 2, bbox[1] + max_loc[1] + h // 2)
                return center, max_val
            else:
                result = cv2.matchTemplate(screenshot, template, cv2.TM_CCOEFF_NORMED)
                min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
                h, w = template.shape[:2]
                center = (int(max_loc[0]) + w // 2, int(max_loc[1]) + h // 2)
                return center, max_val
        except Exception as e:
            log.error(f"图片识别出现错误：{e}")

    @staticmethod
    def match_template_with_multiple_targets(screenshot, template, threshold):
        # 获取模板的宽度和高度
        w, h = ImageUtils.get_image_info(template)
        # 存储所有匹配位置的中心点
        center_points = []
        # 使用matchTemplate对图片进行模板匹配
        res = cv2.matchTemplate(screenshot, template, cv2.TM_CCOEFF_NORMED)
        # 遍历所有超过阈值的区域
        loc = np.where(res >= threshold)
        points = zip(*loc[::-1])
        # 对匹配结果进行排序，根据匹配度得分从高到低
        sorted_points = sorted(points, key=lambda x: res[x[1], x[0]], reverse=True)
        # 非极大值抑制（NMS）的最小距离
        min_dist = 10
        # 遍历排序后的匹配位置
        if sorted_points:
            for pt in sorted_points:
                # 检查当前匹配点是否与已保留的匹配点太近
                if all(np.linalg.norm(np.array(pt) - np.array(kept_pt)) > min_dist for kept_pt in center_points):
                    # 如果没有太近的匹配点，保留当前匹配点
                    center_points.append(pt)
            # 计算每个匹配点的中心坐标
            center_points = [(int(pt[0] + w / 2), int(pt[1] + h / 2)) for pt in center_points]
            return center_points
        log.debug(f"未找到匹配项，最高匹配度为：{np.max(res)}")
        return []

    @staticmethod
    def get_image_info(image_array):
        """
        获取图片的信息，如尺寸。
        :param image_array: 图片的 numpy 数组。
        :return: 图片的宽度和高度。
        """
        return image_array.shape[::-1]

    @staticmethod
    def feature_matching(template_img, target_img, min_matches=8):
        # 读取图像并进行预处理

        template = cv2.resize(template_img, None, fx=2, fy=2, interpolation=cv2.INTER_LINEAR)
        target = cv2.resize(target_img, None, fx=2, fy=2, interpolation=cv2.INTER_LINEAR)

        # 使用ORB特征检测器
        orb = cv2.ORB_create(nfeatures=1000, scaleFactor=1.2, edgeThreshold=10)

        # 检测关键点和描述符
        kp1, des1 = orb.detectAndCompute(template, None)
        kp2, des2 = orb.detectAndCompute(target, None)

        # 使用FLANN匹配器
        FLANN_INDEX_LSH = 6
        index_params = dict(algorithm=FLANN_INDEX_LSH, table_number=6, key_size=12, multi_probe_level=1)
        search_params = dict(checks=50)
        flann = cv2.FlannBasedMatcher(index_params, search_params)

        matches = flann.knnMatch(des1, des2, k=2)

        # 比率测试
        good_matches = []
        for match in matches:
            if len(match) >= 2:
                m, n = match
                if m.distance < 0.7 * n.distance:
                    good_matches.append(m)

        if len(good_matches) >= min_matches:
            # 获取匹配点的坐标
            src_pts = np.float32([kp1[m.queryIdx].pt for m in good_matches])
            dst_pts = np.float32([kp2[m.trainIdx].pt for m in good_matches])

            # 计算单应性矩阵
            M, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)

            # 计算匹配置信度评分
            inlier_ratio = np.sum(mask) / len(mask)
            if inlier_ratio < 0.3:  # 如果内点比例过低，认为匹配不可靠
                return False, len(good_matches)

            return True, len(good_matches)
        else:
            return False, len(good_matches)

    @staticmethod
    def get_icon_advise_scales(image_name: str) -> tuple[list[float], int]:
        """获取某个模板图片的推荐缩放比例列表, 以及基准尺寸（通常是1440）"""
        if image_name.endswith(".png"):
            image_name = image_name[:-4]
        if image_name in (
            "body",
            "back",
            "head",
            "left_hand",
            "right_hand",
            "left_eye",
            "right_eye",
            "left_foot",
            # "right_foot", 暂无
            "tail",
            "top_plate",
        ):  # 异想体部位
            return [0.19, 0.18, 0.20, 0.25, 0.26, 0.23, 0.22], 1440
        return [1], 1440

    @staticmethod
    def find_all_icons_canny(
        screenshot,
        template,
        threshold=0.35,
        iou_threshold=0.3,
        target_path="",
        image_name="",
        clear_cache: bool = False,
        advise_scales: list[float] | None = None,
        base_size: int = 1440,
    ):
        """
        识别所有图标位置
        Args:
            iou_threshold: float, 非极大值抑制的IOU阈值，默认为0.3
            clear_cache: bool, 是否清除缓存，默认为False
            target_path: str, 模板图片所在的路径（相对于assets/images/），默认为空字符串
            image_name: str, 模板图片的名称（不带扩展名），默认为空字符串
            advise_scales: list[float], 可选的缩放比例列表，如果提供则只使用这些比例进行检测
            base_size: int, 基准尺寸，通常是1440，用于根据当前截图尺寸调整建议的缩放比例
        """

        # 读取图像
        large_img = screenshot
        original_template = template

        cache_size = f"{screenshot.shape[1]}x{screenshot.shape[0]}"
        cache_path: Path = Path("cache") / cache_size / target_path / image_name

        # 预处理大图（只做一次）
        large_edges = ImageUtils._canny_process(large_img)
        cv2.imwrite("test_large_edges.png", large_edges)

        # 存储所有检测结果
        all_detections = []

        # 预先计算模板的原始尺寸
        template_h, template_w = original_template.shape

        # 只在可能成功的缩放比例范围内搜索（根据给出的范围）
        if not advise_scales:
            advise_scales, base_size = ImageUtils.get_icon_advise_scales(image_name)
        scale = screenshot.shape[0] / base_size
        optimized_scales: set[float] = set([round(s * scale, 2) for s in advise_scales])
        # 优先读取缓存模板
        if not clear_cache and cache_path and cache_path.exists():
            template_list = [f for f in cache_path.iterdir() if f.is_file() and f.suffix == ".png"]
            if template_list:
                for template_file in template_list:
                    scale_str = template_file.stem
                    try:
                        scale = float(scale_str)
                        if scale in optimized_scales:
                            scaled_template = cv2.imread(str(template_file), cv2.IMREAD_GRAYSCALE)
                            result = cv2.matchTemplate(large_edges, scaled_template, cv2.TM_CCOEFF_NORMED)
                            locations = ImageUtils.__find_local_maxima_fast(result, threshold=threshold)
                            new_w, new_h = scaled_template.shape[::-1]
                            for x, y, score in locations:
                                all_detections.append(
                                    {"location": (x, y), "size": (new_w, new_h), "score": score, "scale": scale}
                                )
                            optimized_scales.remove(scale)  # 从待处理列表中移除已处理的比例
                        else:
                            log.debug(f"缓存模板 {template_file.name} 的缩放比例 {scale} 不在建议范围内，已删除。")
                            template_file.unlink()
                    except ValueError:
                        log.debug(f"缓存文件名 {template_file} 不是有效的缩放比例，已删除。")
                        template_file.unlink()
        for scale in optimized_scales:
            # 缩放模板
            new_w = int(template_w * scale)
            new_h = int(template_h * scale)

            if new_w < 10 or new_h < 10:
                log.debug(
                    f"缩放比例 {scale} 导致模板尺寸过小，已跳过。相关图片: {target_path}/{image_name}，模板尺寸: ({new_w}, {new_h})"
                )
                continue
            if new_w > large_edges.shape[1] or new_h > large_edges.shape[0]:
                log.debug(
                    f"缩放比例 {scale} 导致模板尺寸过大，已跳过。相关图片: {target_path}/{image_name}，模板尺寸: ({new_w}, {new_h})"
                )
                continue

            # 处理模板
            scaled_template = cv2.resize(original_template, (new_w, new_h))
            template_edges = ImageUtils._canny_process(scaled_template)

            # 缓存模板
            if cache_path:
                cache_path.mkdir(parents=True, exist_ok=True)
                cv2.imwrite(str(cache_path / f"{scale}.png"), template_edges)

            # 模板匹配
            result = cv2.matchTemplate(large_edges, template_edges, cv2.TM_CCOEFF_NORMED)

            # 找到所有局部最大值
            locations = ImageUtils.__find_local_maxima_fast(result, threshold=threshold)

            for x, y, score in locations:
                all_detections.append({"location": (x, y), "size": (new_w, new_h), "score": score, "scale": scale})

        # 应用非极大值抑制合并重复检测
        final_detections = ImageUtils.__non_max_suppression(all_detections, iou_threshold=iou_threshold)

        # 按Y坐标排序（从上到下），再按X排序（从左到右）
        final_detections.sort(key=lambda d: (d["location"][1], d["location"][0]))

        return final_detections

    @staticmethod
    def __find_local_maxima_fast(result, threshold=0.35, min_distance=20):
        """
        找到所有局部最大值
        """

        # 使用 dilation 快速找到局部最大值
        # 创建核，膨胀操作会扩大最大值区域
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        dilated = cv2.dilate(result, kernel)

        # 局部最大值就是原始值等于膨胀值的位置
        local_max_mask = (result == dilated) & (result >= threshold)

        # 找到所有局部最大值的坐标
        locations = np.where(local_max_mask)

        # 转换为列表并过滤
        raw_locations = []
        for y, x in zip(locations[0], locations[1]):
            raw_locations.append((x, y, result[y, x]))

        # 按分数排序
        raw_locations.sort(key=lambda x: x[2], reverse=True)

        # 移除距离太近的点
        filtered = []
        for x, y, score in raw_locations:
            too_close = False
            for fx, fy, _ in filtered:
                if abs(x - fx) < min_distance and abs(y - fy) < min_distance:
                    too_close = True
                    break
            if not too_close:
                filtered.append((x, y, score))

        return filtered

    @staticmethod
    def __non_max_suppression(detections, iou_threshold=0.3):
        """
        合并重叠的检测框
        """
        if not detections:
            return []

        # 按分数排序
        detections = sorted(detections, key=lambda x: x["score"], reverse=True)

        keep = []
        while detections:
            current = detections.pop(0)
            keep.append(current)

            # 只计算一次当前框的参数
            x1, y1 = current["location"]
            w1, h1 = current["size"]
            area1 = w1 * h1

            # 过滤重叠的检测
            remaining = []
            for d in detections:
                x2, y2 = d["location"]
                w2, h2 = d["size"]

                # 快速检查：如果中心点距离太远，直接跳过IoU计算
                center_dist = abs((x1 + w1 // 2) - (x2 + w2 // 2)) + abs((y1 + h1 // 2) - (y2 + h2 // 2))
                if center_dist > (max(w1, w2) + max(h1, h2)):
                    remaining.append(d)
                    continue

                # 计算IoU
                xi1 = max(x1, x2)
                yi1 = max(y1, y2)
                xi2 = min(x1 + w1, x2 + w2)
                yi2 = min(y1 + h1, y2 + h2)

                if xi2 > xi1 and yi2 > yi1:
                    inter_area = (xi2 - xi1) * (yi2 - yi1)
                    area2 = w2 * h2
                    union_area = area1 + area2 - inter_area
                    iou = inter_area / union_area

                    if iou < iou_threshold:
                        remaining.append(d)
                else:
                    remaining.append(d)

            detections = remaining
        return keep

    @staticmethod
    def _canny_process(image, blur_ksize=(3, 3), low_threshold: float = 50, high_threshold: float = 150):
        """
        对图像进行Canny边缘检测的预处理
        """
        if ImageUtils.image_channel(image) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        blur = cv2.GaussianBlur(gray, blur_ksize, 0)
        edges = cv2.Canny(blur, low_threshold, high_threshold)
        return edges

    @staticmethod
    def auto_find_best_scales(
        screenshot, template, threshold: float = 0.4, scale_range=(0.1, 0.5), step=0.01, resize=False
    ):
        """
        自动找出最佳的缩放比例范围（快速扫描）
        Args:
            screenshot: 大图的numpy数组
            template: 模板图的numpy数组
            threshold: 匹配度阈值，范围在0到1之间
            scale_range: 扫描的缩放比例范围，默认为0.1到0.5
            step: 扫描的步长，默认为0.01
            resize: 是否根据窗口大小调整图片尺寸，默认为False
        Returns:
            best_scales: 满足阈值条件的最佳缩放比例列表
            img: 标注了匹配结果的图像（BGR格式）
            edge_target_img: 经过边缘处理的原图
        """
        if resize:
            if cfg.set_win_size < 1440:
                screenshot = cv2.resize(
                    screenshot,
                    None,
                    fx=1440 / cfg.set_win_size,
                    fy=1440 / cfg.set_win_size,
                    interpolation=cv2.INTER_AREA,
                )
            elif cfg.set_win_size > 1440:
                screenshot = cv2.resize(
                    screenshot,
                    None,
                    fx=cfg.set_win_size / 1440,
                    fy=cfg.set_win_size / 1440,
                    interpolation=cv2.INTER_AREA,
                )
        large_img = screenshot
        original_template = template
        raw_screenshot = screenshot
        if ImageUtils.image_channel(large_img) == 3:
            large_gray = cv2.cvtColor(large_img, cv2.COLOR_BGR2GRAY)
        else:
            large_gray = large_img
        large_edges = ImageUtils._canny_process(large_gray)

        template_h, template_w = original_template.shape
        best_scores = []
        results = []
        # 大步长快速扫描
        for scale in np.arange(scale_range[0], scale_range[1], step):
            new_w = int(template_w * scale)
            new_h = int(template_h * scale)

            if new_w > large_edges.shape[1] or new_h > large_edges.shape[0]:
                continue

            scaled_template = cv2.resize(original_template, (new_w, new_h))
            template_edges = ImageUtils._canny_process(scaled_template)

            result = cv2.matchTemplate(large_edges, template_edges, cv2.TM_CCOEFF_NORMED)
            locations = ImageUtils.__find_local_maxima_fast(result, threshold=threshold * 0.9)
            max_score = np.max(result)
            for x, y, score in locations:
                results.append(
                    {
                        "scale": scale,
                        "score": score,
                        "location": (x, y),
                        "size": (new_w, new_h),
                    }
                )
            best_scores.append((scale, max_score))

        # 找出最佳比例
        best_scores.sort(key=lambda x: x[1], reverse=True)
        top_scales = [s[0] if s[1] >= threshold else None for s in best_scores[:3]]
        for scale in top_scales:
            if scale is not None:
                log.debug(f"最佳缩放比例: {scale:.2f}，匹配度: {dict(best_scores)[scale]:.3f}")
            else:
                log.debug(
                    f"没有找到满足阈值的缩放比例，最高匹配度为: {best_scores[0][1]:.3f}, 前五的匹配度为: {[f'{s[1]:.3f}, scale: {s[0]:.2f}' for s in best_scores[:5]]}"
                )

        img = cv2.cvtColor(np.array(raw_screenshot), cv2.COLOR_RGB2BGR)
        pass_count = 0
        for i, det in enumerate(results):
            x, y = det["location"]
            w, h = det["size"]
            score = det["score"]
            scale = det["scale"]
            if score >= threshold:
                # 绘制矩形框
                cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 2)

                # 标注序号和分数
                # sl : scale
                # so : score
                line1 = f"sl:{scale:.2f}"
                line2 = f"so:{score:.2f}"
                cv2.putText(img, line1, (x, y - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 1)
                cv2.putText(img, line2, (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 1)
                pass_count += 1
            else:
                # 绘制矩形框
                cv2.rectangle(img, (x, y), (x + w, y + h), (0, 0, 255), 2)

                # 标注序号和分数
                line1 = f"sl:{scale:.2f}"
                line2 = f"so:{score:.2f}"
                cv2.putText(img, line1, (x, y - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 1)
                cv2.putText(img, line2, (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 1)

        cv2.putText(
            img, f"Total Icons: {pass_count}/{len(results)}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2
        )
        return top_scales, img, large_edges

import os

import cv2
import numpy as np
from cv2 import createCLAHE
from PIL import Image

from module.config import cfg
from module.logger import log
from utils import pic_path


class ImageUtils:
    @staticmethod
    def load_image(image_path, resize=True):
        """
        加载图片，并根据指定区域裁剪图片。
        :param image_path: 图片文件路径。
        :return: numpy数组，如果图片通道数大于3，则只返回前三个通道。
        """
        try:
            img_path = None
            for path in pic_path:
                img_path = os.path.join(f"./assets/images/{path}/{image_path}")
                if os.path.exists(img_path):
                    break
            # 使用上下文管理器打开图片文件，确保文件对象及时关闭
            with Image.open(img_path) as img:
                # 将图片转换为numpy数组
                image = np.array(img)
                # 获取图片的通道数，如果图片为多通道（如RGB）则获取，否则默认为1（如灰度图）
                channel = image.shape[2] if len(image.shape) > 2 else 1
                # 如果图片通道数大于3，只保留前三个通道（如RGB）
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
                # 返回处理后的图片数组
                image = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
                return image
        except FileNotFoundError:
            log.error(f"未找到图片： {image_path} ")
            return None
        except IOError:
            log.error(f"无法读取图片： {image_path}")
            return None
        except Exception as e:
            log.error(f"加载图片时发生错误： {e}")
            return None

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
            image = cv2.copyMakeBorder(
                image, *border, borderType=cv2.BORDER_CONSTANT, value=(0, 0, 0)
            )
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
                result = cv2.matchTemplate(
                    screenshot_crop, template, cv2.TM_CCOEFF_NORMED
                )
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
                if all(
                    np.linalg.norm(np.array(pt) - np.array(kept_pt)) > min_dist
                    for kept_pt in center_points
                ):
                    # 如果没有太近的匹配点，保留当前匹配点
                    center_points.append(pt)
            # 计算每个匹配点的中心坐标
            center_points = [
                (int(pt[0] + w / 2), int(pt[1] + h / 2)) for pt in center_points
            ]
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

        template = cv2.resize(
            template_img, None, fx=2, fy=2, interpolation=cv2.INTER_LINEAR
        )
        target = cv2.resize(
            target_img, None, fx=2, fy=2, interpolation=cv2.INTER_LINEAR
        )

        # 使用ORB特征检测器
        orb = cv2.ORB_create(nfeatures=1000, scaleFactor=1.2, edgeThreshold=10)

        # 检测关键点和描述符
        kp1, des1 = orb.detectAndCompute(template, None)
        kp2, des2 = orb.detectAndCompute(target, None)

        # 使用FLANN匹配器
        FLANN_INDEX_LSH = 6
        index_params = dict(
            algorithm=FLANN_INDEX_LSH, table_number=6, key_size=12, multi_probe_level=1
        )
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

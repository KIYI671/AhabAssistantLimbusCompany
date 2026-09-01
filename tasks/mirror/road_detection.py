"""镜牢地图节点与道路识别的纯计算逻辑。"""

from __future__ import annotations

from collections.abc import Sequence

import cv2
import numpy as np

NODE_CLASSES = (
    "battle",
    "boss_battle",
    "event",
    "focused_encounter",
    "risky_encounter",
    "shop",
    "abnormality_focused_encounter",
)

ROAD_DIRECTIONS = (
    ("DOWN", 30.0, 60.0),
    ("UP", 120.0, 150.0),
)
REFERENCE_HEIGHT = 1440
MAX_WORKING_HEIGHT = 1440


def prepare_node_model_input(image: np.ndarray, input_size: int = 640) -> tuple[np.ndarray, float]:
    """等比例缩到模型尺寸后补黑边，避免按 4K 长边创建巨大的方形临时图。"""
    if image.ndim != 3 or image.shape[2] != 3:
        raise ValueError(f"节点模型输入图像格式异常: {image.shape}")
    height, width, _ = image.shape
    length = max(height, width)
    scale = length / input_size
    resized_width = max(1, min(input_size, round(width / scale)))
    resized_height = max(1, min(input_size, round(height / scale)))

    resized = cv2.resize(
        image,
        (resized_width, resized_height),
        interpolation=cv2.INTER_LINEAR,
    )
    model_image = np.zeros((input_size, input_size, 3), dtype=np.uint8)
    model_image[:resized_height, :resized_width] = resized
    blob = cv2.dnn.blobFromImage(
        model_image,
        scalefactor=1 / 255,
        size=(input_size, input_size),
        swapRB=True,
    )
    return blob, scale


def decode_node_detections(
    output: np.ndarray,
    scale: float,
    *,
    classes: Sequence[str] = NODE_CLASSES,
    score_threshold: float = 0.25,
    nms_threshold: float = 0.4,
) -> list[dict]:
    """向量化解析 YOLO 输出，保持原有阈值和 NMS 行为。"""
    tensor = np.asarray(output)
    if tensor.ndim == 3:
        if tensor.shape[0] != 1:
            raise ValueError(f"节点模型输出批次数量异常: {tensor.shape}")
        tensor = tensor[0]
    if tensor.ndim != 2:
        raise ValueError(f"节点模型输出维度异常: {tensor.shape}")

    expected_columns = 4 + len(classes)
    if tensor.shape[0] == expected_columns:
        predictions = tensor.T
    elif tensor.shape[1] == expected_columns:
        predictions = tensor
    else:
        raise ValueError(f"节点模型输出类别数量异常: {tensor.shape}")

    if predictions.shape[0] == 0:
        return []

    class_scores = predictions[:, 4:]
    class_ids = np.argmax(class_scores, axis=1)
    scores = class_scores[np.arange(class_scores.shape[0]), class_ids]
    keep_mask = scores >= score_threshold
    if not np.any(keep_mask):
        return []

    selected_boxes = predictions[keep_mask, :4]
    selected_scores = scores[keep_mask]
    selected_class_ids = class_ids[keep_mask]

    boxes_xywh = np.column_stack(
        (
            selected_boxes[:, 0] - selected_boxes[:, 2] * 0.5,
            selected_boxes[:, 1] - selected_boxes[:, 3] * 0.5,
            selected_boxes[:, 2],
            selected_boxes[:, 3],
        )
    )
    boxes = boxes_xywh.astype(float).tolist()
    score_values = selected_scores.astype(float).tolist()
    kept_indices = cv2.dnn.NMSBoxes(
        boxes,
        score_values,
        0.0,
        nms_threshold,
        0.5,
    )
    if kept_indices is None or len(kept_indices) == 0:
        return []

    detections = []
    for index in np.asarray(kept_indices).reshape(-1):
        index = int(index)
        class_id = int(selected_class_ids[index])
        detections.append(
            {
                "class_id": class_id,
                "class_name": classes[class_id],
                "confidence": float(selected_scores[index]),
                "box": boxes[index],
                "scale": scale,
            }
        )
    return detections


def _to_gray(image: np.ndarray) -> np.ndarray:
    if image.ndim == 2:
        return image
    if image.ndim == 3 and image.shape[2] == 3:
        return cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    if image.ndim == 3 and image.shape[2] == 4:
        return cv2.cvtColor(image, cv2.COLOR_RGBA2GRAY)
    raise ValueError(f"道路检测输入图像格式异常: {image.shape}")


def _working_road_image(
    image: np.ndarray,
    max_working_height: int,
) -> tuple[np.ndarray, float]:
    """限制 LSD 的像素量；返回工作图以及工作坐标/原图坐标比例。"""
    gray = _to_gray(np.asarray(image))
    height, width = gray.shape
    if height <= max_working_height:
        return gray, 1.0

    work_scale = max_working_height / height
    working = cv2.resize(
        gray,
        (max(1, round(width * work_scale)), max_working_height),
        interpolation=cv2.INTER_AREA,
    )
    return working, work_scale


def _fit_merged_line(lines: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """用一组近似平行线段的全部端点拟合代表线段。"""
    points = lines.reshape(-1, 2)
    x = points[:, 0]
    y = points[:, 1]
    if np.ptp(x) <= np.finfo(np.float32).eps:
        line = lines[0].astype(np.float64, copy=True)
    else:
        slope, intercept = np.polyfit(x, y, 1)
        min_x = float(np.min(x))
        max_x = float(np.max(x))
        line = np.array(
            [min_x, slope * min_x + intercept, max_x, slope * max_x + intercept],
            dtype=np.float64,
        )
    center = np.array(((line[0] + line[2]) * 0.5, (line[1] + line[3]) * 0.5))
    return line, center


def merge_road_lines(
    raw_lines: np.ndarray,
    *,
    image_height: int,
    bus_x: float,
    output_scale: float = 1.0,
    min_length: float = 160,
    merge_distance: float = 230,
) -> list[list]:
    """向量化筛选 LSD 线段，并按真实角度和空间距离合并道路边缘。"""
    if raw_lines is None:
        return []
    lines = np.asarray(raw_lines, dtype=np.float32).reshape(-1, 4)
    if lines.size == 0:
        return []

    resolution_scale = image_height / REFERENCE_HEIGHT
    min_length_px = min_length * resolution_scale
    fallback_length_px = 50 * resolution_scale
    max_length_px = 1000 * resolution_scale
    merge_distance_px = merge_distance * resolution_scale
    bus_margin_px = 50 * resolution_scale

    vectors = lines[:, 2:4] - lines[:, 0:2]
    lengths = np.hypot(vectors[:, 0], vectors[:, 1])
    centers = (lines[:, 0:2] + lines[:, 2:4]) * 0.5
    angles = np.degrees(np.arctan2(vectors[:, 1], vectors[:, 0])) % 180

    length_mask = (lengths >= min_length_px) & (lengths < max_length_px)
    if not np.any(length_mask):
        length_mask = (lengths >= fallback_length_px) & (lengths < max_length_px)
    if not np.any(length_mask):
        return []

    result = []
    for direction, min_angle, max_angle in ROAD_DIRECTIONS:
        group_indices = np.flatnonzero(length_mask & (angles >= min_angle) & (angles <= max_angle))
        if group_indices.size == 0:
            continue

        order = np.argsort(-lengths[group_indices], kind="stable")
        group_indices = group_indices[order]
        group_centers = centers[group_indices]
        group_angles = angles[group_indices]
        unused = np.ones(group_indices.size, dtype=bool)

        while np.any(unused):
            base_index = int(np.flatnonzero(unused)[0])
            center_delta = group_centers - group_centers[base_index]
            distances = np.hypot(center_delta[:, 0], center_delta[:, 1])
            angle_delta = np.abs(group_angles - group_angles[base_index])
            cluster_mask = unused & (angle_delta <= 8.0) & (distances <= merge_distance_px)
            unused[cluster_mask] = False

            merged_line, merged_center = _fit_merged_line(lines[group_indices[cluster_mask]])
            merged_vector = merged_line[2:4] - merged_line[0:2]
            merged_length = float(np.hypot(merged_vector[0], merged_vector[1]))
            if merged_length < min_length_px or merged_center[0] < bus_x + bus_margin_px:
                continue

            original_center = merged_center * output_scale
            result.append([direction, (float(original_center[0]), float(original_center[1]))])

    return result


def detect_roads(
    image: np.ndarray,
    bus_x: float,
    *,
    min_length: float = 160,
    merge_distance: float = 230,
    max_working_height: int = MAX_WORKING_HEIGHT,
) -> list[list]:
    """检测镜牢地图道路，并用原始截图坐标返回方向和中心点。"""
    if max_working_height <= 0:
        raise ValueError("max_working_height 必须大于 0")
    working_image, work_scale = _working_road_image(image, max_working_height)
    detected = cv2.createLineSegmentDetector(0).detect(working_image)
    if not detected or detected[0] is None:
        return []
    return merge_road_lines(
        detected[0],
        image_height=working_image.shape[0],
        bus_x=bus_x * work_scale,
        output_scale=1.0 / work_scale,
        min_length=min_length,
        merge_distance=merge_distance,
    )

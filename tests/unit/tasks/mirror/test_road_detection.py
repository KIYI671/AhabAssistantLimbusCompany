import importlib.util
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = REPO_ROOT / "tasks" / "mirror" / "road_detection.py"
SPEC = importlib.util.spec_from_file_location("road_detection_under_test", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
ROAD_DETECTION = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ROAD_DETECTION)
NODE_CLASSES = ROAD_DETECTION.NODE_CLASSES
decode_node_detections = ROAD_DETECTION.decode_node_detections
detect_roads = ROAD_DETECTION.detect_roads
merge_road_lines = ROAD_DETECTION.merge_road_lines
prepare_node_model_input = ROAD_DETECTION.prepare_node_model_input


def _model_output() -> np.ndarray:
    output = np.zeros((1, 4 + len(NODE_CLASSES), 4), dtype=np.float32)
    output[0, :4, 0] = [100, 100, 40, 40]
    output[0, 4 + 0, 0] = 0.90

    # 与第一个框高度重叠，NMS 应保留高分框。
    output[0, :4, 1] = [102, 102, 40, 40]
    output[0, 4 + 0, 1] = 0.80

    output[0, :4, 2] = [300, 200, 60, 20]
    output[0, 4 + 5, 2] = 0.75

    # 低于原算法的 0.25 阈值，应被过滤。
    output[0, :4, 3] = [500, 300, 30, 30]
    output[0, 4 + 2, 3] = 0.20
    return output


def test_decode_node_detections_preserves_threshold_and_nms() -> None:
    detections = decode_node_detections(_model_output(), scale=2.0)

    assert [item["class_name"] for item in detections] == ["battle", "shop"]
    centers = [
        (
            int((item["box"][0] + item["box"][2] / 2) * item["scale"]),
            int((item["box"][1] + item["box"][3] / 2) * item["scale"]),
        )
        for item in detections
    ]
    assert centers == [(200, 200), (600, 400)]


def test_decode_node_detections_accepts_transposed_rows() -> None:
    rows = _model_output()[0].T
    detections = decode_node_detections(rows, scale=1.0)
    assert [item["class_name"] for item in detections] == ["battle", "shop"]


def test_prepare_node_model_input_matches_legacy_16_by_9_tensor() -> None:
    rng = np.random.default_rng(7)
    image = rng.integers(0, 256, size=(1080, 1920, 3), dtype=np.uint8)

    legacy_square = np.zeros((1920, 1920, 3), dtype=np.uint8)
    legacy_square[:1080, :1920] = image
    legacy_blob = ROAD_DETECTION.cv2.dnn.blobFromImage(
        legacy_square,
        scalefactor=1 / 255,
        size=(640, 640),
        swapRB=True,
    )

    blob, scale = prepare_node_model_input(image)
    assert scale == 3.0
    assert np.array_equal(blob, legacy_blob)


def _synthetic_road_map(height: int) -> tuple[np.ndarray, dict[str, tuple[float, float]]]:
    width = round(height * 16 / 9)
    image = np.zeros((height, width), dtype=np.uint8)
    roads = {
        "DOWN": ((0.30, 0.30), (0.42, 0.45)),
        "UP": ((0.60, 0.65), (0.72, 0.50)),
    }
    expected = {}
    thickness = max(2, round(6 * height / 1440))
    for direction, (start, end) in roads.items():
        start_px = (round(start[0] * width), round(start[1] * height))
        end_px = (round(end[0] * width), round(end[1] * height))
        ROAD_DETECTION.cv2.line(image, start_px, end_px, 255, thickness, ROAD_DETECTION.cv2.LINE_AA)
        expected[direction] = ((start[0] + end[0]) * 0.5, (start[1] + end[1]) * 0.5)
    return image, expected


def test_detect_roads_is_resolution_consistent() -> None:
    normalized_centers = {}
    for height in (720, 1440, 2160):
        image, expected = _synthetic_road_map(height)
        width = image.shape[1]
        roads = detect_roads(image, bus_x=0.10 * width)

        by_direction = {direction: center for direction, center in roads}
        assert set(by_direction) == {"DOWN", "UP"}
        normalized_centers[height] = {
            direction: (center[0] / width, center[1] / height)
            for direction, center in by_direction.items()
        }
        for direction, expected_center in expected.items():
            assert np.allclose(normalized_centers[height][direction], expected_center, atol=0.01)

    for direction in ("DOWN", "UP"):
        baseline = normalized_centers[1440][direction]
        assert np.allclose(normalized_centers[720][direction], baseline, atol=0.005)
        assert np.allclose(normalized_centers[2160][direction], baseline, atol=0.005)


def test_merge_road_lines_uses_angle_difference_in_degrees() -> None:
    raw_lines = np.array(
        [
            [[300, 300, 500, 440]],  # 约 35°
            [[350, 350, 500, 529]],  # 约 50°，中心很近但并非同一方向
        ],
        dtype=np.float32,
    )

    roads = merge_road_lines(raw_lines, image_height=1440, bus_x=0)

    assert [direction for direction, _ in roads] == ["DOWN", "DOWN"]

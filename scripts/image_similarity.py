import argparse
import csv
import hashlib
import html
import math
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}
PATH_THEMES = {"default", "dark"}
PATH_LANGUAGES = {"zh_cn", "en", "share"}
ISSUE_TITLES = {
    "should_add_assets_or_bbox_suffix": "应添加 _assets 或 _bbox 后缀",
    "assets_or_bbox_suffix_but_core_like": "_assets / _bbox 后缀疑似用于核心小图",
    "empty_assets_or_bbox_area": "_assets / _bbox 图片没有可用非黑区域",
    "assets_or_bbox_suffix_format": "_assets / _bbox 后缀格式不规范",
    "path_layout": "路径结构不规范",
}


@dataclass(frozen=True)
class ImageEntry:
    name: str
    image: np.ndarray
    template: np.ndarray
    is_assets: bool
    bbox: tuple[int, int, int, int] | None
    width: int
    height: int
    black_ratio: float


@dataclass(frozen=True)
class NamingIssue:
    kind: str
    name: str
    detail: str


def emit(message: str) -> None:
    sys.stdout.write(f"{message}\n")
    sys.stdout.flush()


def format_duration(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes, sec = divmod(seconds, 60)
    if minutes < 60:
        return f"{int(minutes)}m{sec:04.1f}s"
    hours, minutes = divmod(minutes, 60)
    return f"{int(hours)}h{int(minutes):02d}m{sec:04.1f}s"


def render_progress(completed: int, total: int, start_time: float, *, final: bool = False) -> None:
    width = 32
    percent = completed / total if total else 1.0
    filled = min(width, int(width * percent))
    bar = "#" * filled + "-" * (width - filled)
    elapsed = max(time.time() - start_time, 0.001)
    speed = completed / elapsed
    remaining = max(total - completed, 0)
    eta = remaining / speed if speed > 0 else 0
    message = (
        f"\r[{bar}] {percent:6.2%} "
        f"{completed}/{total} pairs "
        f"{speed:,.1f} pairs/s "
        f"elapsed {format_duration(elapsed)} "
        f"eta {format_duration(eta)}"
    )

    if sys.stdout.isatty():
        sys.stdout.write(message)
        if final:
            sys.stdout.write("\n")
    else:
        emit(message.strip())
    sys.stdout.flush()


def sanitize_output_name(path: Path) -> str:
    text = path.as_posix().strip("./")
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text) or "images"


def collect_image_paths(folder: Path, recursive: bool) -> list[Path]:
    iterator = folder.rglob("*") if recursive else folder.iterdir()
    return sorted(
        [path for path in iterator if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS],
        key=lambda path: path.relative_to(folder).as_posix().lower(),
    )


def to_gray(path: Path) -> np.ndarray:
    with Image.open(path) as image_file:
        image = np.array(image_file)

    channel = image.shape[2] if len(image.shape) > 2 else 1
    if channel > 3:
        image = image[:, :, :3].copy()

    if len(image.shape) == 2:
        return image
    if image.shape[2] == 1:
        return image[:, :, 0]
    return cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)


def get_bbox(image: np.ndarray, threshold: int = 0) -> tuple[int, int, int, int] | None:
    x = np.where(np.max(image, axis=0) > threshold)[0]
    y = np.where(np.max(image, axis=1) > threshold)[0]
    if len(x) == 0 or len(y) == 0:
        return None
    return int(x[0]), int(y[0]), int(x[-1]) + 1, int(y[-1]) + 1


def crop(image: np.ndarray, area: tuple[int, int, int, int]) -> np.ndarray:
    x1, y1, x2, y2 = area
    return image[y1:y2, x1:x2].copy()


def black_ratio(image: np.ndarray) -> float:
    return float(np.count_nonzero(image == 0) / image.size)


def is_assets_name(path: Path) -> bool:
    return path.stem.endswith(("_assets", "_bbox"))


def naming_issues_for(
    relative_name: str,
    image: np.ndarray,
    is_assets: bool,
    bbox: tuple[int, int, int, int] | None,
    enforce_path_layout: bool,
):
    issues = []
    parts = relative_name.split("/")
    filename = parts[-1]
    width, height = image.shape[1], image.shape[0]
    ratio = black_ratio(image)
    full_size_black_template = width == 2560 and height == 1440 and ratio >= 0.85

    if enforce_path_layout and (len(parts) < 3 or parts[0] not in PATH_THEMES or parts[1] not in PATH_LANGUAGES):
        issues.append(NamingIssue("path_layout", relative_name, "路径应形如 <theme>/<language>/<module>/<name>.png"))
    if full_size_black_template and not is_assets:
        issues.append(
            NamingIssue("should_add_assets_or_bbox_suffix", relative_name, f"{width}x{height}, black={ratio:.3f}")
        )
    if is_assets and not full_size_black_template and ratio < 0.30:
        issues.append(
            NamingIssue("assets_or_bbox_suffix_but_core_like", relative_name, f"{width}x{height}, black={ratio:.3f}")
        )
    if is_assets and bbox is None:
        issues.append(NamingIssue("empty_assets_or_bbox_area", relative_name, "图片没有可用非黑区域"))
    if path_stem_ends_with_assets_without_underscore(filename):
        issues.append(NamingIssue("assets_or_bbox_suffix_format", relative_name, "后缀应写作 _assets 或 _bbox"))
    return issues


def path_stem_ends_with_assets_without_underscore(filename: str) -> bool:
    stem = Path(filename).stem
    return (stem.endswith("assets") and not stem.endswith("_assets")) or (
        stem.endswith("bbox") and not stem.endswith("_bbox")
    )


def prepare_entry(
    path: Path,
    folder: Path,
    crop_assets: bool,
    enforce_path_layout: bool,
) -> tuple[ImageEntry, list[NamingIssue]]:
    relative_name = path.relative_to(folder).as_posix()
    image = to_gray(path)
    width, height = image.shape[1], image.shape[0]
    is_assets = is_assets_name(path)
    bbox = get_bbox(image) if is_assets else None

    if is_assets and crop_assets and bbox is not None:
        template = crop(image, bbox)
    else:
        template = image

    entry = ImageEntry(
        name=relative_name,
        image=image,
        template=template,
        is_assets=is_assets,
        bbox=bbox,
        width=width,
        height=height,
        black_ratio=black_ratio(image),
    )
    return entry, naming_issues_for(relative_name, image, is_assets, bbox, enforce_path_layout)


def score_one(screenshot: np.ndarray, template: np.ndarray) -> float | None:
    screenshot_height, screenshot_width = screenshot.shape[:2]
    template_height, template_width = template.shape[:2]
    if screenshot_height < template_height or screenshot_width < template_width:
        return None

    try:
        result = cv2.matchTemplate(screenshot, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, _ = cv2.minMaxLoc(result)
    except Exception:
        return None

    if max_val is None or not math.isfinite(max_val):
        return None
    return float(max_val)


def bbox_for_model(
    bbox: tuple[int, int, int, int],
    screenshot: np.ndarray,
    model: str,
) -> tuple[int, int, int, int] | None:
    if model == "aggressive":
        return None

    pad = 100 if model == "normal" else 30
    height, width = screenshot.shape[:2]
    return (
        max(bbox[0] - pad, 0),
        max(bbox[1] - pad, 0),
        min(bbox[2] + pad, width),
        min(bbox[3] + pad, height),
    )


def positioned_assets_score(screenshot_entry: ImageEntry, template_entry: ImageEntry, model: str) -> float | None:
    if template_entry.bbox is None:
        return None
    search_bbox = bbox_for_model(template_entry.bbox, screenshot_entry.image, model)
    if search_bbox is None:
        return score_one(screenshot_entry.image, template_entry.template)
    x1, y1, x2, y2 = search_bbox
    screenshot_crop = screenshot_entry.image[y1:y2, x1:x2]
    return score_one(screenshot_crop, template_entry.template)


def non_positioned_similarity(image_a: np.ndarray, image_b: np.ndarray) -> float:
    scores = [score_one(image_a, image_b), score_one(image_b, image_a)]
    valid_scores = [score for score in scores if score is not None]
    if not valid_scores:
        return 0.0
    return max(valid_scores)


def pair_type(left: ImageEntry, right: ImageEntry) -> str:
    if left.is_assets and right.is_assets:
        return "assets-assets"
    if not left.is_assets and not right.is_assets:
        return "non-assets"
    return "mixed"


def target_name(image_name: str) -> str:
    return image_name.split("/")[-1]


def name_relation(left_name: str, right_name: str) -> str:
    return "same-target" if target_name(left_name) == target_name(right_name) else "different-target"


def image_link(name: str) -> str:
    path = f"assets/images/{name}"
    return f"[`{name}`]({path})"


def html_link(label: str, href: str) -> str:
    escaped_label = html.escape(label)
    escaped_href = html.escape(href, quote=True)
    return f'<a href="{escaped_href}"><code>{escaped_label}</code></a>'


def markdown_item_line(text: str) -> str:
    return f"- {text}\n"


def checkbox_key(*parts: object) -> str:
    raw = "\t".join(str(part) for part in parts)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def entry_similarity(left: ImageEntry, right: ImageEntry, assets_model: str) -> tuple[float, str]:
    kind = pair_type(left, right)
    if kind == "assets-assets":
        scores = [
            positioned_assets_score(left, right, assets_model),
            positioned_assets_score(right, left, assets_model),
        ]
        valid_scores = [score for score in scores if score is not None]
        return (max(valid_scores) if valid_scores else 0.0), kind
    if kind == "non-assets":
        return non_positioned_similarity(left.image, right.image), kind

    assets_entry = left if left.is_assets else right
    non_assets_entry = right if left.is_assets else left
    return non_positioned_similarity(assets_entry.template, non_assets_entry.image), kind


def compute_similarity_row(row: int, images: list[ImageEntry], threshold: float, assets_model: str):
    row_entry = images[row]
    row_scores = [0.0 for _ in images]
    row_scores[row] = 1.0
    highlighted_pairs = []
    category_counts = {"assets-assets": 0, "non-assets": 0, "mixed": 0}

    for col in range(row + 1, len(images)):
        col_entry = images[col]
        score, kind = entry_similarity(row_entry, col_entry, assets_model)
        category_counts[kind] += 1
        row_scores[col] = score
        if score >= threshold:
            highlighted_pairs.append((row_entry.name, col_entry.name, score, kind, name_relation(row_entry.name, col_entry.name)))

    return row, row_scores, highlighted_pairs, len(images) - row - 1, category_counts


def load_images(
    folder: Path,
    recursive: bool,
    crop_assets: bool,
) -> tuple[list[ImageEntry], list[tuple[str, str]], list[NamingIssue]]:
    images = []
    skipped = []
    naming_issues = []
    enforce_path_layout = folder.as_posix().replace("\\", "/").rstrip("/").endswith("assets/images")
    for path in collect_image_paths(folder, recursive):
        relative_name = path.relative_to(folder).as_posix()
        try:
            entry, issues = prepare_entry(path, folder, crop_assets, enforce_path_layout)
            images.append(entry)
            naming_issues.extend(issues)
        except Exception as exc:
            skipped.append((relative_name, str(exc)))
    return images, skipped, naming_issues


def write_matrix(output_path: Path, images: list[ImageEntry], matrix: list[list[float]]) -> None:
    with output_path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.writer(file)
        writer.writerow(["image"] + [entry.name for entry in images])
        for entry, row in zip(images, matrix):
            writer.writerow([entry.name] + [f"{score:.6f}" for score in row])


def write_pairs(
    output_path: Path,
    folder: Path,
    images_count: int,
    threshold: float,
    max_workers: int,
    total_pairs: int,
    category_counts: dict[str, int],
    match_seconds: float,
    load_seconds: float,
    write_seconds: float,
    total_seconds: float,
    pairs: list[tuple[str, str, float, str, str]],
    skipped: list[tuple[str, str]],
    naming_issues: list[NamingIssue],
) -> None:
    with output_path.open("w", encoding="utf-8") as file:
        file.write(f"folder={folder.as_posix()}\n")
        file.write(f"images={images_count}\n")
        file.write(f"threshold={threshold}\n")
        file.write(f"pairs={len(pairs)}\n")
        file.write(f"total_pairs={total_pairs}\n")
        file.write(f"matched_ratio={len(pairs)}/{total_pairs}\n")
        file.write(f"assets_assets_pairs={category_counts['assets-assets']}\n")
        file.write(f"non_assets_pairs={category_counts['non-assets']}\n")
        file.write(f"mixed_pairs={category_counts['mixed']}\n")
        same_target_pairs = [pair for pair in pairs if pair[4] == "same-target"]
        different_target_pairs = [pair for pair in pairs if pair[4] == "different-target"]
        file.write(f"same_target_pairs={len(same_target_pairs)}\n")
        file.write(f"different_target_pairs={len(different_target_pairs)}\n")
        file.write(f"naming_issues={len(naming_issues)}\n")
        file.write(f"max_workers={max_workers}\n")
        file.write(f"parallel_pair_workers={max_workers}\n")
        file.write(f"load_seconds={load_seconds:.3f}\n")
        file.write(f"match_seconds={match_seconds:.3f}\n")
        file.write(f"write_seconds={write_seconds:.3f}\n")
        file.write(f"total_seconds={total_seconds:.3f}\n")
        if skipped:
            file.write(f"skipped={len(skipped)}\n")
            for name, error in skipped:
                file.write(f"SKIPPED\t{name}\t{error}\n")
        if naming_issues:
            file.write("NAMING_ISSUES\n")
            for issue in naming_issues:
                file.write(f"{issue.kind}\t{issue.name}\t{issue.detail}\n")
        file.write("SAME_TARGET_PAIRS\n")
        for left, right, score, kind, relation in same_target_pairs:
            file.write(f"{score:.6f}\t{left}\t{right}\t{kind}\t{relation}\n")
        file.write("DIFFERENT_TARGET_PAIRS\n")
        for left, right, score, kind, relation in different_target_pairs:
            file.write(f"{score:.6f}\t{left}\t{right}\t{kind}\t{relation}\n")


def write_report(
    output_path: Path,
    folder: Path,
    images: list[ImageEntry],
    threshold: float,
    total_pairs: int,
    category_counts: dict[str, int],
    pairs: list[tuple[str, str, float, str, str]],
    naming_issues: list[NamingIssue],
    html_report_path: Path | None = None,
) -> None:
    grouped_pairs = {
        "same-target": {"assets-assets": [], "non-assets": [], "mixed": []},
        "different-target": {"assets-assets": [], "non-assets": [], "mixed": []},
    }
    for pair in pairs:
        grouped_pairs[pair[4]][pair[3]].append(pair)

    grouped_issues: dict[str, list[NamingIssue]] = {}
    for issue in naming_issues:
        grouped_issues.setdefault(issue.kind, []).append(issue)

    with output_path.open("w", encoding="utf-8") as file:
        file.write("# 图片相似度与命名规范报告\n\n")
        file.write("依据：[`assets/doc/zh/image_recognition.md`](assets/doc/zh/image_recognition.md)。\n\n")
        if html_report_path is not None:
            file.write(
                f"勾选整理请使用可记忆版：[`{html_report_path.as_posix()}`]({html_report_path.as_posix()})。\n\n"
            )
        file.write("## 汇总\n\n")
        folder_path = folder.as_posix()
        file.write(f"- 图片目录：[`{folder_path}`]({folder_path})\n")
        file.write(f"- 图片数量：{len(images)}\n")
        file.write(f"- 阈值：score >= {threshold}\n")
        file.write(f"- 总匹配对数：{total_pairs}\n")
        file.write(f"- 命中对数：{len(pairs)}\n")
        file.write(f"- assets-assets 对数：{category_counts['assets-assets']}\n")
        file.write(f"- non-assets 对数：{category_counts['non-assets']}\n")
        file.write(f"- mixed 对数：{category_counts['mixed']}\n")
        file.write(f"- 同名高相似对数：{sum(len(v) for v in grouped_pairs['same-target'].values())}\n")
        file.write(f"- 不同名高相似对数：{sum(len(v) for v in grouped_pairs['different-target'].values())}\n")
        file.write(f"- 命名问题：{len(naming_issues)}\n\n")

        file.write("## A. 命名规范问题\n\n")
        if not naming_issues:
            file.write("- 未发现命名规范问题。\n\n")
        else:
            for kind, issues in sorted(grouped_issues.items()):
                file.write(f"### {ISSUE_TITLES.get(kind, kind)}\n\n")
                for issue in issues:
                    file.write(markdown_item_line(issue.detail))
                    file.write(f"  - {image_link(issue.name)}\n")
                file.write("\n")

        write_relation_section(file, "B", "同名高相似", grouped_pairs["same-target"])
        write_relation_section(file, "C", "不同名高相似", grouped_pairs["different-target"])


def write_relation_section(file, section: str, title: str, grouped_by_kind: dict[str, list]) -> None:
    file.write(f"## {section}. {title}\n\n")
    file.write("同名指文件名相同，不考虑所在路径；不同名则通常需要人工判断是否能合并或是否存在误识别风险。\n\n")
    write_kind_section(
        file,
        "assets-assets：位置敏感匹配",
        "这类包含 `_assets` 和 `_bbox` 后缀图片，使用 `find_element` 风格的 bbox 限定区域，默认 model=normal。",
        grouped_by_kind["assets-assets"],
    )
    write_kind_section(file, "non-assets：核心图匹配", "", grouped_by_kind["non-assets"])
    write_kind_section(
        file,
        "mixed：assets 与非 assets 核心相似",
        "这类只说明核心视觉相似；因调用语义不同，不能直接按同图删除。",
        grouped_by_kind["mixed"],
    )


def write_kind_section(file, title: str, description: str, pairs: list) -> None:
    file.write(f"### {title}（{len(pairs)} 对）\n\n")
    if description:
        file.write(f"{description}\n\n")
    if not pairs:
        file.write("- 无\n\n")
        return
    for left, right, score, kind, relation in pairs:
        file.write(markdown_item_line(f"score={score:.6f}"))
        file.write(f"  - {image_link(left)}\n")
        file.write(f"  - {image_link(right)}\n")
    file.write("\n")


def write_html_report(
    output_path: Path,
    folder: Path,
    images: list[ImageEntry],
    threshold: float,
    total_pairs: int,
    category_counts: dict[str, int],
    pairs: list[tuple[str, str, float, str, str]],
    naming_issues: list[NamingIssue],
) -> None:
    grouped_pairs = {
        "same-target": {"assets-assets": [], "non-assets": [], "mixed": []},
        "different-target": {"assets-assets": [], "non-assets": [], "mixed": []},
    }
    for pair in pairs:
        grouped_pairs[pair[4]][pair[3]].append(pair)

    grouped_issues: dict[str, list[NamingIssue]] = {}
    for issue in naming_issues:
        grouped_issues.setdefault(issue.kind, []).append(issue)

    folder_path = folder.as_posix()
    with output_path.open("w", encoding="utf-8") as file:
        file.write("<!doctype html>\n<html lang=\"zh-CN\">\n<head>\n")
        file.write("<meta charset=\"utf-8\">\n")
        file.write("<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n")
        file.write("<title>图片相似度与命名规范报告</title>\n")
        file.write("<style>\n")
        file.write(
            "body{font-family:system-ui,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;"
            "line-height:1.55;margin:32px;max-width:1180px;color:#1f2328}"
            "a{color:#0969da;text-decoration:none}a:hover{text-decoration:underline}"
            "code{font-family:ui-monospace,SFMono-Regular,Consolas,monospace}"
            "h1,h2,h3{line-height:1.25}.summary{columns:2;max-width:900px}"
            ".hint{color:#57606a}"
            "li{margin:4px 0}.score{font-family:ui-monospace,SFMono-Regular,Consolas,monospace}"
            "input[type=checkbox]{margin-right:8px;transform:translateY(1px)}"
        )
        file.write("</style>\n</head>\n<body>\n")
        file.write("<h1>图片相似度与命名规范报告</h1>\n")
        file.write(
            f"<p>依据：{html_link('assets/doc/zh/image_recognition.md', 'assets/doc/zh/image_recognition.md')}。</p>\n"
        )
        file.write("<p class=\"hint\">勾选状态会自动保存在本机浏览器 localStorage，重新打开此 HTML 文件后会恢复。</p>\n")
        file.write("<h2>汇总</h2>\n<ul class=\"summary\">\n")
        file.write(f"<li>图片目录：{html_link(folder_path, folder_path)}</li>\n")
        file.write(f"<li>图片数量：{len(images)}</li>\n")
        file.write(f"<li>阈值：score &gt;= {threshold}</li>\n")
        file.write(f"<li>总匹配对数：{total_pairs}</li>\n")
        file.write(f"<li>命中对数：{len(pairs)}</li>\n")
        file.write(f"<li>assets-assets 对数：{category_counts['assets-assets']}</li>\n")
        file.write(f"<li>non-assets 对数：{category_counts['non-assets']}</li>\n")
        file.write(f"<li>mixed 对数：{category_counts['mixed']}</li>\n")
        same_count = sum(len(v) for v in grouped_pairs["same-target"].values())
        different_count = sum(len(v) for v in grouped_pairs["different-target"].values())
        file.write(f"<li>同名高相似对数：{same_count}</li>\n")
        file.write(f"<li>不同名高相似对数：{different_count}</li>\n")
        file.write(f"<li>命名问题：{len(naming_issues)}</li>\n")
        file.write("</ul>\n")

        file.write("<h2>A. 命名规范问题</h2>\n")
        if not naming_issues:
            file.write("<p>未发现命名规范问题。</p>\n")
        else:
            for kind, issues in sorted(grouped_issues.items()):
                file.write(f"<h3>{html.escape(ISSUE_TITLES.get(kind, kind))}</h3>\n<ul>\n")
                for issue in issues:
                    key = checkbox_key("issue", issue.kind, issue.name)
                    file.write(f"<li>{html_checkbox_html(key, issue.detail)}\n<ul>\n")
                    file.write(f"<li>{html_link(issue.name, f'assets/images/{issue.name}')}</li>\n")
                    file.write("</ul>\n</li>\n")
                file.write("</ul>\n")

        write_html_relation_section(file, "B", "同名高相似", grouped_pairs["same-target"])
        write_html_relation_section(file, "C", "不同名高相似", grouped_pairs["different-target"])
        file.write(
            "<script>\n"
            "const prefix='image-similarity-report:';\n"
            "document.querySelectorAll('input[data-check-key]').forEach((box)=>{\n"
            "  const key=prefix+box.dataset.checkKey;\n"
            "  box.checked=localStorage.getItem(key)==='1';\n"
            "  box.addEventListener('change',()=>{\n"
            "    if(box.checked){localStorage.setItem(key,'1');}\n"
            "    else{localStorage.removeItem(key);}\n"
            "  });\n"
            "});\n"
            "</script>\n"
        )
        file.write("</body>\n</html>\n")


def html_checkbox_html(key: str, text: str) -> str:
    escaped_key = html.escape(key, quote=True)
    escaped_text = html.escape(text)
    return f'<label><input type="checkbox" data-check-key="{escaped_key}"><span class="score">{escaped_text}</span></label>'


def write_html_relation_section(file, section: str, title: str, grouped_by_kind: dict[str, list]) -> None:
    file.write(f"<h2>{section}. {html.escape(title)}</h2>\n")
    file.write("<p>同名指文件名相同，不考虑所在路径；不同名则通常需要人工判断是否能合并或是否存在误识别风险。</p>\n")
    write_html_kind_section(
        file,
        "assets-assets：位置敏感匹配",
        "这类包含 `_assets` 和 `_bbox` 后缀图片，使用 `find_element` 风格的 bbox 限定区域，默认 model=normal。",
        grouped_by_kind["assets-assets"],
    )
    write_html_kind_section(file, "non-assets：核心图匹配", "", grouped_by_kind["non-assets"])
    write_html_kind_section(
        file,
        "mixed：assets 与非 assets 核心相似",
        "这类只说明核心视觉相似；因调用语义不同，不能直接按同图删除。",
        grouped_by_kind["mixed"],
    )


def write_html_kind_section(file, title: str, description: str, pairs: list) -> None:
    file.write(f"<h3>{html.escape(title)}（{len(pairs)} 对）</h3>\n")
    if description:
        file.write(f"<p>{html.escape(description)}</p>\n")
    if not pairs:
        file.write("<p>无</p>\n")
        return
    file.write("<ul>\n")
    for left, right, score, kind, relation in pairs:
        key = checkbox_key("pair", left, right, kind)
        file.write(f"<li>{html_checkbox_html(key, f'score={score:.6f}')}\n<ul>\n")
        file.write(f"<li>{html_link(left, f'assets/images/{left}')}</li>\n")
        file.write(f"<li>{html_link(right, f'assets/images/{right}')}</li>\n")
        file.write("</ul>\n</li>\n")
    file.write("</ul>\n")


def build_default_outputs(folder: Path) -> tuple[Path, Path, Path, Path]:
    stem = sanitize_output_name(folder)
    return (
        Path(f"image_similarity_{stem}.csv"),
        Path(f"image_similarity_{stem}_pairs.txt"),
        Path(f"image_similarity_{stem}_report.md"),
        Path(f"image_similarity_{stem}_report.html"),
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="生成图片文件夹的 n x n 模板匹配相似度矩阵。")
    parser.add_argument("folder", nargs="?", default="assets/images", help="图片文件夹，默认 assets/images")
    parser.add_argument("--threshold", type=float, default=0.75, help="图片对输出阈值，默认 0.75")
    parser.add_argument("--matrix-output", type=Path, default=None, help="完整矩阵 CSV 输出路径")
    parser.add_argument("--pairs-output", type=Path, default=None, help="高相似图片对 TXT 输出路径")
    parser.add_argument("--report-output", type=Path, default=None, help="分类报告 Markdown 输出路径")
    parser.add_argument("--html-report-output", type=Path, default=None, help="可记忆 checkbox 的 HTML 报告输出路径")
    parser.add_argument("--max-workers", type=int, default=16, help="并行线程数，默认 16")
    parser.add_argument(
        "--assets-model",
        choices=("normal", "clam", "aggressive"),
        default="normal",
        help="assets-assets 的 bbox 搜索模式，默认 normal",
    )
    parser.add_argument("--no-recursive", action="store_true", help="只扫描文件夹第一层")
    parser.add_argument("--no-assets-crop", action="store_true", help="不对 *_assets / *_bbox 图片裁剪黑边")
    parser.add_argument("--top", type=int, default=30, help="控制台展示前 N 个高相似图片对，默认 30")
    parser.add_argument("--no-progress", action="store_true", help="不显示进度条")
    parser.add_argument("--progress-interval", type=float, default=0.5, help="进度刷新间隔秒数，默认 0.5")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    folder = Path(args.folder)
    if not folder.exists() or not folder.is_dir():
        emit(f"图片文件夹不存在：{folder}")
        return 1

    matrix_output, pairs_output, report_output, html_report_output = build_default_outputs(folder)
    if args.matrix_output is not None:
        matrix_output = args.matrix_output
    if args.pairs_output is not None:
        pairs_output = args.pairs_output
    if args.report_output is not None:
        report_output = args.report_output
        html_report_output = report_output.with_suffix(".html")
    if args.html_report_output is not None:
        html_report_output = args.html_report_output

    start_time = time.time()
    load_start = time.time()
    images, skipped, naming_issues = load_images(
        folder,
        recursive=not args.no_recursive,
        crop_assets=not args.no_assets_crop,
    )
    load_seconds = time.time() - load_start
    if not images:
        emit("没有找到可用于计算的图片")
        return 1

    matrix_output.parent.mkdir(parents=True, exist_ok=True)
    pairs_output.parent.mkdir(parents=True, exist_ok=True)
    report_output.parent.mkdir(parents=True, exist_ok=True)
    html_report_output.parent.mkdir(parents=True, exist_ok=True)

    image_count = len(images)
    matrix = [[0.0 for _ in images] for _ in images]
    pairs = []
    category_counts = {"assets-assets": 0, "non-assets": 0, "mixed": 0}
    total_pairs = image_count * (image_count - 1) // 2
    completed_pairs = 0
    max_workers = args.max_workers
    max_workers = max(1, min(max_workers, max(image_count - 1, 1)))

    emit("RUN_CONFIG")
    emit(f"folder={folder.as_posix()}")
    emit(f"images={image_count}")
    emit(f"skipped={len(skipped)}")
    emit(f"naming_issues={len(naming_issues)}")
    emit(f"threshold={args.threshold}")
    emit(f"total_pairs={total_pairs}")
    emit(f"matrix_cells={image_count * image_count}")
    emit(f"recursive={not args.no_recursive}")
    emit(f"crop_assets={not args.no_assets_crop}")
    emit(f"assets_model={args.assets_model}")
    emit(f"parallel_workers={max_workers}")
    emit(f"parallel_pair_workers={max_workers}")
    emit("opencv_threads_per_worker=1")
    emit(f"load_seconds={load_seconds:.3f}")

    if naming_issues:
        emit("NAMING_ISSUES_PREVIEW")
        for issue in naming_issues[:20]:
            emit(f"{issue.kind}\t{issue.name}\t{issue.detail}")
        if len(naming_issues) > 20:
            emit(f"... {len(naming_issues) - 20} more naming issues")

    match_start = time.time()
    last_progress_time = 0.0
    if not args.no_progress:
        render_progress(0, total_pairs, match_start)

    previous_cv_threads = cv2.getNumThreads()
    cv2.setNumThreads(1)
    try:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_row = {
                executor.submit(compute_similarity_row, row, images, args.threshold, args.assets_model): row
                for row in range(image_count)
            }
            for future in as_completed(future_to_row):
                row, row_scores, row_pairs, row_pair_count, row_category_counts = future.result()
                for col in range(row, image_count):
                    score = row_scores[col]
                    matrix[row][col] = score
                    matrix[col][row] = score
                pairs.extend(row_pairs)
                for kind, count in row_category_counts.items():
                    category_counts[kind] += count
                completed_pairs += row_pair_count
                now = time.time()
                if (
                    not args.no_progress
                    and (now - last_progress_time >= args.progress_interval or completed_pairs == total_pairs)
                ):
                    render_progress(completed_pairs, total_pairs, match_start, final=completed_pairs == total_pairs)
                    last_progress_time = now
    finally:
        cv2.setNumThreads(previous_cv_threads)

    match_seconds = time.time() - match_start
    pairs_sorted = sorted(pairs, key=lambda item: item[2], reverse=True)
    write_start = time.time()
    write_matrix(matrix_output, images, matrix)
    write_pairs(
        pairs_output,
        folder,
        image_count,
        args.threshold,
        max_workers,
        total_pairs,
        category_counts,
        match_seconds,
        load_seconds,
        0.0,
        0.0,
        pairs_sorted,
        skipped,
        naming_issues,
    )
    write_report(
        report_output,
        folder,
        images,
        args.threshold,
        total_pairs,
        category_counts,
        pairs_sorted,
        naming_issues,
        html_report_output,
    )
    write_html_report(
        html_report_output,
        folder,
        images,
        args.threshold,
        total_pairs,
        category_counts,
        pairs_sorted,
        naming_issues,
    )
    write_seconds = time.time() - write_start
    total_seconds = time.time() - start_time
    write_pairs(
        pairs_output,
        folder,
        image_count,
        args.threshold,
        max_workers,
        total_pairs,
        category_counts,
        match_seconds,
        load_seconds,
        write_seconds,
        total_seconds,
        pairs_sorted,
        skipped,
        naming_issues,
    )

    emit("RESULT_START")
    emit(f"folder={folder.as_posix()}")
    emit(f"images={image_count}")
    emit(f"skipped={len(skipped)}")
    emit(f"naming_issues={len(naming_issues)}")
    emit(f"pairs_ge_threshold={len(pairs_sorted)}")
    emit(f"total_pairs={total_pairs}")
    emit(f"matched_ratio={len(pairs_sorted)}/{total_pairs}")
    emit(f"matched_percent={(len(pairs_sorted) / total_pairs * 100 if total_pairs else 0):.4f}%")
    emit(f"assets_assets_pairs={category_counts['assets-assets']}")
    emit(f"non_assets_pairs={category_counts['non-assets']}")
    emit(f"mixed_pairs={category_counts['mixed']}")
    emit(f"threshold={args.threshold}")
    emit(f"assets_model={args.assets_model}")
    emit(f"parallel_workers={max_workers}")
    emit(f"parallel_rows_in_flight={max_workers}")
    emit(f"parallel_pair_workers={max_workers}")
    emit(f"matrix_file={matrix_output}")
    emit(f"pairs_file={pairs_output}")
    emit(f"report_file={report_output}")
    emit(f"html_report_file={html_report_output}")
    emit(f"load_seconds={load_seconds:.3f}")
    emit(f"match_seconds={match_seconds:.3f}")
    emit(f"write_seconds={write_seconds:.3f}")
    emit(f"total_seconds={total_seconds:.3f}")
    emit(f"match_elapsed={format_duration(match_seconds)}")
    emit(f"total_elapsed={format_duration(total_seconds)}")
    emit(f"pair_speed={total_pairs / match_seconds if match_seconds > 0 else 0:.1f} pairs/s")
    emit("top_pairs")
    for left, right, score, kind, relation in pairs_sorted[: args.top]:
        emit(f"{score:.3f}\t{left}\t{right}\t{kind}\t{relation}")
    emit("RESULT_END")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

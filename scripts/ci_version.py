from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote
from urllib.request import Request, urlopen

# 只把正式 release tag 当作 CI 预发布版本的基线，忽略 beta/rc/dev 等标签。
STABLE_TAG_PATTERN = re.compile(r"^[Vv]?(\d+)\.(\d+)\.(\d+)$")


@dataclass(frozen=True)
class StableRelease:
    # 统一承载一个可用于计算下个 CI 预发布版本的正式 release 信息。
    tag_name: str
    version: tuple[int, int, int]
    published_at: datetime


def parse_args() -> argparse.Namespace:
    # 同时支持 GitHub Actions 在线调用与本地注入 JSON 的离线验证模式。
    parser = argparse.ArgumentParser(description="Generate a semver-compatible CI version.")
    parser.add_argument("--releases-json", type=Path, help="Path to mocked GitHub releases JSON for local tests.")
    parser.add_argument("--runs-json", type=Path, help="Path to mocked workflow runs JSON for local tests.")
    parser.add_argument("--repo", help="GitHub repository in owner/name format.")
    parser.add_argument("--workflow-file", default="ci.yaml", help="Workflow file name used to count CI runs.")
    parser.add_argument("--current-run-id", type=int, required=True, help="Current GitHub Actions run id.")
    parser.add_argument("--current-run-number", type=int, help="Current GitHub Actions workflow run number.")
    parser.add_argument("--fallback-version", help="Fallback version to use when CI semver generation fails.")
    parser.add_argument("--github-api-url", default=os.environ.get("GITHUB_API_URL", "https://api.github.com"))
    parser.add_argument("--github-token", default=os.environ.get("GITHUB_TOKEN"))
    parser.add_argument("--github-output", default=os.environ.get("GITHUB_OUTPUT"))
    return parser.parse_args()


def load_json_file(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def parse_iso8601(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def parse_stable_release(item: dict[str, Any]) -> StableRelease | None:
    # 只接受完整的稳定版 tag，其他 release 记录直接跳过。
    if item.get("draft"):
        return None

    tag_name = item.get("tag_name", "")
    match = STABLE_TAG_PATTERN.fullmatch(tag_name)
    if not match:
        return None

    published_at = item.get("published_at")
    if not published_at:
        return None

    return StableRelease(
        tag_name=tag_name,
        version=tuple(int(part) for part in match.groups()),
        published_at=parse_iso8601(published_at),
    )


def find_latest_stable_release(releases: list[dict[str, Any]]) -> StableRelease:
    # 从所有 release 中挑出最新稳定版，作为下一次 alpha 预发布的基线。
    stable_releases = [release for item in releases if (release := parse_stable_release(item)) is not None]
    if not stable_releases:
        raise ValueError("No stable GitHub release matching vX.Y.Z or VX.Y.Z was found.")

    return max(stable_releases, key=lambda release: (release.version, release.published_at))


def build_ci_version(
    releases: list[dict[str, Any]],
    runs: list[dict[str, Any]],
    current_run_id: int,
    current_run_number: int | None = None,
) -> str:
    latest_release = find_latest_stable_release(releases)
    # CI 预发布版本始终在最新正式 release 的 patch 号基础上递增 1。
    next_version = (
        latest_release.version[0],
        latest_release.version[1],
        latest_release.version[2] + 1,
    )

    # 只统计最新正式 release 发布之后的 CI 运行，作为 alpha 序号来源。
    runs_after_release = [
        run
        for run in runs
        if run.get("created_at") and parse_iso8601(run["created_at"]) > latest_release.published_at
    ]
    runs_after_release.sort(key=lambda run: (run.get("run_number", 0), run.get("id", 0)))

    current_index = next((index for index, run in enumerate(runs_after_release) if run.get("id") == current_run_id), None)
    if current_index is not None:
        build_number = current_index + 1
    elif current_run_number is not None:
        # GitHub API 偶尔会在运行初期查不到当前 run，回退到 run_number 仍能保持单调递增。
        build_number = 1 + sum(1 for run in runs_after_release if (run.get("run_number") or 0) < current_run_number)
    else:
        build_number = len(runs_after_release) + 1

    return f"{next_version[0]}.{next_version[1]}.{next_version[2]}-alpha.{build_number}"


def fetch_json(url: str, token: str | None) -> dict[str, Any] | list[Any]:
    # 统一封装 GitHub API 请求头，便于后续复用同一鉴权和版本配置。
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "AALC-CI-Version-Generator",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = Request(url, headers=headers)
    with urlopen(request) as response:
        return json.load(response)


def fetch_paginated_collection(base_url: str, collection_key: str, token: str | None) -> list[dict[str, Any]]:
    page = 1
    items: list[dict[str, Any]] = []

    while True:
        # GitHub API 单页最多返回 100 条，这里翻完分页避免构建序号计算偏小。
        separator = "&" if "?" in base_url else "?"
        page_url = f"{base_url}{separator}per_page=100&page={page}"
        payload = fetch_json(page_url, token)
        batch = payload[collection_key] if isinstance(payload, dict) else payload
        if not batch:
            break
        items.extend(batch)
        if len(batch) < 100:
            break
        page += 1

    return items


def load_releases_and_runs(args: argparse.Namespace) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if args.releases_json and args.runs_json:
        # 本地测试直接读固定 JSON，避免依赖在线 GitHub API。
        releases = load_json_file(args.releases_json)
        runs = load_json_file(args.runs_json)
        return releases, runs

    if not args.repo:
        raise ValueError("--repo is required unless --releases-json and --runs-json are provided.")

    # 在线模式下分别拉取 release 列表和当前 workflow 的运行记录。
    releases_url = f"{args.github_api_url}/repos/{args.repo}/releases"
    workflow_path = quote(args.workflow_file, safe="")
    runs_url = f"{args.github_api_url}/repos/{args.repo}/actions/workflows/{workflow_path}/runs"

    releases = fetch_paginated_collection(releases_url, "items", args.github_token)
    runs = fetch_paginated_collection(runs_url, "workflow_runs", args.github_token)
    return releases, runs


def write_github_output(path: str | None, version: str) -> None:
    if not path:
        return

    # 输出到 GITHUB_OUTPUT，供 workflow 后续 job 通过 outputs 继续传递版本号。
    with open(path, "a", encoding="utf-8") as file:
        file.write(f"version={version}\n")


def main() -> int:
    # 主流程优先生成 semver 预发布版本，失败时再按调用方提供的 fallback 兜底。
    args = parse_args()
    try:
        releases, runs = load_releases_and_runs(args)
        version = build_ci_version(releases, runs, args.current_run_id, args.current_run_number)
    except Exception as exc:
        if not args.fallback_version:
            print(f"Failed to generate CI version: {exc}", file=sys.stderr)
            raise

        print(f"Failed to generate CI version: {exc}", file=sys.stderr)
        print(f"Falling back to workflow SHA version: {args.fallback_version}", file=sys.stderr)
        version = args.fallback_version

    write_github_output(args.github_output, version)
    print(version)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        raise SystemExit(1) from exc

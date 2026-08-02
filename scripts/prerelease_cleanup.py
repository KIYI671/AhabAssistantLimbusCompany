from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

BETA_TAG_PATTERN = re.compile(r"^V(\d+)\.(\d+)\.(\d+)-beta\.([1-9]\d*)$")


class GitHubApiError(RuntimeError):
    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status


class CurrentPrereleaseMissingError(ValueError):
    pass


@dataclass(frozen=True)
class BetaRelease:
    release_id: int
    tag_name: str
    base_version: tuple[int, int, int]
    beta_number: int


@dataclass(frozen=True)
class CleanupPlan:
    retained_tag: str
    current_retained: bool
    delete: tuple[BetaRelease, ...]


def parse_current_tag(tag_name: str) -> tuple[tuple[int, int, int], int]:
    match = BETA_TAG_PATTERN.fullmatch(tag_name)
    if not match:
        raise ValueError(f"Current tag is not a valid beta tag: {tag_name}")
    major, minor, patch, beta_number = (int(part) for part in match.groups())
    return (major, minor, patch), beta_number


def parse_beta_release(item: dict[str, Any]) -> BetaRelease | None:
    if item.get("draft") or not item.get("prerelease"):
        return None

    tag_name = item.get("tag_name")
    release_id = item.get("id")
    if not isinstance(tag_name, str) or not isinstance(release_id, int):
        return None

    match = BETA_TAG_PATTERN.fullmatch(tag_name)
    if not match:
        return None

    major, minor, patch, beta_number = (int(part) for part in match.groups())
    return BetaRelease(
        release_id=release_id,
        tag_name=tag_name,
        base_version=(major, minor, patch),
        beta_number=beta_number,
    )


def build_cleanup_plan(releases: list[dict[str, Any]], current_tag: str) -> CleanupPlan:
    current_base, _ = parse_current_tag(current_tag)
    beta_releases = [release for item in releases if (release := parse_beta_release(item)) is not None]
    candidates = [release for release in beta_releases if release.base_version == current_base]

    current_release = next((release for release in candidates if release.tag_name == current_tag), None)
    if current_release is None:
        matching_record = next((item for item in releases if item.get("tag_name") == current_tag), None)
        if matching_record is not None:
            raise ValueError(f"Current tag is not a published prerelease: {current_tag}")
        raise CurrentPrereleaseMissingError(f"Current prerelease was not found: {current_tag}")

    retained_release = max(candidates, key=lambda release: (release.beta_number, release.release_id))
    return CleanupPlan(
        retained_tag=retained_release.tag_name,
        current_retained=retained_release.tag_name == current_tag,
        delete=tuple(release for release in candidates if release != retained_release),
    )


def missing_current_plan(releases: list[dict[str, Any]], current_tag: str) -> CleanupPlan | None:
    current_base, current_beta = parse_current_tag(current_tag)
    candidates = [
        release
        for item in releases
        if (release := parse_beta_release(item)) is not None and release.base_version == current_base
    ]
    if not candidates:
        return None

    retained_release = max(candidates, key=lambda release: (release.beta_number, release.release_id))
    if retained_release.beta_number <= current_beta:
        return None

    return CleanupPlan(
        retained_tag=retained_release.tag_name,
        current_retained=False,
        delete=(),
    )


def resolve_cleanup_plan(
    fetch_releases: Callable[[], list[dict[str, Any]]],
    current_tag: str,
    *,
    retries: int = 3,
    sleep: Callable[[float], None] = time.sleep,
) -> CleanupPlan:
    for attempt in range(retries):
        releases = fetch_releases()
        try:
            return build_cleanup_plan(releases, current_tag)
        except CurrentPrereleaseMissingError:
            concurrent_plan = missing_current_plan(releases, current_tag)
            if concurrent_plan is not None:
                return concurrent_plan
            if attempt == retries - 1:
                raise
            sleep(float(2**attempt))

    raise AssertionError("Unreachable retry loop exit")


def delete_planned_releases(
    plan: CleanupPlan,
    *,
    delete_tag: Callable[[str], None],
    delete_release: Callable[[int], None],
) -> None:
    for release in plan.delete:
        try:
            delete_tag(release.tag_name)
        except GitHubApiError as exc:
            if exc.status != 404:
                raise

        try:
            delete_release(release.release_id)
        except GitHubApiError as exc:
            if exc.status != 404:
                raise


def cleanup_prereleases(
    *,
    current_tag: str,
    fetch_releases: Callable[[], list[dict[str, Any]]],
    delete_tag: Callable[[str], None],
    delete_release: Callable[[int], None],
    sleep: Callable[[float], None] = time.sleep,
) -> CleanupPlan:
    plan = resolve_cleanup_plan(fetch_releases, current_tag, sleep=sleep)
    for _ in range(3):
        delete_planned_releases(plan, delete_tag=delete_tag, delete_release=delete_release)
        plan = resolve_cleanup_plan(fetch_releases, current_tag, sleep=sleep)
        if not plan.delete:
            return plan

    raise RuntimeError("Prerelease cleanup did not converge after three refreshes.")


def request_json(url: str, token: str | None) -> dict[str, Any] | list[Any]:
    request = Request(url, headers=github_headers(token))
    try:
        with urlopen(request) as response:
            return json.load(response)
    except HTTPError as exc:
        raise GitHubApiError(exc.code, f"GitHub API request failed: {url}") from exc


def delete_request(url: str, token: str | None) -> None:
    request = Request(url, headers=github_headers(token), method="DELETE")
    try:
        with urlopen(request):
            return
    except HTTPError as exc:
        raise GitHubApiError(exc.code, f"GitHub API delete failed: {url}") from exc


def github_headers(token: str | None) -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "AALC-Prerelease-Cleanup",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def fetch_paginated_releases(repo: str, token: str | None, github_api_url: str) -> list[dict[str, Any]]:
    releases: list[dict[str, Any]] = []
    page = 1
    while True:
        payload = request_json(
            f"{github_api_url}/repos/{repo}/releases?per_page=100&page={page}",
            token,
        )
        if not isinstance(payload, list):
            raise ValueError("GitHub releases response was not a list")
        if not payload:
            return releases
        releases.extend(item for item in payload if isinstance(item, dict))
        if len(payload) < 100:
            return releases
        page += 1


def delete_tag(repo: str, tag_name: str, token: str | None, github_api_url: str) -> None:
    encoded_tag = quote(tag_name, safe="")
    delete_request(f"{github_api_url}/repos/{repo}/git/refs/tags/{encoded_tag}", token)


def delete_release(repo: str, release_id: int, token: str | None, github_api_url: str) -> None:
    delete_request(f"{github_api_url}/repos/{repo}/releases/{release_id}", token)


def write_github_output(path: str | None, plan: CleanupPlan) -> None:
    if not path:
        return
    with open(path, "a", encoding="utf-8") as file:
        file.write(f"retained={str(plan.current_retained).lower()}\n")
        file.write(f"retained_tag={plan.retained_tag}\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Keep only the highest beta prerelease for the current base version.")
    parser.add_argument("--repo", required=True, help="GitHub repository in owner/name format.")
    parser.add_argument("--current-tag", required=True, help="Published beta tag for the current CI run.")
    parser.add_argument("--github-token", default=os.environ.get("GITHUB_TOKEN"))
    parser.add_argument("--github-api-url", default=os.environ.get("GITHUB_API_URL", "https://api.github.com"))
    parser.add_argument("--github-output", default=os.environ.get("GITHUB_OUTPUT"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.github_token:
        raise ValueError("A GitHub token is required to clean prereleases.")

    def fetch_releases() -> list[dict[str, Any]]:
        return fetch_paginated_releases(args.repo, args.github_token, args.github_api_url)

    plan = cleanup_prereleases(
        current_tag=args.current_tag,
        fetch_releases=fetch_releases,
        delete_tag=lambda tag_name: delete_tag(args.repo, tag_name, args.github_token, args.github_api_url),
        delete_release=lambda release_id: delete_release(args.repo, release_id, args.github_token, args.github_api_url),
    )
    write_github_output(args.github_output, plan)
    sys.stdout.write(f"Retained beta prerelease: {plan.retained_tag}\n")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        sys.stderr.write(f"Failed to clean prereleases: {exc}\n")
        raise SystemExit(1) from exc

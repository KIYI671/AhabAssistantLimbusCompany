"""决定帮助页里点击链接后做什么（不依赖 Qt）。

帮助页可以在本地的帮助文档（用法详解、常见问题）之间跳转；
README 是项目首页，开头没有回到帮助页的导航，所以用浏览器打开 GitHub 上的版本。

链接以百分号编码的字符串传入（界面用 QUrl.toString(FullyEncoded) 得到）。
"""

import os
from collections.abc import Callable
from dataclasses import dataclass
from urllib.parse import unquote, urlsplit


@dataclass(frozen=True)
class ScrollTo:
    """在当前页内滚动到锚点；fragment 为空表示回到顶部"""

    fragment: str


@dataclass(frozen=True)
class ShowDoc:
    """在帮助页里换成另一份本地文档，然后滚动到 fragment"""

    path: str
    fragment: str


@dataclass(frozen=True)
class OpenExternal:
    """用系统浏览器打开"""

    url: str


def _same_file(a: str, b: str) -> bool:
    return os.path.normcase(os.path.normpath(a.lstrip("/"))) == os.path.normcase(os.path.normpath(b.lstrip("/")))


def _is_readme(path: str) -> bool:
    return os.path.basename(path).lower().startswith("readme")


def resolve_help_link(
    href: str, current_path: str, *, repo_url: str, exists: Callable[[str], bool] = os.path.isfile
) -> ScrollTo | ShowDoc | OpenExternal | None:
    """repo_url 是 GitHub 仓库地址，README 会链到它的 main 分支。返回 None 表示忽略这个链接"""
    link = urlsplit(href)
    if link.scheme in ("http", "https"):
        return OpenExternal(href)
    if link.scheme != "":
        return None

    path = unquote(link.path)
    fragment = unquote(link.fragment)
    if path == "" or _same_file(path, current_path):
        return ScrollTo(fragment)

    path = path.lstrip("/")
    if _is_readme(path):
        # 交给浏览器的地址保持编码后的样子
        return OpenExternal(
            f"{repo_url}/blob/main/" + link.path.lstrip("/") + (f"#{link.fragment}" if link.fragment else "")
        )

    if path.endswith(".md") and exists(path):
        return ShowDoc(path, fragment)
    return None

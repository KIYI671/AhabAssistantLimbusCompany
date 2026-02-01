"""
A markdown-it-py plugin to wrap images in div containers.

This plugin processes paragraph tokens containing only images and wraps them in div containers,
similar to the markdown-it-figure plugin for JavaScript markdown-it.

Features:
- Wraps standalone images in configurable div containers
- Supports images wrapped in links
- Adds tabindex for accessibility (optional)
- Preserves alt text and title attributes
- Handles multiple images in separate containers
- Does not interfere with inline images (images mixed with text)

Usage:
    from markdown_it import MarkdownIt
    from markdown_it_imgdiv import imgdiv_plugin

    md = MarkdownIt()
    md.use(imgdiv_plugin, class_name="figure", focusable=True)

    # Example input:
    # ![Alt text](image.jpg)
    #
    # Example output:
    # <div class="figure"><img src="image.jpg" alt="Alt text" tabindex="0" /></div>
"""

from typing import TYPE_CHECKING, Optional, Sequence

from markdown_it import MarkdownIt
from markdown_it.rules_core import StateCore

if TYPE_CHECKING:
    from markdown_it.renderer import RendererProtocol
    from markdown_it.token import Token
    from markdown_it.utils import EnvType, OptionsDict


def imgdiv_plugin(
    md: MarkdownIt,
    class_name: str = "image-container",
    focusable: bool = True,
    align: Optional[str] = None,
) -> None:
    """
    Plugin to wrap images in div containers.

    Args:
        md: The MarkdownIt instance
        class_name: CSS class name for the div wrapper (default: "image-container")
        focusable: Whether to add tabindex="0" to images for accessibility (default: True)
    """

    def imgdiv_rule(state: StateCore) -> None:
        """Core rule to process tokens and wrap images in divs."""

        # Process tokens from start to end, looking for image patterns
        i = 0
        while i < len(state.tokens):
            token = state.tokens[i]

            # Skip if not a paragraph_open token
            if token.type != "paragraph_open":
                i += 1
                continue

            # Check if we have the pattern: paragraph_open -> inline -> paragraph_close
            if (
                i + 2 >= len(state.tokens)
                or state.tokens[i + 1].type != "inline"
                or state.tokens[i + 2].type != "paragraph_close"
            ):
                i += 1
                continue

            inline_token = state.tokens[i + 1]

            # Check if inline token contains only image(s) or image(s) wrapped in link(s)
            if not _is_image_only_content(inline_token):
                i += 1
                continue

            # We have a paragraph containing only image(s)
            # Convert paragraph tokens to div tokens
            paragraph_open = state.tokens[i]
            paragraph_close = state.tokens[i + 2]

            # Transform paragraph_open to div_open
            paragraph_open.type = "div_open"
            paragraph_open.tag = "div"
            paragraph_open.attrSet("class", class_name)
            if align:
                paragraph_open.attrSet("align", align)

            # Transform paragraph_close to div_close
            paragraph_close.type = "div_close"
            paragraph_close.tag = "div"

            # Process images within the inline token
            if inline_token.children:
                _process_images(inline_token.children, focusable)

            # Move to next token after the processed group
            i += 3

    def _is_image_only_content(inline_token: "Token") -> bool:
        """Check if inline token contains only images or images wrapped in links."""
        if not inline_token.children:
            return False

        children = inline_token.children

        # Single image
        if len(children) == 1 and children[0].type == "image":
            return True

        # Image wrapped in link: link_open -> image -> link_close
        if (
            len(children) == 3
            and children[0].type == "link_open"
            and children[1].type == "image"
            and children[2].type == "link_close"
        ):
            return True

        # Multiple images (potentially mixed with links)
        i = 0
        while i < len(children):
            child = children[i]

            if child.type == "image":
                # Standalone image
                i += 1
            elif (
                child.type == "link_open"
                and i + 2 < len(children)
                and children[i + 1].type == "image"
                and children[i + 2].type == "link_close"
            ):
                # Image wrapped in link
                i += 3
            else:
                # Non-image content found
                return False

        return True

    def _process_images(children: Sequence["Token"], focusable: bool) -> None:
        """Process images within the children tokens."""
        for child in children:
            if child.type == "image":
                _enhance_image(child, focusable)

    def _enhance_image(image_token: "Token", focusable: bool) -> None:
        """Enhance a single image token."""
        # Add focusable attribute if enabled
        if focusable:
            image_token.attrSet("tabindex", "0")

    # Register the core rule
    md.core.ruler.before("linkify", "imgdiv", imgdiv_rule)


# Use default renderers for div tokens
def render_div_open(
    self: "RendererProtocol",
    tokens: Sequence["Token"],
    idx: int,
    options: "OptionsDict",
    env: "EnvType",
) -> str:
    """Render opening div tag using default renderer."""
    return self.renderToken(tokens, idx, options, env)  # type: ignore[attr-defined,no-any-return]


def render_div_close(
    self: "RendererProtocol",
    tokens: Sequence["Token"],
    idx: int,
    options: "OptionsDict",
    env: "EnvType",
) -> str:
    """Render closing div tag using default renderer."""
    return self.renderToken(tokens, idx, options, env)  # type: ignore[attr-defined,no-any-return]


# Example usage and testing
if __name__ == "__main__":
    from markdown_it import MarkdownIt

    # Create markdown-it instance with the plugin
    md = MarkdownIt("commonmark", {"breaks": True, "linkify": True})
    md.use(imgdiv_plugin, class_name="figure", focusable=True)

    # Add custom renderers
    md.add_render_rule("div_open", render_div_open)
    md.add_render_rule("div_close", render_div_close)

    # Test cases
    test_cases = [
        "![Alt text](image.jpg)",
        "[![Alt text](image.jpg)](link.html)",
        "![Alt text](image.jpg 'Title text')",
        "Some text ![image](img.jpg) more text",
        "![Image 1](img1.jpg)\n\n![Image 2](img2.jpg)",
        "![](image.jpg)\n\nSome paragraph text.",
    ]

    print("Testing markdown-it-imgdiv plugin:")
    print("=" * 50)

    for i, test in enumerate(test_cases, 1):
        print(f"\nTest {i}: {test}")
        print("-" * 30)
        result = md.render(test)
        print(result)

from qfluentwidgets import FluentIconBase, FluentIcon, Theme, getIconColor, isDarkTheme
from enum import Enum


class OverflowIcons(FluentIconBase, Enum):
    """放一些超出了渲染范围的svg图标

    即范围外还有数据的图标"""

    DOUBLE_ADD = "double_add"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.reverse = False

    def path(self, theme=Theme.AUTO):
        if self.reverse:
            theme = Theme.DARK if not isDarkTheme() else Theme.LIGHT
        return f"assets/app/svgs/icons/{self.value}_{getIconColor(theme)}.svg"

    def set_reverse(self, reverse: bool):
        self.reverse = reverse

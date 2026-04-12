from qfluentwidgets import FluentIconBase, FluentIcon, Theme, getIconColor
from enum import Enum


class Icons(FluentIconBase, Enum):
    DOUBLE_ADD = "double_add"

    def path(self, theme=Theme.AUTO):
        return f"assets/app/svgs/icons/{self.value}_{getIconColor(theme)}.svg"

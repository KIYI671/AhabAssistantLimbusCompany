"""Native hover notes: retain every explanation without a permanent text row."""

from PySide6.QtWidgets import QLabel
from qfluentwidgets import SettingCard


def set_hover_note(widget, key, text):
    parts = getattr(widget, "_explanation_notes", None)
    if parts is None:
        parts = {"existing": widget.toolTip()} if widget.toolTip() else {}
        widget._explanation_notes = parts
    parts[key] = text or ""
    widget.setToolTip("\n\n".join(part for part in parts.values() if part))


class HoverNoteLabel(QLabel):
    """Hidden text model, so dynamic status hints also update their tooltips."""

    def __init__(self, text, parent, targets=()):
        super().__init__(parent)
        self.targets = []
        self.setObjectName("hoverExplanation")
        self.setText(text)
        for target in targets:
            self.add_target(target)
        self.hide()

    def add_target(self, target):
        if target not in self.targets:
            self.targets.append(target)
        set_hover_note(target, id(self), self.text())

    def setText(self, text):
        super().setText(text)
        for target in self.targets:
            set_hover_note(target, id(self), text)


def move_setting_notes_to_hover(root):
    """Only explanatory setting-card content; editable values remain visible."""
    for card in root.findChildren(SettingCard):
        if card is getattr(root, "game_path_card", None):
            continue
        if type(card).__name__ in {"PushSettingCardDate", "PushSettingCardMirrorchyan"}:
            continue
        text = card.contentLabel.text()
        set_hover_note(card.titleLabel, "setting-content", text)
        set_hover_note(card, "setting-content", text)
        card.contentLabel.hide()
        card.setFixedHeight(50)

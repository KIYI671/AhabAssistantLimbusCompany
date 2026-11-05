"""Exercise the real observation inputs offscreen, without loading user config."""

import ast
import os
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPoint, QPointF, Qt, Signal
from PySide6.QtGui import QWheelEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QHBoxLayout, QLabel, QScrollArea, QVBoxLayout, QWidget
from qfluentwidgets import PushButton, SpinBox

ROOT = Path(__file__).resolve().parents[1]


def load_observation_row():
    # Importing app initializes the application's config writer. Compile only
    # these unchanged class definitions so the test cannot load/save user data.
    source = ast.parse((ROOT / "app/rabbit_options.py").read_text(encoding="utf-8"))
    names = {"ObservationCoordinateSpinBox", "ObservePackRuleRow"}
    classes = [node for node in source.body if isinstance(node, ast.ClassDef) and node.name in names]
    assert {node.name for node in classes} == names
    namespace = dict(globals())
    exec(compile(ast.Module(body=classes, type_ignores=[]), "app/rabbit_options.py", "exec"), namespace)
    return namespace["ObservePackRuleRow"]


ObservePackRuleRow = load_observation_row()
APP = QApplication.instance() or QApplication([])


def send_wheel(widget, delta):
    center = widget.rect().center()
    event = QWheelEvent(
        QPointF(center), QPointF(widget.mapToGlobal(center)), QPoint(), QPoint(0, delta),
        Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier, Qt.ScrollPhase.ScrollUpdate, False,
    )
    QApplication.sendEvent(widget, event)
    return event


class ObservationCoordinateInputTests(unittest.TestCase):
    def setUp(self):
        self.row = ObservePackRuleRow([2, 2, 2])
        self.row.show()
        self.row.activateWindow()
        APP.processEvents()
        self.changes = []
        self.row.changed.connect(lambda: self.changes.append(self.row.value()))

    def tearDown(self):
        self.row.close()
        self.row.deleteLater()

    def test_wheel_keeps_each_coordinate_with_or_without_focus(self):
        for name in ("floor", "row", "column"):
            control = getattr(self.row, name)
            for focused in (False, True):
                with self.subTest(coordinate=name, focused=focused):
                    if focused:
                        control.setFocus()
                    else:
                        control.clearFocus()
                    APP.processEvents()
                    self.assertEqual(control.hasFocus(), focused)
                    for target in (control, control.lineEdit()):
                        for delta in (120, -360):
                            send_wheel(target, delta)
                            self.assertEqual(self.row.value(), [2, 2, 2])
                            self.assertEqual(self.changes, [])

    def test_reported_second_and_third_floor_drift_is_blocked(self):
        third = ObservePackRuleRow([3, 2, 5])
        third.changed.connect(lambda: self.changes.append(third.value()))
        try:
            send_wheel(self.row.row, 120)
            send_wheel(third.column, -360)
            self.assertEqual(self.row.value(), [2, 2, 2])
            self.assertEqual(third.value(), [3, 2, 5])
            self.assertEqual(self.changes, [])
        finally:
            third.close()
            third.deleteLater()

    def test_explicit_values_buttons_and_keyboard_still_emit_changes(self):
        for name in ("floor", "row", "column"):
            with self.subTest(coordinate=name):
                control = getattr(self.row, name)
                for change, expected in (
                    (lambda: control.setValue(3), 3),
                    (lambda: QTest.mouseClick(control.upButton, Qt.MouseButton.LeftButton), 4),
                    (lambda: QTest.mouseClick(control.downButton, Qt.MouseButton.LeftButton), 3),
                    (lambda: QTest.keyClick(control, Qt.Key.Key_Up), 4),
                ):
                    self.changes.clear()
                    change()
                    self.assertEqual(control.value(), expected)
                    self.assertEqual(self.changes, [self.row.value()])
                self.changes.clear()
                control.lineEdit().selectAll()
                QTest.keyClicks(control.lineEdit(), "2")
                QTest.keyClick(control, Qt.Key.Key_Return)
                self.assertEqual(control.value(), 2)
                self.assertTrue(self.changes)
                self.assertEqual(self.changes[-1], self.row.value())

    def test_ignored_wheel_remains_available_to_the_page_scroll_area(self):
        area = QScrollArea()
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.addWidget(self.row)
        spacer = QWidget()
        spacer.setFixedHeight(600)
        layout.addWidget(spacer)
        area.setWidget(content)
        area.setWidgetResizable(True)
        area.resize(800, 160)
        area.show()
        APP.processEvents()
        try:
            scrollbar = area.verticalScrollBar()
            before = scrollbar.value()
            event = send_wheel(self.row.row, -120)
            self.assertFalse(event.isAccepted())
            # sendEvent targets one receiver and does not reproduce native
            # wheel bubbling; deliver the ignored event to its scroll parent.
            QApplication.sendEvent(area.viewport(), event)
            self.assertGreater(scrollbar.value(), before)
            self.assertEqual(self.row.value(), [2, 2, 2])
            self.assertEqual(self.changes, [])
        finally:
            self.row.setParent(None)
            area.close()
            area.deleteLater()


if __name__ == "__main__":
    unittest.main()

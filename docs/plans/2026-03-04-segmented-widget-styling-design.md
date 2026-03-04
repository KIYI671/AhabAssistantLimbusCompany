# SegmentedWidget Custom Styling Design

**Date**: 2026-03-04
**Status**: Approved
**Author**: AI Assistant + User

## Background

### Problem Statement

The project needs to customize the appearance of `SegmentedWidget` (from qfluentwidgets) with:
- Rounded corners on outer edges
- Sharp corners between inner segments
- Theme-aware borders and backgrounds
- Smooth sliding animation with themed highlight

### Previous Attempt

A previous implementation attempted to use dynamic `paintEvent` replacement without subclassing. While functional, it had issues:
- Lost original `SegmentedWidget` paint logic
- Required manual application in each usage location
- Hard-coded magic numbers
- No centralized management

### Requirements

1. **Immediate need (Phase 1)**: Apply custom styling using subclass pattern
2. **Future need (Phase 2)**: Enable global application with zero code changes
3. **Consistency**: Match the existing `FullWidthPivot` pattern in the codebase
4. **Maintainability**: Centralized configuration in `ui_config.py`

## Solution Overview

### Architecture

```
┌─────────────────────────────────────────────────┐
│          Application Layer                      │
├─────────────────────────────────────────────────┤
│  Phase 1 (Now)        │  Phase 2 (Future)       │
│  Manual Subclass      │  Global Auto-Apply      │
│                       │                         │
│  CustomSegmented-     │  apply_custom_          │
│  Widget(parent)       │  widget_styles()        │
│                       │  ↓                      │
│                       │  Monkey patch global    │
└──────────┬────────────┴──────────┬──────────────┘
           │                       │
           └──────────┬────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│         CustomSegmentedWidget Class             │
│  - Inherits from SegmentedWidget                │
│  - Auto-applies custom style                    │
│  - Responds to theme changes                    │
└──────────┬──────────────────────────────────────┘
           ↓
┌─────────────────────────────────────────────────┐
│       ui_config.py Style Configuration          │
│  - SEGMENTED_WIDGET_STYLES (QSS)                │
│  - Style constants (radius, colors, etc.)       │
│  - segmented_widget_paint_event()               │
│  - get_segmented_widget_qss()                   │
└─────────────────────────────────────────────────┘
```

### File Structure

```
app/
├── common/
│   └── ui_config.py          # Style config (extend existing)
├── custom_widgets.py         # NEW: Custom components
│   └── CustomSegmentedWidget # Subclass implementation
└── page_card.py              # Uses custom component
```

## Detailed Design

### 1. Style Configuration (ui_config.py)

#### Constants

```python
# SegmentedWidget style constants
SEGMENTED_WIDGET_BORDER_RADIUS = 6.0  # Outer border radius
SEGMENTED_WIDGET_EDGE_TOLERANCE = 2   # Edge detection tolerance (pixels)

# SegmentedWidget theme color opacity
DARK_BORDER_ALPHA = 40       # Dark theme border opacity
DARK_BG_ALPHA = 5            # Dark theme background opacity
LIGHT_BORDER_ALPHA = 30      # Light theme border opacity
LIGHT_BG_ALPHA = 3           # Light theme background opacity
DARK_SELECTED_BG_ALPHA = 255 # Dark theme selected background opacity
LIGHT_SELECTED_BG_ALPHA = 255# Light theme selected background opacity
```

#### QSS Styles

```python
SEGMENTED_WIDGET_STYLES = {
    "light": """
        SegmentedWidget {
            background: transparent;
            border: none;
        }
        SegmentedItem[pivotItem="true"] {
            padding: 6px 16px;
            font-size: 14px;
            font-weight: 400;
            color: rgba(0, 0, 0, 0.7);
            background: transparent;
            border: none;
        }
        SegmentedItem[pivotItem="true"]:hover {
            color: rgba(0, 0, 0, 0.9);
        }
        SegmentedItem[pivotItem="true"][selected="true"] {
            color: {theme_color};
            font-weight: bold;
        }
    """,
    "dark": """
        SegmentedWidget {
            background: transparent;
            border: none;
        }
        SegmentedItem[pivotItem="true"] {
            padding: 6px 16px;
            font-size: 14px;
            font-weight: 400;
            color: rgba(255, 255, 255, 0.7);
            background: transparent;
            border: none;
        }
        SegmentedItem[pivotItem="true"]:hover {
            color: rgba(255, 255, 255, 0.9);
        }
        SegmentedItem[pivotItem="true"][selected="true"] {
            color: {theme_color};
            font-weight: bold;
        }
    """,
}

def get_segmented_widget_qss(theme_color: str) -> tuple[str, str]:
    """Return (light_qss, dark_qss) for SegmentedWidget."""
    light_qss = SEGMENTED_WIDGET_STYLES["light"].format(theme_color=theme_color)
    dark_qss = SEGMENTED_WIDGET_STYLES["dark"].format(theme_color=theme_color)
    return light_qss, dark_qss
```

#### Custom Paint Event

```python
def segmented_widget_paint_event(
    widget: "SegmentedWidget",
    e: "QPaintEvent",
    original_paint_event
) -> None:
    """
    Custom paintEvent for SegmentedWidget with rounded outer corners
    and sharp inner corners.

    Args:
        widget: SegmentedWidget instance
        e: QPaintEvent event
        original_paint_event: Original paintEvent method to preserve base functionality
    """
    from qfluentwidgets import isDarkTheme, themeColor

    # Call original paintEvent first (preserve animations, states)
    if original_paint_event is not None:
        original_paint_event(e)
    else:
        QWidget.paintEvent(widget, e)

    # Validate widget has required attributes
    if not hasattr(widget, 'items') or not widget.items:
        return

    painter = QPainter(widget)
    painter.setRenderHints(QPainter.Antialiasing)

    # 1. Draw outer border and background
    is_dark = isDarkTheme()
    if is_dark:
        border_color = QColor(255, 255, 255, DARK_BORDER_ALPHA)
        bg_color = QColor(255, 255, 255, DARK_BG_ALPHA)
    else:
        border_color = QColor(0, 0, 0, LIGHT_BORDER_ALPHA)
        bg_color = QColor(0, 0, 0, LIGHT_BG_ALPHA)

    painter.setPen(QPen(border_color, 1))
    painter.setBrush(bg_color)

    rect_all = widget.rect().adjusted(1, 1, -1, -1)
    painter.drawRoundedRect(
        rect_all,
        SEGMENTED_WIDGET_BORDER_RADIUS,
        SEGMENTED_WIDGET_BORDER_RADIUS
    )

    # 2. Draw vertical dividers between items
    items = list(widget.items.values())
    for i in range(len(items) - 1):
        item_rect = items[i].geometry()
        x = item_rect.right()
        painter.drawLine(x, rect_all.top(), x, rect_all.bottom())

    # 3. Early return if no selected item
    if not widget.currentItem():
        return

    # 4. Draw selected item highlight with theme color
    c = themeColor()
    painter.setPen(QPen(c, 1.5))
    if is_dark:
        painter.setBrush(QColor(30, 30, 30, DARK_SELECTED_BG_ALPHA))
    else:
        painter.setBrush(QColor(255, 255, 255, LIGHT_SELECTED_BG_ALPHA))

    item = widget.currentItem()
    slidex = int(widget.slideAni.value())

    rect_active = QRectF(slidex + 1, 1, item.width() - 2, widget.height() - 2)

    # Draw custom shape with rounded outer corners and sharp inner corners
    path = QPainterPath()

    is_left_edge = slidex <= widget.rect().left() + SEGMENTED_WIDGET_EDGE_TOLERANCE
    is_right_edge = (
        slidex + item.width() >= widget.rect().right() - SEGMENTED_WIDGET_EDGE_TOLERANCE
    )

    if is_left_edge and is_right_edge:
        # Single item: all corners rounded
        path.addRoundedRect(
            rect_active,
            SEGMENTED_WIDGET_BORDER_RADIUS,
            SEGMENTED_WIDGET_BORDER_RADIUS,
        )
    else:
        # Multiple items: outer corners rounded, inner corners sharp
        x, y, w, h = (
            rect_active.x(),
            rect_active.y(),
            rect_active.width(),
            rect_active.height(),
        )
        radius = SEGMENTED_WIDGET_BORDER_RADIUS

        # Build path manually
        path.moveTo(x + (radius if is_left_edge else 0), y)

        # Top edge and top-right corner
        if is_right_edge:
            path.lineTo(x + w - radius, y)
            path.arcTo(x + w - 2 * radius, y, 2 * radius, 2 * radius, 90, -90)
        else:
            path.lineTo(x + w, y)

        # Right edge and bottom-right corner
        if is_right_edge:
            path.lineTo(x + w, y + h - radius)
            path.arcTo(
                x + w - 2 * radius, y + h - 2 * radius, 2 * radius, 2 * radius, 0, -90
            )
        else:
            path.lineTo(x + w, y + h)

        # Bottom edge and bottom-left corner
        if is_left_edge:
            path.lineTo(x + radius, y + h)
            path.arcTo(x, y + h - 2 * radius, 2 * radius, 2 * radius, 270, -90)
        else:
            path.lineTo(x, y + h)

        # Left edge and close path
        path.lineTo(x, y + (radius if is_left_edge else 0))
        if is_left_edge:
            path.arcTo(x, y, 2 * radius, 2 * radius, 180, -90)

    painter.drawPath(path)
```

### 2. CustomSegmentedWidget Class (custom_widgets.py)

```python
from PySide6.QtGui import QPaintEvent
from qfluentwidgets import SegmentedWidget, qconfig, setCustomStyleSheet, themeColor

from app.common.ui_config import (
    get_segmented_widget_qss,
    segmented_widget_paint_event,
)


class CustomSegmentedWidget(SegmentedWidget):
    """
    Custom SegmentedWidget with rounded outer corners and sharp inner corners.

    Features:
    - Automatically applies custom styling
    - Responds to theme changes
    - Fully compatible with original SegmentedWidget API

    Usage:
        widget = CustomSegmentedWidget(parent)
        widget.addItem("key1", "Label 1")
        widget.addItem("key2", "Label 2")
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        # Save original paintEvent
        self._original_paint_event = super().paintEvent

        # Apply custom style
        self._apply_custom_style()

        # Connect theme change signal
        qconfig.themeChanged.connect(self._update_theme)

    def _apply_custom_style(self):
        """Apply custom QSS styling."""
        color = themeColor().name()
        light_qss, dark_qss = get_segmented_widget_qss(color)
        setCustomStyleSheet(self, light_qss, dark_qss)

    def _update_theme(self):
        """Update styling when theme changes."""
        self._apply_custom_style()
        self.update()

    def paintEvent(self, e: QPaintEvent):
        """Custom paint event with rounded corners."""
        segmented_widget_paint_event(self, e, self._original_paint_event)
```

### 3. Phase 2 Global Application (Future)

```python
# In ui_config.py

def apply_custom_widget_styles():
    """
    Apply custom widget styles globally via monkey patching.

    Call this once at application startup to automatically style
    all SegmentedWidget instances without code changes.

    Usage:
        # In main.py or my_app.py
        from app.common.ui_config import apply_custom_widget_styles
        apply_custom_widget_styles()
    """
    from qfluentwidgets import SegmentedWidget

    # Check if already applied
    if hasattr(SegmentedWidget, '_custom_style_applied'):
        log.warning("Custom widget styles already applied, skipping")
        return

    # Mark as applied
    SegmentedWidget._custom_style_applied = True

    # Save original __init__
    _original_init = SegmentedWidget.__init__

    def _custom_init(self, parent=None):
        _original_init(self, parent)
        _apply_segmented_widget_custom_style(self)

    # Replace __init__
    SegmentedWidget.__init__ = _custom_init


def _apply_segmented_widget_custom_style(widget):
    """
    Internal function to apply custom style to a widget instance.
    Shared by CustomSegmentedWidget and apply_custom_widget_styles().
    """
    # Save original paintEvent
    original_paint = widget.paintEvent

    # Apply QSS
    color = themeColor().name()
    light_qss, dark_qss = get_segmented_widget_qss(color)
    setCustomStyleSheet(widget, light_qss, dark_qss)

    # Replace paintEvent
    widget.paintEvent = lambda e: segmented_widget_paint_event(
        widget, e, original_paint
    )

    # Connect theme change
    def update_style():
        color = themeColor().name()
        light_qss, dark_qss = get_segmented_widget_qss(color)
        setCustomStyleSheet(widget, light_qss, dark_qss)
        widget.update()

    qconfig.themeChanged.connect(update_style)
```

## Data Flow

### Initialization Flow (Phase 1)

```
User Code
  │
  ├─ CustomSegmentedWidget(parent)
  │
  └─> CustomSegmentedWidget.__init__()
       │
       ├─ super().__init__(parent)        # Call SegmentedWidget init
       │
       ├─ self._original_paint_event = super().paintEvent
       │
       ├─ self._apply_custom_style()
       │   │
       │   ├─ themeColor().name() → color
       │   │
       │   ├─ get_segmented_widget_qss(color) → (light_qss, dark_qss)
       │   │
       │   └─ setCustomStyleSheet(self, light_qss, dark_qss)
       │
       └─ qconfig.themeChanged.connect(self._update_theme)
```

### Theme Change Flow

```
User switches theme
  │
  └─> qconfig.themeChanged signal
       │
       └─> CustomSegmentedWidget._update_theme()
            │
            ├─ self._apply_custom_style()
            │
            └─ self.update()
                 │
                 └─> paintEvent(e)
```

### Paint Flow

```
Qt event loop triggers paintEvent
  │
  └─> CustomSegmentedWidget.paintEvent(e)
       │
       └─> segmented_widget_paint_event(self, e, self._original_paint_event)
            │
            ├─ [1] original_paint_event(e)      # Preserve animations
            │
            ├─ [2] Validate widget.items exists
            │
            ├─ [3] Draw outer border and dividers
            │
            └─ [4] Draw selected item highlight with custom corners
```

## Error Handling

### Edge Cases

1. **Empty widget** (0 items): Early return after validation
2. **Single item**: All four corners rounded
3. **Animation state**: Convert `slideAni.value()` to int
4. **Theme change during paint**: Cache `isDarkTheme()` result
5. **Missing original paintEvent**: Fallback to `QWidget.paintEvent`

### Error Recovery

```python
def _apply_custom_style(self):
    try:
        # Apply QSS and paintEvent
        ...
    except Exception as e:
        log.warning(f"Failed to apply custom SegmentedWidget style: {e}")
        # Keep default style, don't break functionality
```

## Testing Strategy

### Test Scenarios

1. **Basic functionality**
   - Normal initialization
   - Adding items (2, 3, single)
   - Switching selected item
   - Animation transitions

2. **Style application**
   - QSS correctly loaded
   - Theme color applied
   - Theme switch updates style

3. **Edge cases**
   - Empty widget (0 items)
   - Single item (all corners rounded)
   - Multiple items (outer rounded + inner sharp)

4. **Phase 2** (future)
   - `apply_custom_widget_styles()` works
   - No duplicate application
   - No conflict with manual `CustomSegmentedWidget`

### Visual Regression

- Outer corner radius = 6.0px
- Inner dividers correctly drawn
- Selected highlight positioned correctly
- Theme switch updates colors

## Migration Path

### PageCard Migration

**Before** (rolled back state):
```python
from qfluentwidgets import SegmentedWidget

self.pivot = SegmentedWidget(self)
self.pivot.setFixedHeight(50)
```

**After**:
```python
from app.custom_widgets import CustomSegmentedWidget

self.pivot = CustomSegmentedWidget(self)
self.pivot.setFixedHeight(36)  # Updated height
```

**Changes**:
- Import path change
- Class name change
- Height adjustment
- All other method calls unchanged (fully compatible)

## Implementation Plan

### Phase 1 (Current)

1. ✅ Extend `ui_config.py` with constants, QSS, and paint function
2. ✅ Create `custom_widgets.py` with `CustomSegmentedWidget`
3. ✅ Migrate `PageCard` to use `CustomSegmentedWidget`
4. ✅ Test basic functionality and theme switching

### Phase 2 (Future)

1. Implement `apply_custom_widget_styles()` in `ui_config.py`
2. Call it at application startup
3. Gradually remove manual `CustomSegmentedWidget` usage
4. Test with all existing `SegmentedWidget` instances

## Dependencies

- **qfluentwidgets** >= 1.0.0 (requires `SegmentedWidget.items`, `slideAni`, `currentItem()`)
- **PySide6** >= 6.0 (uses `QPainterPath`, `QRectF`, etc.)

## References

- Existing pattern: `app/custom_pivot.py` (`FullWidthPivot`)
- Style configuration: `app/common/ui_config.py`
- Code review feedback: Previous implementation issues addressed

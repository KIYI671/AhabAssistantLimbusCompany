# Sidebar Layout for Settings Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a fixed left-side navigation for the settings page that scrolls the right content to the corresponding section and highlights the active section.

**Architecture:** Convert SettingInterface into a two-column layout: left nav frame (fixed width) + right ScrollArea containing existing ExpandLayout with all setting groups. Navigation items map to existing group widgets; clicks use ensureWidgetVisible; scroll events update active highlight.

**Tech Stack:** PySide6, qfluentwidgets, existing BaseSettingCardGroup components.

---

### Task 1: Restructure SettingInterface into two-column container

**Files:**
- Modify: `app/setting_interface.py`

**Step 1: Add container widgets**
- Introduce `main_widget = QWidget()` and `main_layout = QHBoxLayout(main_widget)`.
- Create `nav_frame = QFrame()` (fixed width ~180px) with `nav_layout = QVBoxLayout(nav_frame)`.
- Create `content_scroll = QScrollArea()` set to widget-resizable, no horizontal bar.
- Move existing `scroll_widget = QWidget()` + `expand_layout = ExpandLayout(scroll_widget)` into `content_scroll.setWidget(scroll_widget)` and `content_scroll.setWidgetResizable(True)`.
- Set `self.setWidget(main_widget)` and add `nav_frame` and `content_scroll` to `main_layout`.

**Step 2: Keep existing card/group creation**
- Ensure `__init_card`, `__initLayout`, `set_style_sheet`, `__connect_signal` still operate on `scroll_widget`/`expand_layout`.

**Step 3: Run app smoke (manual)**
- Launch app and open settings page; verify content still renders without nav yet.

---

### Task 2: Build navigation items and click-to-scroll

**Files:**
- Modify: `app/setting_interface.py`

**Step 1: Collect group references**
- After groups are constructed, build an ordered list of tuples `[ ("game", "游戏设置", self.game_setting_group), ... ]` following current display order.

**Step 2: Render nav buttons**
- For each tuple, create a QPushButton (or qfluentwidgets Primary button style), flat, full width, add to `nav_layout`.
- Store mapping key -> widget and button for later state updates.

**Step 3: Implement click handler**
- On button click, call `content_scroll.ensureWidgetVisible(target_widget, xMargin=0, yMargin=12)` (or set scrollbar value based on widget.y()).

**Step 4: Manual check**
- Click each nav item; confirm the right pane scrolls to correct group.

---

### Task 3: Active-section highlight on scroll

**Files:**
- Modify: `app/setting_interface.py`

**Step 1: Connect scroll listener**
- Connect `content_scroll.verticalScrollBar().valueChanged` to a handler.
- In handler, compute which group top is closest to current scroll value (use widget.y() and height; consider yMargin offset).

**Step 2: Update button states**
- Maintain a `current_key`; when it changes, apply selected style to the nav button, reset others.

**Step 3: Manual check**
- Scroll manually; observe highlight follows visible section.

---

### Task 4: Style the navigation

**Files:**
- Modify: `app/setting_interface.py` (inline setStyleSheet)

**Step 1: Apply basic QSS**
- nav_frame padding (e.g., 12px), spacing 4–6px.
- Buttons: normal, hover, selected states using palette/Theme colors; ensure text contrast in LIGHT/DARK.
- Hide nav scrollbar; keep right scrollbar default.

**Step 2: Default selection**
- On init, set first item as selected state.

**Step 3: Manual check**
- Toggle theme modes (AUTO/LIGHT/DARK) and visually confirm contrast.

---

### Task 5: Verification pass

**Files:**
- N/A (runtime verification)

**Step 1: Functional checks**
- Click-through all nav items; ensure scroll targets correct groups.
- Manual scroll to confirm highlight updates with position.
- Check with various zoom scales (via existing zoom setting) that layout remains usable and nav width stable.

**Step 2: Regression smoke**
- Confirm existing setting cards still interact (open dialogs, toggles) without layout break.

---

### Task 6: Documentation snapshot (already have design)

**Files:**
- Already added: `docs/plans/2026-03-05-sidebar-layout-design.md`
- Optional: Add a brief note to README/CHANGELOG if the project requires, otherwise skip.

**Step 1: If needed, append a short note**
- If project expects changelog, add a one-liner about sidebar navigation on settings page.

---

### Task 7: Commit

**Files:**
- `app/setting_interface.py`
- (Optional) doc/changelog file if added

**Step 1: Stage changes**
- `git add app/setting_interface.py docs/plans/2026-03-05-sidebar-layout-design.md` (and any doc note if added)

**Step 2: Commit**
- `git commit -m "feat: add settings sidebar navigation"`


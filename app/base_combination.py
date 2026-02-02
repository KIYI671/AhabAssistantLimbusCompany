import base64
import datetime

import pyperclip
from PySide6.QtCore import QObject, QRect, QTime, QUrl, Signal
from PySide6.QtGui import (
    QColor,
    QDesktopServices,
    QKeyEvent,
    QKeySequence,
    QPainter,
    QPixmap,
)
from PySide6.QtWidgets import QFrame, QGraphicsOpacityEffect, QPushButton, QLabel
from qfluentwidgets import (
    IndicatorPosition,
    InfoBarPosition,
    LineEdit,
    MessageBox,
    PrimaryPushButton,
    PrimaryPushSettingCard,
    ProgressBar,
    PushSettingCard,
    SettingCard,
    SettingCardGroup,
    SwitchButton,
    TimePicker,
    setCustomStyleSheet,
)

from app.base_tools import *
from app.base_tools import FluentIconBase, QIcon
from app.card.messagebox_custom import (
    BaseInfoBar,
    MessageBoxDate,
    MessageBoxEdit,
    MessageBoxSpinbox,
)
from app.language_manager import LanguageManager
from module.logger import log
from module.my_error.my_error import settingsTypeError
from module.update.check_update import check_update
from utils.utils import decrypt_string, encrypt_string, get_timezone


class CheckBoxWithButton(QFrame):
    def __init__(
        self,
        check_box_name,
        check_box_title,
        check_box_icon: Union[str, QIcon, FluentIconBase, None],
        button_name,
        parent=None,
    ):
        super().__init__(parent)
        # self.setFixedHeight(80)

        self.hBoxLayout = QHBoxLayout(self)
        self.box_text = check_box_title
        self.box = BaseCheckBox(
            check_box_name, check_box_icon, check_box_title, parent=self
        )
        self.button = ChangePageButton(button_name, parent=self)
        self.hBoxLayout.addWidget(self.box)
        self.hBoxLayout.addWidget(self.button)
        self.hBoxLayout.setAlignment(Qt.AlignCenter)
        task_check_box.append(self.box.check_box)

    def set_box_enabled(self, b: bool):
        self.box.set_box_enabled(b)

    def retranslateUi(self):
        self.box.check_box.setText(self.tr(self.box_text))


class CheckBoxWithLineEdit(QFrame):
    def __init__(self, config_name, check_box_title, parent=None):
        super().__init__(parent)
        self.setObjectName(config_name)
        self.config_name = config_name
        self.hBoxLayout = QHBoxLayout(self)
        self.box = CheckBox(check_box_title, parent=self)
        self.line_edit = LineEdit(self)
        self.line_edit.setMaximumWidth(70)
        self.line_edit.setAlignment(Qt.AlignCenter)
        self.line_edit.setReadOnly(True)
        self.hBoxLayout.addWidget(self.box)
        self.hBoxLayout.addWidget(self.line_edit)
        self.hBoxLayout.setAlignment(Qt.AlignCenter)

        self.box.toggled.connect(self.on_toggle)

    def on_toggle(self, checked):
        data_dict = {self.config_name: checked}
        self.send_switch_signal(data_dict)

    def send_switch_signal(self, target: dict):
        mediator.team_setting.emit(target)

    def set_checked(self, checked):
        self.box.toggled.disconnect(self.on_toggle)
        self.box.setChecked(checked)
        self.box.toggled.connect(self.on_toggle)

    def set_text(self, text):
        self.line_edit.setText(text)


class CheckBoxWithComboBox(QFrame):
    def __init__(
        self,
        check_box_name,
        check_box_title,
        check_box_icon: Union[str, QIcon, FluentIconBase, None],
        combo_box_name,
        combo_box_width=None,
        parent=None,
    ):
        super().__init__(parent)
        # self.setFixedHeight(80)
        self.additional_combo_box = None
        self.hBoxLayout = QHBoxLayout(self)
        self.box_text = check_box_title
        self.box = BaseCheckBox(
            check_box_name, check_box_icon, check_box_title, parent=self, center=False
        )
        self.box.setFixedWidth(150)
        self.combo_box = BaseComboBox(combo_box_name, combo_box_width)
        self.combo_box.setFixedWidth(300)
        self.hBoxLayout.addWidget(self.box, Qt.AlignLeft)
        self.hBoxLayout.addWidget(self.combo_box)
        self.hBoxLayout.setAlignment(Qt.AlignCenter)

    def add_combobox(self, config_name, combo_box_width=None):
        self.additional_combo_box = BaseComboBox(config_name, combo_box_width)
        self.hBoxLayout.addWidget(self.additional_combo_box)

    def add_items(self, items):
        self.combo_box.add_items(items)
        self.items = items

    def add_times_for_additional(self, items):
        try:
            self.additional_combo_box.add_items(items)
        except AttributeError:
            pass

    def retranslateUi(self):
        self.box.check_box.setText(self.tr(self.box_text))
        self.combo_box.retranslateUi()
        if self.additional_combo_box:
            self.additional_combo_box.retranslateUi()


class LabelWithComboBox(QFrame):
    def __init__(self, label_text, config_name, items, vbox=True, parent=None):
        super().__init__(parent)
        self.setObjectName(config_name)

        self.text = label_text
        self.items = items

        if vbox:
            self.layout_ = QVBoxLayout(self)
        else:
            self.layout_ = QHBoxLayout(self)
        self.layout_.setContentsMargins(0, 0, 0, 0)
        self.label = BaseLabel(label_text)
        self.combo_box = BaseComboBox(config_name)
        self.combo_box.add_items(items)
        self.layout_.addWidget(self.label)
        if vbox is not True:
            self.layout_.addSpacing(10)
        self.layout_.addWidget(self.combo_box, Qt.AlignmentFlag.AlignLeft)
        self.layout_.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMaximumHeight(80)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)

    def add_items(self, items):
        self.combo_box.add_items(items)

    def retranslateUi(self):
        self.label.label.setText(self.tr(self.text))
        self.combo_box.retranslateUi()


class LabelWithSpinBox(QFrame):
    def __init__(
        self,
        label_text,
        box_name,
        parent=None,
        double=False,
        min_value=0.1,
        min_step=0.01,
    ):
        super().__init__(parent)
        self.vbox_layout = QVBoxLayout(self)
        self.text = label_text
        self.label = BaseLabel(label_text)
        self.box = BaseSpinBox(
            box_name, double=double, min_value=min_value, min_step=min_step
        )
        self.vbox_layout.addWidget(self.label)
        self.vbox_layout.addWidget(self.box)
        self.vbox_layout.setAlignment(Qt.AlignCenter)
        self.setMaximumHeight(100)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)

    def retranslateUi(self):
        self.label.label.setText(self.tr(self.text))


class MirrorSpinBox(QFrame):
    def __init__(
        self, label_text, box_name, parent=None, double=False, min_value=0, min_step=1
    ):
        super().__init__(parent)
        self.box_layout = QHBoxLayout(self)
        self.text = label_text
        self.label = BaseLabel(label_text)
        self.box = BaseSpinBox(
            box_name, double=double, min_value=min_value, min_step=min_step
        )
        self.box_layout.addWidget(self.label, stretch=1)
        self.box_layout.addWidget(self.box, stretch=2)
        self.setMaximumHeight(70)

    def retranslateUi(self):
        self.label.label.setText(self.tr(self.text))


class MirrorTeamCombination(QFrame):
    def __init__(
        self,
        team_number,
        check_box_name,
        check_box_title,
        check_box_icon: Union[str, QIcon, FluentIconBase, None],
        button_name,
        parent=None,
    ):
        super().__init__(parent)
        self.setObjectName(f"team_{team_number}")

        self.box_text = check_box_title

        self.hBoxLayout = QHBoxLayout(self)
        self.box = BaseCheckBox(
            check_box_name, check_box_icon, check_box_title, parent=self
        )
        self.button = ToSettingButton(button_name, parent=self)

        self.hBoxLayout.setAlignment(Qt.AlignCenter)

        self.team_number = team_number

        self.remark_name = LineEdit()
        self.remark_name.setAlignment(Qt.AlignCenter)
        self.remark_name.setPlaceholderText("备注名")
        self.remark_name.setMaximumWidth(100)
        self.remark_name.textChanged.connect(self.remark_name_changed)

        self.order = LineEdit()
        self.order.setAlignment(Qt.AlignCenter)
        self.order.setReadOnly(True)
        self.order.setMaximumWidth(60)

        self.hBoxLayout.addWidget(self.box)
        self.hBoxLayout.addWidget(self.remark_name)
        self.hBoxLayout.addWidget(self.order)
        self.hBoxLayout.addWidget(self.button)

        self.button.edit_name.triggered.connect(self.edit_button_clicked)
        self.button.del_action.triggered.connect(self.delete_button_clicked)
        self.button.copy_settings.triggered.connect(self.copy_team_settings)
        self.button.paste_settings.triggered.connect(self.paste_team_settings)

        self.refresh_remark_name()

    def copy_team_settings(self):
        setting = str(cfg.get_value(f"team{self.team_number}_setting"))
        setting = "||AALC_TEAM_SETTING||" + setting  # 添加标识符
        setting = base64.b64encode(setting.encode("utf-8")).decode("utf-8")
        pyperclip.copy(setting)
        bar = BaseInfoBar.success(
            title=QT_TRANSLATE_NOOP("BaseInfoBar", "已复制到剪切板"),
            content="",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=500,
            parent=self.parent().parent(),
        )

    def paste_team_settings(self):
        setting = pyperclip.paste().strip()
        try:
            setting = base64.b64decode(setting).decode("utf-8")
            if "||AALC_TEAM_SETTING||" not in setting:
                raise settingsTypeError("不是有效的AALC设置")
            setting = setting.replace("||AALC_TEAM_SETTING||", "", 1)
        except settingsTypeError:
            bar = BaseInfoBar.error(
                title=QT_TRANSLATE_NOOP("BaseInfoBar", "该设置不属于 AALC"),
                content="",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=500,
                parent=self.parent().parent(),
            )
            return
        except Exception:
            bar = BaseInfoBar.error(
                title=QT_TRANSLATE_NOOP("BaseInfoBar", "不是有效的 AALC 设置"),
                content="",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=500,
                parent=self.parent().parent(),
            )
            return

        data: dict = cfg.yaml.load(setting)
        from copy import deepcopy

        from app import team_setting_template

        default_config = deepcopy(team_setting_template)
        cfg._update_config(default_config, data)

        cfg.set_value(f"team{self.team_number}_setting", default_config)
        bar = BaseInfoBar.success(
            title=QT_TRANSLATE_NOOP("BaseInfoBar", "已粘贴设置"),
            content="",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=500,
            parent=self.parent().parent(),
        )

    def remark_name_changed(self, text):
        cfg.set_value(f"team{self.team_number}_remark_name", text)

    def edit_button_clicked(self):
        name = cfg.get_value(f"team{self.team_number}_remark_name")
        if name is None:
            name = ""
        message_box = MessageBoxEdit(
            QT_TRANSLATE_NOOP("MessageBoxEdit", "设置备注名"), name, self.window()
        )
        self.retranslateTempUi(message_box)
        if message_box.exec():
            new_name = str(message_box.getText())
            cfg.set_value(f"team{self.team_number}_remark_name", new_name)
            self.remark_name.setText(new_name)

    def delete_button_clicked(self):
        if len(team_toggle_button_group) > 1:
            team_toggle_button_group.remove(self.button.button)
            mediator.delete_team_setting.emit(f"team_{self.team_number}")

    def refresh_remark_name(self):
        name = cfg.get_value(f"team{self.team_number}_remark_name")
        if name is not None:
            self.remark_name.setText(name)

    def retranslateUi(self):
        self.remark_name.setPlaceholderText(self.tr("备注名"))
        self.button.retranslateUi()
        if self.team_number == 1:
            self.box.check_box.setText(self.tr(self.box_text))
        elif self.team_number <= 9:
            text = self.box_text[:-1]
            box_text = f"{self.tr(text)}{self.team_number}"
            self.box.check_box.setText(box_text)
        else:
            text = self.box_text[:-2]
            box_text = f"{self.tr(text)}{self.team_number}"
            self.box.check_box.setText(box_text)

    def retranslateTempUi(self, message_box: MessageBoxEdit):
        message_box.retranslateUi()


class SinnerSelect(QFrame):
    def __init__(
        self,
        config_name,
        label_title,
        check_box_icon: Union[str, QIcon, FluentIconBase, None],
        sinner_img,
        crop_left=13,
        crop_right=13,
        crop_top=93,
        crop_bottom=90,
        parent=None,
    ):
        super().__init__(parent)
        self.setObjectName(config_name)
        self.vBoxLayout = QVBoxLayout(self)
        self.vBoxLayout.setContentsMargins(5, 5, 5, 5)
        self.vBoxLayout.setSpacing(5)

        # Image Label
        self.label_pic = BodyLabel()
        self.label_pic.setAlignment(Qt.AlignCenter)
        # self.label_pic.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Name Label
        self.label_str = BodyLabel(label_title)
        self.label_str.setAlignment(Qt.AlignCenter)

        # Load and set image
        pixmap = QPixmap(sinner_img)
        if crop_left or crop_right or crop_top or crop_bottom:
            rect = QRect(
                crop_left,
                crop_top,
                pixmap.width() - crop_left - crop_right,
                pixmap.height() - crop_top - crop_bottom,
            )
            pixmap = pixmap.copy(rect)

        # Manual scaling to fit the label area (approx 100x120) while keeping aspect ratio
        pixmap = pixmap.scaled(92, 96, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.label_pic.setPixmap(pixmap)

        # Opacity Effect for Image
        self.opacity_effect = QGraphicsOpacityEffect(self.label_pic)
        self.opacity_effect.setOpacity(1.0)
        self.label_pic.setGraphicsEffect(self.opacity_effect)

        self.vBoxLayout.addWidget(self.label_pic, stretch=5)
        self.vBoxLayout.addWidget(self.label_str, stretch=1)

        # Internal CheckBox (Hidden, for logic reuse)
        self.box = BaseCheckBox(config_name, check_box_icon, "", parent=self)
        self.box.setVisible(False)
        self.box.check_box.toggled.connect(self._on_internal_toggle)

        # Overlay Widget (Container for number and SELECTED label)
        self.overlay_widget = QWidget(self)
        self.overlay_widget.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.overlay_layout = QVBoxLayout(self.overlay_widget)
        self.overlay_layout.setAlignment(Qt.AlignCenter)
        self.overlay_layout.setSpacing(5)  # Space between number and SELECTED text

        # Number Label
        self.number_label = QLabel()  # Parent handled by layout
        self.number_label.setAlignment(Qt.AlignCenter)

        font = self.number_label.font()
        font.setPointSize(30)
        font.setBold(True)
        self.number_label.setFont(font)
        self.number_label.setStyleSheet(
            "color: rgba(255, 255, 0, 1);"
        )  # Number color: Yellow

        # SELECTED Label
        self.selected_label = QLabel()  # Initialization, content/style set in set_text
        self.selected_label.setAlignment(Qt.AlignCenter)

        self.overlay_layout.addWidget(self.number_label)
        self.overlay_layout.addWidget(self.selected_label)

        self.overlay_widget.hide()

        # Fixed Size
        self.setFixedSize(110, 145)  # Fixed size: 110x145

        # Initial Style
        self._update_style(self.box.check_box.isChecked())

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.box.check_box.toggle()

    def _on_internal_toggle(self, checked):
        self._update_style(checked)

    def _update_style(self, checked):
        if checked:
            self.opacity_effect.setOpacity(0.5)  # 选中时不透明度设为0.5（变暗50%）
            self.setStyleSheet(
                """
                SinnerSelect {
                    background-color: rgba(126.5, 126.5, 126.5, 1); /* 背景色黑，叠加50%透明度图片 -> 图片亮度减半 */
                    border: 3px solid #FFD700; /* 选中态边框：3px实线，金色 */
                    border-radius: 8px; /* 圆角半径：8px */
                }
            """
            )
        else:
            self.opacity_effect.setOpacity(1.0)  # 未选中时恢复图片不透明度
            self.setStyleSheet(
                """
                SinnerSelect {
                    border: 2px solid rgba(128, 128, 128, 0.4);  /* 未选中态边框：2px实线，淡灰色 */
                    border-radius: 8px;                          /* 圆角半径：8px */
                    background-color: transparent;               /* 未选中态背景：透明 */
                }
                SinnerSelect:hover {
                    border: 4px solid #778899;                   /* 悬停态边框：4px实线，蓝灰色 */
                    background-color: rgba(255, 255, 255, 0.1);  /* 悬停态背景：白色微透明 */
                }
            """
            )

    def set_text(self, text):
        self.number_label.setText(text)
        if text and text != "0":
            # Determine label style based on number
            try:
                number = int(text)
                if number >= 8:
                    self.selected_label.setText("BACK UP")
                    self.selected_label.setStyleSheet(
                        """
                        background-color: rgba(179, 229, 252, 1); /* Light Blue background */
                        color: rgba(1, 87, 155, 1);               /* Dark Blue text */
                        font-weight: bold;
                        padding: 2px 4px;
                        border-radius: 4px;
                    """
                    )
                else:
                    self.selected_label.setText("SELECTED")
                    self.selected_label.setStyleSheet(
                        """
                        background-color: rgba(211, 47, 47, 1); /* Red background */
                        color: rgba(255, 255, 0, 1);            /* Yellow text */
                        font-weight: bold;
                        padding: 2px 4px;
                        border-radius: 4px;
                    """
                    )
            except ValueError:
                # Fallback if text is not a number
                self.selected_label.setText("SELECTED")
                self.selected_label.setStyleSheet(
                    """
                    background-color: rgba(211, 47, 47, 1); 
                    color: rgba(255, 255, 0, 1);            
                    font-weight: bold;
                    padding: 2px 4px;
                    border-radius: 4px;
                """
                )

            self.overlay_widget.show()
        else:
            self.overlay_widget.hide()

    def set_checkbox(self, checked):
        self.box.set_checked(checked)

    def resizeEvent(self, event):
        self.overlay_widget.setGeometry(self.rect())
        super().resizeEvent(event)


class ComboBoxSettingCard(SettingCard):
    valueChanged = Signal()

    def __init__(
        self,
        config_name: str,
        icon: Union[str, QIcon, FluentIconBase],
        title,
        content=None,
        texts=None,
        parent=None,
    ):
        super().__init__(icon, title, content, parent)
        self.config_name = config_name

        self.title = title
        self.content = content
        self.texts = texts

        self.comboBox = ComboBox(self)
        self.hBoxLayout.addWidget(self.comboBox, 0, Qt.AlignRight)
        self.hBoxLayout.addSpacing(16)

        for key, value in texts.items():
            self.comboBox.addItem(key, userData=value)
            if value == cfg.get_value(config_name):
                self.comboBox.setCurrentText(key)

        self.comboBox.currentIndexChanged.connect(self._onCurrentIndexChanged)
        self.comboBox.currentIndexChanged.connect(self.valueChanged)

    def _onCurrentIndexChanged(self, index: int):
        cfg.set_value(self.config_name, self.comboBox.itemData(index))
        if self.config_name == "language_in_program":
            LanguageManager().set_language(self.comboBox.itemData(index))

    def retranslateUi(self):
        self.setTitle(self.tr(self.title))
        self.setContent(self.tr(self.content))
        if self.texts:
            index = 0
            for key in self.texts:
                self.comboBox.setItemText(index, self.tr(key))
                index += 1


class BaseSettingCardGroup(SettingCardGroup):
    def __init__(self, title: str, parent=None):
        super().__init__(title, parent)
        self.text = title

    def retranslateUi(self):
        self.titleLabel.setText(self.tr(self.text))


class BasePushSettingCard(PushSettingCard):
    def __init__(
        self, text, icon: str | QIcon | FluentIconBase, title, content=None, parent=None
    ):
        super().__init__(text, icon, title, content, parent)
        self.text = text
        self.title = title
        self.content = content

    def retranslateUi(self):
        self.titleLabel.setText(self.tr(self.title))
        self.contentLabel.setText(self.tr(self.content))
        self.button.setText(self.tr(self.text))


class BasePrimaryPushSettingCard(PrimaryPushSettingCard):
    def __init__(self, text, icon, title, content=None, parent=None):
        super().__init__(text, icon, title, content, parent)
        self.text = text
        self.title = title
        self.content = content

    def retranslateUi(self):
        self.titleLabel.setText(self.tr(self.title))
        self.contentLabel.setText(self.tr(self.content))
        self.button.setText(self.tr(self.text))


class PushSettingCardMirrorchyan(SettingCard):
    def __init__(
        self,
        text,
        icon: Union[str, QIcon, FluentIconBase],
        title,
        update_callback,
        config_name,
        parent: QObject | None = None,
    ):
        self.config_value = decrypt_string(str(cfg.get_value(config_name)))
        self.update_callback = update_callback
        super().__init__(icon, title, "", parent)

        self.title = title
        self.button_text = text
        self.config_name = config_name

        self.button2 = QPushButton("获取 CDK", self)
        self.button2.setObjectName("primaryButton")
        self.hBoxLayout.addWidget(self.button2, 0, Qt.AlignRight)
        self.hBoxLayout.addSpacing(10)
        self.button2.clicked.connect(self.__onclicked2)

        self.button = QPushButton(text, self)
        self.hBoxLayout.addWidget(self.button, 0, Qt.AlignRight)
        self.hBoxLayout.addSpacing(16)
        self.button.clicked.connect(self.__onclicked)

    def __onclicked(self):
        message_box = MessageBoxEdit(
            self.tr(self.title), self.config_value, self.window()
        )
        if message_box.exec():
            base64_cdk = encrypt_string(message_box.getText())
            cfg.set_value(self.config_name, base64_cdk)
            self.contentLabel.setText(message_box.getText())
            self.config_value = message_box.getText()
            parent = self._find_parent(self)
            check_update(parent, flag=True)

    def __onclicked2(self):
        QDesktopServices.openUrl(QUrl("https://mirrorchyan.com/?source=aalc_app"))

    def _find_parent(self, widget):
        while widget.parent() is not None:
            widget = widget.parent()
        return widget

    def retranslateUi(self):
        self.button2.setText(self.tr("获取 CDK"))
        self.titleLabel.setText(self.tr(self.title))
        self.button.setText(self.tr(self.button_text))


class SwitchSettingCard(SettingCard):
    """Setting card with switch button"""

    checkedChanged = Signal(bool)

    def __init__(
        self,
        icon: Union[str, QIcon, FluentIconBase],
        title,
        content=None,
        config_name: str = None,
        parent=None,
    ):
        super().__init__(icon, title, content, parent)
        self.config_name = config_name
        self.switchButton = SwitchButton(self.tr("关"), self, IndicatorPosition.RIGHT)

        self.setValue(cfg.get_value(self.config_name))

        self.title = title
        self.content = content

        # add switch button to layout
        self.hBoxLayout.addWidget(self.switchButton, 0, Qt.AlignRight)
        self.hBoxLayout.addSpacing(16)

        self.switchButton.checkedChanged.connect(self.__onCheckedChanged)

    def __onCheckedChanged(self, isChecked: bool):
        """switch button checked state changed slot"""
        self.setValue(isChecked)
        cfg.set_value(self.config_name, isChecked)

    def setValue(self, isChecked: bool):
        self.switchButton.setChecked(isChecked)
        self.switchButton.setText(self.tr("开") if isChecked else self.tr("关"))

    def retranslateUi(self):
        self.switchButton.setText(
            self.tr("开") if self.switchButton.checked else self.tr("关")
        )
        self.titleLabel.setText(self.tr(self.title))
        self.contentLabel.setText(self.tr(self.content))


class PushSettingCardDate(BasePushSettingCard):
    # clicked = pyqtSignal()
    def __init__(
        self,
        text,
        icon: Union[str, QIcon, FluentIconBase],
        title,
        config_name,
        parent=None,
    ):
        self.config_name = config_name
        self.config_value = datetime.datetime.fromtimestamp(cfg.get_value(config_name))
        super().__init__(
            text, icon, title, self.config_value.strftime("%Y-%m-%d %H:%M"), parent
        )
        self.button.clicked.connect(self.__onclicked)

    def __onclicked(self):
        message_box = MessageBoxDate(
            self.tr(self.title), self.config_value, self.window()
        )
        if message_box.exec():
            self.config_value = message_box.getDateTime()
            get_timezone()
            cfg.set_value(self.config_name, self.config_value.timestamp())
            self.contentLabel.setText(self.config_value.strftime("%Y-%m-%d %H:%M"))


class PushSettingCardChance(BasePushSettingCard):
    def __init__(
        self,
        text,
        icon: Union[str, QIcon, FluentIconBase],
        title,
        max_value=3,
        content=None,
        config_name: str = None,
        parent=None,
    ):
        super().__init__(text, icon, title, content, parent)
        self.config_name = config_name
        self.max_value = max_value
        self.line_text = LineEdit()
        self.line_text.setAlignment(Qt.AlignCenter)
        self.line_text.setReadOnly(True)
        self.line_text.setMaximumWidth(100)
        self.line_text.setText(str(cfg.get_value(self.config_name)))
        current_count = self.hBoxLayout.count()
        self.hBoxLayout.insertWidget(current_count - 2, self.line_text)
        self.button.clicked.connect(self.__onclicked)

    def __onclicked(self):
        message_box = MessageBoxSpinbox(
            self.tr(self.title), self.window(), self.max_value
        )
        if message_box.exec():
            cfg.set_value(f"{self.config_name}", int(message_box.getValue()))
            self.line_text.setText(str(message_box.getValue()))


class DailySettingCard(SwitchSettingCard):
    def __init__(
        self,
        icon: Union[str, QIcon, FluentIconBase],
        title,
        content=None,
        config_name: str = None,
        parent=None,
    ):
        super().__init__(icon, title, content, config_name, parent)
        self.config_name = config_name
        self.autodaily_timepicker = TimePicker()
        autodaily_time = cfg.get_value("autodaily_time") or "00:00"
        autodaily_qtime = QTime.fromString(autodaily_time, "HH:mm")
        if not autodaily_qtime.isValid():
            autodaily_qtime = QTime(0, 0)
        self.autodaily_timepicker.setTime(autodaily_qtime)
        current_count = self.hBoxLayout.count()
        self.hBoxLayout.insertWidget(current_count - 2, self.autodaily_timepicker)
        self.hBoxLayout.insertSpacing(current_count - 1, 20)
        self.autodaily_timepicker.setDisabled(not self.switchButton.isChecked())
        self.autodaily_timepicker.timeChanged.connect(
            self.__onAutoDailyTimepickerChanged
        )

    def __connect_signal(self):
        self.switchButton.checkedChanged.connect(self.__onAutoDailyCheckboxChanged)
        self.autodaily_timepicker.timeChanged.connect(
            self.__onAutoDailyTimepickerChanged
        )

    @staticmethod
    def __autodaily_taskname() -> str:
        return "AALC Daily Task"

    def __onAutoDailyCheckboxChanged(self, isChecked):
        from utils.schedule_helper import ScheduleHelper

        helper = ScheduleHelper()
        task_name = self.__autodaily_taskname()

        cfg.set_value(self.config_name, isChecked)
        if isChecked:
            self.autodaily_timepicker.setDisabled(False)
            time = self.autodaily_timepicker.getTime()
            helper.register_daily_task(
                task_name, "start --exit", time.hour(), time.minute()
            )
        else:
            self.autodaily_timepicker.setDisabled(True)
            helper.unregister_task(task_name)

    def __onAutoDailyTimepickerChanged(self, time: QTime):
        from utils.schedule_helper import ScheduleHelper

        helper = ScheduleHelper()
        task_name = self.__autodaily_taskname()

        cfg.set_value("autodaily_time", time.toString("HH:mm"))
        helper.unregister_task(task_name)
        helper.register_daily_task(
            task_name, "start --exit", time.hour(), time.minute()
        )


class HotkeySettingCard(BasePushSettingCard):
    def __init__(
        self,
        text,
        icon: str | QIcon | FluentIconBase,
        title,
        hotkeys: dict[str, str],
        parent=None,
    ):
        super().__init__(text, icon, title, "", parent)
        self.button.clicked.connect(self.__on_clicked)
        self.hotkeys = hotkeys

    def __on_clicked(self):
        message_box = HotkeyEditCard(self.tr(self.title), self.hotkeys, self.window())
        message_box.exec()

    def retranslateUi(self):
        super().retranslateUi()
        new_keys = {}
        for key in self.hotkeys:
            tr_key = self.tr(key)
            new_keys[tr_key] = self.hotkeys[key]
        self.hotkeys = new_keys


class KeyButton(PrimaryPushButton):
    def __init__(self, key_name: str, parent=None):
        super().__init__(parent=parent)
        self.key_name = key_name
        self.setText(key_name)
        self.setFocusPolicy(Qt.NoFocus)

    def mousePressEvent(self, e):
        e.ignore()
        self.parent().mousePressEvent(e)

    def mouseReleaseEvent(self, e):
        e.ignore()
        self.parent().mouseReleaseEvent(e)


class KeyEditButton(PushButton):
    kill_key_input = Signal()

    def __init__(self, key_config: str, parent=None):
        super().__init__(parent)
        self.key_config = key_config
        self.key_name: str = cfg.get_value(key_config)
        self.hBoxLayout = QHBoxLayout(self)
        self.hBoxLayout.setAlignment(Qt.AlignCenter)
        self._create_key_button()

        self.hBoxLayout.addStretch(1)
        self.editIcon = BodyLabel()
        self.editIcon.setPixmap(FIF.EDIT.icon().pixmap(16, 16))

        self.hBoxLayout.addWidget(self.editIcon)

        self.setFixedHeight(50)
        self.setMinimumWidth(self.calculate_minimum_width())

        self.clicked.connect(self.__on_clicked)

    def calculate_minimum_width(self):
        # 计算所有子控件的大致宽度
        icon_width = self.editIcon.pixmap().size().width()  # 编辑图标宽度
        margins = self.hBoxLayout.contentsMargins()
        margins_width = margins.left() + margins.right()

        # 估算每个按键按钮的宽度（根据文本长度）
        key_widths = 0
        for key in self.key_name.replace("<", "").replace(">", "").split("+"):
            key_widths += len(key) * 8 + 20  # 粗略估算

        return icon_width + key_widths + margins_width + 20  # 额外留些边距

    def _create_key_button(self):
        key_name = self.key_name
        keys = key_name.replace("<", "").replace(">", "").split("+")
        index = 0
        for key in keys:
            key = key.capitalize()
            key_button = KeyButton(key, self)
            self.kill_key_input.connect(key_button.deleteLater)
            self.hBoxLayout.insertWidget(index, key_button)
            index += 1

    def __on_clicked(self):
        input_card = HotketInputCard(
            self.tr("设置快捷键"), self.key_config, self.window()
        )
        mediator.hotkey_listener_stop_signal.emit()
        if input_card.exec():
            self.key_name = cfg.get_value(self.key_config)
            self.kill_key_input.emit()
            self._create_key_button()
            self.setMinimumWidth(self.calculate_minimum_width())
            mediator.hotkey_listener_start_signal.emit()
        else:
            mediator.hotkey_listener_start_signal.emit()


class KeyItem(QFrame):
    kill_key_item = Signal(object)

    def __init__(self, key_config: str, content: str, parent=None):
        super().__init__(parent)
        self.key_name = key_config
        self.content = content
        self.hBoxLayout = QHBoxLayout(self)
        self.hBoxLayout.setAlignment(Qt.AlignCenter)
        self.hBoxLayout.setContentsMargins(0, 0, 0, 0)

        self.label = BodyLabel(content)
        self.hBoxLayout.addWidget(self.label)
        self.hBoxLayout.addStretch(1)
        self.button = KeyEditButton(key_config, self)
        self.hBoxLayout.addWidget(self.button)


class HotkeyEditCard(MessageBox):
    def __init__(self, title: str, hotkeys: dict[str, str], parent=None):
        super().__init__(title, "", parent)
        self.yesButton.setText(self.tr("返回"))
        self.textLayout.removeWidget(self.contentLabel)
        self.contentLabel.deleteLater()
        self.cancelButton.setParent(None)
        self.cancelButton.deleteLater()

        for key in hotkeys:
            item = KeyItem(hotkeys[key], key, self)
            item.setFixedWidth(420)
            self.textLayout.addWidget(item)


class HotketInputCard(MessageBox):
    kill_key_input = Signal()

    SHIFT_KEYS = {
        "!": "1",
        "@": "2",
        "#": "3",
        "$": "4",
        "%": "5",
        "^": "6",
        "&": "7",
        "*": "8",
        "(": "9",
        ")": "0",
        "_": "-",
        "+": "=",
        "{": "[",
        "}": "]",
        "|": "\\",
        ":": ";",
        '"': "'",
        "<": ",",
        ">": ".",
        "?": "/",
        "~": "`",
    }

    def __init__(self, title: str, key_config: str, parent=None):
        super().__init__(title, "", parent)
        self.key_config = key_config
        self.key_name: str = cfg.get_value(key_config)
        self.yesButton.setText(self.tr("保存"))
        self.resetButton = PushButton(self.tr("重置"))
        self.buttonLayout.insertWidget(1, self.resetButton, 1, Qt.AlignVCenter)
        self.cancelButton.setText(self.tr("取消"))
        self.contentLabel.setText(
            self.tr("按下键盘以设置快捷键, 部分特殊按键可能无法使用")
        )

        self.key_widget = QWidget()
        self.key_widget.setFixedSize(400, 200)
        self.key_layout = QHBoxLayout(self.key_widget)
        self.key_layout.setAlignment(Qt.AlignCenter)

        self.textLayout.addWidget(self.key_widget)

        self._create_key_display(self.key_name)
        self.yesButton.clicked.connect(self._save_config)
        self.resetButton.clicked.connect(self._reset_config)

    def _reset_config(self):
        default_config = cfg._load_default_config().get(self.key_config, "")
        self.key_name = default_config
        self.fresh_key_display(default_config)

    def _save_config(self):
        cfg.set_value(self.key_config, self.key_name)

    def _create_key_display(self, key_name: str):
        keys = self._parse_key_name(key_name)
        for key in keys:
            try:
                key = key.capitalize()
                key_button = KeyButton(key, self)
                qss = """
                KeyButton {font-size: 24px;}
                """
                setCustomStyleSheet(key_button, qss, qss)
                self.kill_key_input.connect(key_button.deleteLater)
                self.key_layout.addWidget(key_button)
            except Exception as e:
                log.error(f"Error creating key button for '{key}': {e}")

    def _parse_key_name(self, key_name: str) -> list[str]:
        self.key_name = key_name
        keys = key_name.split("+")
        for index, key in enumerate(keys):
            if len(key) > 2:
                keys[index] = key.replace("<", "").replace(">", "")
        return keys

    def fresh_key_display(self, key_name: str):
        if key_name:
            self.kill_key_input.emit()
            self._create_key_display(key_name)

    def _parse_input_key(self, arg__1: QKeyEvent) -> str:
        key = arg__1.key()
        modifiers = arg__1.modifiers()
        key_parts = []

        if modifiers & Qt.ControlModifier:
            key_parts.append("<ctrl>")
        if modifiers & Qt.AltModifier:
            key_parts.append("<alt>")
        if modifiers & Qt.ShiftModifier:
            key_parts.append("<shift>")

        key_name = QKeySequence(key).toString().lower()
        if key_name in self.SHIFT_KEYS:
            key_name = self.SHIFT_KEYS[key_name]
        if key_name and key_name not in [
            "control",
            "alt",
            "shift",
            "meta",
            "del",
            "ins",
            "pgup",
            "pgdown",
            "capslock",
        ]:
            if len(key_name) > 1:
                key_parts.append(f"<{key_name.lower()}>")
            else:
                key_parts.append(key_name.lower())

        key_name = "+".join(key_parts)
        return key_name

    def keyPressEvent(self, arg__1: QKeyEvent) -> None:
        self.fresh_key_display(self._parse_input_key(arg__1))
        arg__1.ignore()


class TextProgressBar(ProgressBar):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTextVisible(True)
        if parent:
            self.setObjectName(f"{parent.objectName()}::TextProgressBar")
        else:
            self.setObjectName("TextProgressBar")
        self._text_color = QColor(0, 0, 0)
        self.specialValue = 0

    def setTextColor(self, color):
        """设置文本颜色"""
        self._text_color = QColor(color)
        self.update()

    def paintEvent(self, e):
        painter = QPainter(self)
        painter.setRenderHints(QPainter.Antialiasing)

        painter.setPen(QColor(114, 114, 114, int(255 / 2)))

        r = self.height() / 2
        w = int(self.val / (self.maximum() - self.minimum()) * self.width())

        # 绘制边框
        painter.drawRoundedRect(0, 0, self.width(), self.height(), r + 2, r + 2)

        painter.setPen(Qt.NoPen)

        bc = QColor(255, 255, 255, int(255 / 2))
        painter.setBrush(bc)

        # 绘制背景
        painter.drawRoundedRect(0, 0, self.width(), self.height(), r + 2, r + 2)

        if self.minimum() >= self.maximum():
            return

        # draw bar
        painter.setPen(Qt.NoPen)
        painter.setBrush(self.barColor())

        painter.drawRoundedRect(0, 0, w, self.height(), r, r)
        # 然后绘制文本
        if self.isTextVisible():
            painter.setPen(self._text_color)
            painter.setFont(self.font())

            # 使用格式化文本
            text = (
                self.format()
                .replace("%p", str(self.percentage()))
                .replace("%v", str(self.value()))
                .replace("%m", str(self.maximum()))
                .replace("%raw", str(self.specialValue))
            )

            # 添加字体描边效果

            painter.setPen(QColor(255, 255, 255, 155))
            offsets = [
                (-1, -1),
                (-1, 0),
                (-1, 1),
                (0, -1),
                (0, 1),
                (1, -1),
                (1, 0),
                (1, 1),
            ]

            for dx, dy in offsets:
                rect = self.rect().translated(dx, dy)
                painter.drawText(rect, Qt.AlignCenter, text)

            # 绘制主体文本
            painter.setPen(self._text_color)
            painter.drawText(self.rect(), Qt.AlignCenter, text)

    def percentage(self):
        """计算百分比"""
        if self.maximum() <= self.minimum():
            return 100
        return int(
            (self.value() - self.minimum()) * 100 / (self.maximum() - self.minimum())
        )

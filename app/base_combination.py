import base64
import datetime

import pyperclip
from PyQt5.QtCore import QUrl
from PyQt5.QtGui import QPixmap, QDesktopServices
from PyQt5.QtWidgets import QPushButton
from qfluentwidgets import LineEdit, SettingCard, \
    IndicatorPosition, SwitchButton, SettingCardGroup, \
    PushSettingCard, PrimaryPushSettingCard, InfoBarPosition

from app.base_tools import *
from app.card.messagebox_custom import MessageBoxEdit, MessageBoxDate, \
    MessageBoxSpinbox, BaseInfoBar
from app.language_manager import LanguageManager
from module.my_error.my_error import settingsTypeError
from module.update.check_update import check_update
from utils.utils import encrypt_string, decrypt_string, get_timezone


class CheckBoxWithButton(QFrame):
    def __init__(self, check_box_name, check_box_title, check_box_icon: Union[str, QIcon, FluentIconBase, None],
                 button_name, parent=None):
        super().__init__(parent)
        # self.setFixedHeight(80)

        self.hBoxLayout = QHBoxLayout(self)
        self.box_text = check_box_title
        self.box = BaseCheckBox(check_box_name, check_box_icon, check_box_title, parent=self)
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
    def __init__(self, check_box_name, check_box_title, check_box_icon: Union[str, QIcon, FluentIconBase, None],
                 combo_box_name, combo_box_width=None, parent=None):
        super().__init__(parent)
        # self.setFixedHeight(80)
        self.additional_combo_box = None
        self.hBoxLayout = QHBoxLayout(self)
        self.box_text = check_box_title
        self.box = BaseCheckBox(check_box_name, check_box_icon, check_box_title, parent=self, center=False)
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
            self.layout = QVBoxLayout(self)
        else:
            self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.label = BaseLabel(label_text)
        self.combo_box = BaseComboBox(config_name)
        self.combo_box.add_items(items)
        self.layout.addWidget(self.label)
        if vbox is not True:
            self.layout.addSpacing(10)
        self.layout.addWidget(self.combo_box, Qt.AlignLeft)
        self.layout.setAlignment(Qt.AlignCenter)
        self.setMaximumHeight(80)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)

    def add_items(self, items):
        self.combo_box.add_items(items)

    def retranslateUi(self):
        self.label.label.setText(self.tr(self.text))
        self.combo_box.retranslateUi()


class LabelWithSpinBox(QFrame):
    def __init__(self, label_text, box_name, parent=None, double=False, min_value=0.1, min_step=0.01):
        super().__init__(parent)
        self.vbox_layout = QVBoxLayout(self)
        self.text = label_text
        self.label = BaseLabel(label_text)
        self.box = BaseSpinBox(box_name, double=double, min_value=min_value, min_step=min_step)
        self.vbox_layout.addWidget(self.label)
        self.vbox_layout.addWidget(self.box)
        self.vbox_layout.setAlignment(Qt.AlignCenter)
        self.setMaximumHeight(100)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)

    def retranslateUi(self):
        self.label.label.setText(self.tr(self.text))


class MirrorSpinBox(QFrame):
    def __init__(self, label_text, box_name, double=False, min_value=0, min_step=1):
        super().__init__()
        self.box_layout = QHBoxLayout(self)
        self.text = label_text
        self.label = BaseLabel(label_text)
        self.box = BaseSpinBox(box_name, double=double, min_value=min_value, min_step=min_step)
        self.box_layout.addWidget(self.label, stretch=1)
        self.box_layout.addWidget(self.box, stretch=2)
        self.setMaximumHeight(70)

    def retranslateUi(self):
        self.label.label.setText(self.tr(self.text))


class MirrorTeamCombination(QFrame):
    def __init__(self, team_number, check_box_name, check_box_title,
                 check_box_icon: Union[str, QIcon, FluentIconBase, None],
                 button_name, parent=None):
        super().__init__(parent)
        self.setObjectName(f"team_{team_number}")

        self.box_text = check_box_title

        self.hBoxLayout = QHBoxLayout(self)
        self.box = BaseCheckBox(check_box_name, check_box_icon, check_box_title, parent=self)
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
        setting = base64.b64encode(setting.encode('utf-8')).decode('utf-8')
        pyperclip.copy(setting)
        bar = BaseInfoBar.success(
            title=QT_TRANSLATE_NOOP("BaseInfoBar", '已复制到剪切板'),
            content='',
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=500,
            parent=self.parent().parent()
        )

    def paste_team_settings(self):
        setting = pyperclip.paste().strip()
        try:
            setting = base64.b64decode(setting).decode('utf-8')
            if "||AALC_TEAM_SETTING||" not in setting:
                raise settingsTypeError("不是有效的AALC设置")
            setting = setting.replace("||AALC_TEAM_SETTING||", "", 1)
        except settingsTypeError:
            bar = BaseInfoBar.error(
                title=QT_TRANSLATE_NOOP("BaseInfoBar", '该设置不属于 AALC'),
                content='',
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=500,
                parent=self.parent().parent()
            )
            return
        except Exception:
            bar = BaseInfoBar.error(
                title=QT_TRANSLATE_NOOP("BaseInfoBar", '不是有效的 AALC 设置'),
                content='',
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=500,
                parent=self.parent().parent()
            )
            return

        data = cfg.yaml.load(setting)

        cfg.set_value(f"team{self.team_number}_setting", data)
        bar = BaseInfoBar.success(
            title=QT_TRANSLATE_NOOP("BaseInfoBar", '已粘贴设置'),
            content='',
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=500,
            parent=self.parent().parent()
        )

    def remark_name_changed(self, text):
        cfg.set_value(f"team{self.team_number}_remark_name", text)

    def edit_button_clicked(self):
        name = cfg.get_value(f"team{self.team_number}_remark_name")
        if name is None:
            name = ""
        message_box = MessageBoxEdit(
            QT_TRANSLATE_NOOP("MessageBoxEdit", "设置备注名"),
            name, self.window()
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
    def __init__(self, config_name, label_title, check_box_icon: Union[str, QIcon, FluentIconBase, None], sinner_img,
                 parent=None):
        super().__init__(parent)
        self.setObjectName(config_name)
        # self.setFixedHeight(300)
        self.vBoxLayout = QVBoxLayout(self)
        self.hBoxLayout_up = QHBoxLayout(self)
        self.hBoxLayout_down = QHBoxLayout(self)
        self.box = BaseCheckBox(config_name, check_box_icon, '', parent=self)
        self.line_edit = LineEdit()
        self.line_edit.setAlignment(Qt.AlignCenter)
        self.line_edit.setReadOnly(True)
        self.setMaximumHeight(140)
        self.vBoxLayout.setContentsMargins(5, 0, 0, 0)

        self.setStyleSheet("""
                    SinnerSelect {
                        border: 2px solid #DCDCDC;  /* 边框颜色 */
                        border-radius: 5px;         /* 圆角 */
                        padding: 10px;              /* 内边距 */
                    }
                    SinnerSelect:hover {
                        border-color: #778899;  /* 悬停时边框突出显示 */
                    }
                """)

        # 图片标签配置
        self.label_pic = BodyLabel()
        self.label_pic.setFixedHeight(50)
        self.label_pic.setScaledContents(True)  # 关键修改：允许缩放
        self.label_str = BodyLabel(label_title)

        # 加载并缩放图片
        pixmap = QPixmap(sinner_img)
        scaled_pixmap = pixmap.scaled(
            50, 50,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        self.label_pic.setPixmap(scaled_pixmap)
        self.label_pic.setSizePolicy(
            QSizePolicy.Fixed,  # 水平固定为 50px
            QSizePolicy.Expanding  # 垂直填充剩余空间
        )

        # 调整布局分配比例

        self.hBoxLayout_up.addWidget(self.label_str)
        self.hBoxLayout_up.addWidget(self.label_pic)

        self.hBoxLayout_down.addWidget(self.box, alignment=Qt.AlignCenter)
        self.hBoxLayout_down.addWidget(self.line_edit)

        self.vBoxLayout.addLayout(self.hBoxLayout_up)
        self.vBoxLayout.addLayout(self.hBoxLayout_down)

    def set_text(self, text):
        self.line_edit.setText(text)

    def set_checkbox(self, checked):
        self.box.set_checked(checked)


class ComboBoxSettingCard(SettingCard):
    valueChanged = pyqtSignal()

    def __init__(self, config_name: str, icon: Union[str, QIcon, FluentIconBase], title, content=None, texts=None,
                 parent=None):
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
    def __init__(self, text, icon: str | QIcon | FluentIconBase, title, content=None, parent=None):
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
    def __init__(self, text, icon: Union[str, QIcon, FluentIconBase], title, update_callback, config_name, parent=None):
        self.config_value = decrypt_string(str(cfg.get_value(config_name)))
        self.update_callback = update_callback
        super().__init__(icon, title, "", parent)

        self.title = title
        self.button_text = text
        self.config_name = config_name

        self.button2 = QPushButton("获取 CDK", self)
        self.button2.setObjectName('primaryButton')
        self.hBoxLayout.addWidget(self.button2, 0, Qt.AlignRight)
        self.hBoxLayout.addSpacing(10)
        self.button2.clicked.connect(self.__onclicked2)

        self.button = QPushButton(text, self)
        self.hBoxLayout.addWidget(self.button, 0, Qt.AlignRight)
        self.hBoxLayout.addSpacing(16)
        self.button.clicked.connect(self.__onclicked)

    def __onclicked(self):
        message_box = MessageBoxEdit(self.tr(self.title), self.config_value, self.window())
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
    """ Setting card with switch button """

    checkedChanged = pyqtSignal(bool)

    def __init__(self, icon: Union[str, QIcon, FluentIconBase], title, content=None, config_name: str = None,
                 parent=None):
        super().__init__(icon, title, content, parent)
        self.config_name = config_name
        self.switchButton = SwitchButton(
            self.tr('关'), self, IndicatorPosition.RIGHT
        )

        self.setValue(cfg.get_value(self.config_name))

        self.title = title
        self.content = content

        # add switch button to layout
        self.hBoxLayout.addWidget(self.switchButton, 0, Qt.AlignRight)
        self.hBoxLayout.addSpacing(16)

        self.switchButton.checkedChanged.connect(self.__onCheckedChanged)

    def __onCheckedChanged(self, isChecked: bool):
        """ switch button checked state changed slot """
        self.setValue(isChecked)
        cfg.set_value(self.config_name, isChecked)

    def setValue(self, isChecked: bool):
        self.switchButton.setChecked(isChecked)
        self.switchButton.setText(self.tr('开') if isChecked else self.tr('关'))

    def retranslateUi(self):
        self.switchButton.setText(self.tr('开') if self.switchButton.checked else self.tr('关'))
        self.titleLabel.setText(self.tr(self.title))
        self.contentLabel.setText(self.tr(self.content))


class PushSettingCardDate(BasePushSettingCard):
    # clicked = pyqtSignal()
    def __init__(self, text, icon: Union[str, QIcon, FluentIconBase], title, config_name, parent=None):
        self.config_name = config_name
        self.config_value = datetime.datetime.fromtimestamp(cfg.get_value(config_name))
        super().__init__(text, icon, title, self.config_value.strftime('%Y-%m-%d %H:%M'), parent)
        self.button.clicked.connect(self.__onclicked)

    def __onclicked(self):
        message_box = MessageBoxDate(self.tr(self.title), self.config_value, self.window())
        if message_box.exec():
            self.config_value = message_box.getDateTime()
            get_timezone()
            cfg.set_value(self.config_name, self.config_value.timestamp())
            self.contentLabel.setText(self.config_value.strftime('%Y-%m-%d %H:%M'))


class PushSettingCardChance(BasePushSettingCard):

    def __init__(self, text, icon: Union[str, QIcon, FluentIconBase], title, content=None, config_name: str = None,
                 parent=None):
        super().__init__(text, icon, title, content, parent)
        self.config_name = config_name
        self.line_text = LineEdit()
        self.line_text.setAlignment(Qt.AlignCenter)
        self.line_text.setReadOnly(True)
        self.line_text.setMaximumWidth(60)
        self.line_text.setText(str(cfg.get_value(self.config_name)))
        current_count = self.hBoxLayout.count()
        self.hBoxLayout.insertWidget(current_count - 2, self.line_text)
        self.button.clicked.connect(self.__onclicked)

    def __onclicked(self):
        message_box = MessageBoxSpinbox(self.tr(self.title), self.window())
        if message_box.exec():
            cfg.set_value(f"hard_mirror_chance", int(message_box.getValue()))
            self.line_text.setText(str(message_box.getValue()))

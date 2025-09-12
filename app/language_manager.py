import inspect

from PySide6.QtCore import QTranslator, QLocale, QLibraryInfo, QT_TRANSLATE_NOOP
from PySide6.QtWidgets import QApplication

from module.config import cfg
from module.logger import log
from utils.singletonmeta import SingletonMeta

# from app.my_app import MainWindow # 不要导入这个

# 遵从 IETF BCP-47 除非和 Qt 的不一样
SUPPORTED_LANG_CODE = {
    "zh_cn": "简体中文",  # 暂时是zh_cn 等之后全局替换
    "en": "English",
}
"""
- 内容为UI支持的语言
- 键为语言**代码**, 值为对应名称
"""

# 反转字典，方便设置界面显示语言名称
SUPPORTED_LANG_NAME = {v: k for k, v in SUPPORTED_LANG_CODE.items()}
"""
- 内容为UI支持的语言
- 键为对语言**名称**, 值为对应代码
"""
SUPPORTED_GAME_LANG_CODE = {
    "-": QT_TRANSLATE_NOOP("BaseComboBox", "(实验性功能) 自动识别"),
    "en": "English",
    "zh_cn": "LLC_简体中文",
}
"""
- 内容为图像识别支持的语言
- 键为语言**代码**, 值为对应名称
"""

# 反转字典，方便设置界面显示语言名称
SUPPORTED_GAME_LANG_NAME = {v: k for k, v in SUPPORTED_GAME_LANG_CODE.items()}
"""
- 内容为图像识别支持的语言
- 键为对语言**名称**, 值为对应代码
"""
retranslateUi = "retranslateUi"
"""触发的控件方法名称"""


class LanguageManager(metaclass=SingletonMeta):
    """### 语言管理器
    ---
    \n通过`register_component(cls)`可以直接在对应文件下注册类
    \n通过`set_language`会触发注册过的类的`retranslateUi`方法, 如果该方法需要参数, 会且仅会传入一个参数, lang_code: `str`
    """

    def __init__(self):
        self.app = QApplication.instance()
        self.translatable_components = []  # 存储所有需要翻译的组件
        self.settings_language = cfg.language_in_program
        self.current_lang = None

        # 保留引用
        self.qt_translator = None
        self.app_translator = None

    def register_component(self, component):
        """注册需要翻译的组件"""
        if component in self.translatable_components:
            return

        if hasattr(component, retranslateUi):
            self.translatable_components.append(component)
            component_name = self.check_component_name(component)
            log.DEBUG(f"注册翻译组件: {component_name}")
        else:
            component_name = self.check_component_name(component)

            log.WARNING(f"组件 {component_name} 没有 {retranslateUi} 方法，无法翻译")

    def unregister_component(self, component):
        """注销需要翻译的组件"""
        if component in self.translatable_components:
            self.translatable_components.remove(component)

    def init_language(self):
        """初始化语言设置"""

        if self.settings_language is None or self.settings_language == "":
            lang = self.match_language()
            cfg.set_value("language_in_program", lang)
        else:
            lang = self.settings_language

        return lang

    def match_language(self) -> str:
        """在支持的语言中匹配最接近用户系统语言的语言"""
        user_lang = QLocale.system().name()  # 获取语言代码 示例: zh_CN
        log.DEBUG(f"检查到用户语言代码为: {user_lang}")

        if user_lang in SUPPORTED_LANG_CODE:
            return user_lang

        main_lang = user_lang.split("_")[0]  # 截取主要语言代码

        if main_lang in SUPPORTED_LANG_CODE:
            return main_lang

        for lang_code in SUPPORTED_LANG_CODE:
            if lang_code.startswith(main_lang):
                return lang_code

        return "en"  # 默认英文

    def reload_translator(self, lang_code=None):
        if lang_code is None:
            lang_code = self.current_lang

        if self.app is None:
            self.app = QApplication.instance()

        # 加载Qt基础翻译
        self.qt_translator = QTranslator()
        qt_path = QLibraryInfo.location(QLibraryInfo.TranslationsPath)
        if self.qt_translator.load(f"qt_{lang_code}", qt_path):
            self.app.installTranslator(self.qt_translator)  # type: ignore

        # 加载应用翻译
        self.app_translator = QTranslator()
        ts_path = "i18n"
        if self.app_translator.load(f"myapp_{lang_code}", ts_path):
            self.app.installTranslator(self.app_translator)  # type: ignore

    def set_language(self, lang_code):
        """设置应用语言"""

        if lang_code == "zh_cn":
            lang_code = "zh_CN"  # 暂时特殊处理 等之后全局替换

        # 更新配置
        log.DEBUG(f"切换语言到: {lang_code}")
        self.current_lang = lang_code

        self.reload_translator(lang_code)

        # 更新UI
        self.retranslate_all(lang_code)

    def retranslate_all(self, lang_code=None):
        """更新所有注册组件的翻译"""

        log.DEBUG("开始更新所有组件翻译...")

        # 更新所有注册的组件
        for component in self.translatable_components:
            try:
                if hasattr(component, retranslateUi):
                    if self.method_needs_args(getattr(component, retranslateUi)):
                        if lang_code is None:
                            component_name = self.check_component_name(component)
                            raise ValueError(
                                f"component {component_name}.{retranslateUi} 需要参数 但是为空"
                            )
                        component.retranslateUi(lang_code)
                    else:
                        component.retranslateUi()

            except Exception as e:
                component_name = self.check_component_name(component)
                log.ERROR(f"翻译错误 {component_name}: {type(e).__name__} {str(e)}")

        log.DEBUG("所有组件翻译更新完成")

    def method_needs_args(self, method):
        """检查方法是否需要参数"""
        sig = inspect.signature(method)
        parameters = sig.parameters
        required_params = []

        for param in parameters.values():
            if param.default == inspect.Parameter.empty and param.kind not in (
                    inspect.Parameter.VAR_POSITIONAL,
                    inspect.Parameter.VAR_KEYWORD,
            ):
                # 排除可变参数
                required_params.append(param)

        if required_params:
            if required_params[0].name == "self" or required_params[0].name == "cls":
                required_params = required_params[1:]

        return len(required_params) > 0

    def check_component_name(self, component) -> str:
        if component.objectName():
            return component.objectName()
        else:
            return component

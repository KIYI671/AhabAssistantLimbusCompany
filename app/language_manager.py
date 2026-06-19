import inspect

from PySide6.QtCore import QLibraryInfo, QLocale, QTranslator
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
retranslateUi = "retranslateUi"
"""触发的控件方法名称"""


class LanguageManager(metaclass=SingletonMeta):
    """语言管理器：通过 register_component 注册组件，set_language 触发所有组件重新翻译。"""

    def __init__(self):
        self.app = QApplication.instance()
        self.translatable_components = []  # (component, needs_lang_arg) 元组
        self.settings_language = cfg.language_in_program
        self.current_lang = None

        # 保留引用
        self.qt_translator = None
        self.app_translator = None

    def register_component(self, component):
        """注册需要翻译的组件"""
        if any(c is component for c, _ in self.translatable_components):
            return

        if hasattr(component, retranslateUi):
            method = getattr(component, retranslateUi)
            needs_arg = self._method_needs_args(method)
            self.translatable_components.append((component, needs_arg))
            log.debug(f"注册翻译组件: {self._component_name(component)}", stacklevel=2)
        else:
            log.warning(
                f"组件 {self._component_name(component)} 没有 {retranslateUi} 方法，无法翻译",
                stacklevel=2,
            )

    def unregister_component(self, component):
        """注销需要翻译的组件"""
        for i, (c, _) in enumerate(self.translatable_components):
            if c is component:
                self.translatable_components.pop(i)
                return
        log.warning(f"组件 {self._component_name(component)} 未注册，无法注销", stacklevel=2)

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
        log.debug(f"检查到用户语言代码为: {user_lang}")

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
        qt_path = QLibraryInfo.location(QLibraryInfo.LibraryPath.TranslationsPath)
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
        log.debug(f"切换语言到: {lang_code}")
        self.current_lang = lang_code

        self.reload_translator(lang_code)

        # 更新UI
        self._retranslate_all(lang_code)

    def _retranslate_all(self, lang_code=None):
        """更新所有注册组件的翻译"""

        log.debug("开始更新所有组件翻译...")

        # 更新所有注册的组件
        for component, needs_arg in self.translatable_components:
            try:
                if needs_arg:
                    if lang_code is None:
                        raise ValueError(f"component {self._component_name(component)}.{retranslateUi} 需要参数但为空")
                    component.retranslateUi(lang_code)
                else:
                    component.retranslateUi()
            except Exception as e:
                log.error(f"翻译错误 {self._component_name(component)}: {type(e).__name__} {str(e)}")

        log.debug("所有组件翻译更新完成")

    @staticmethod
    def _method_needs_args(method):
        """检查方法是否需要参数"""
        sig = inspect.signature(method)
        required_params = [
            p for p in sig.parameters.values()
            if p.default is inspect.Parameter.empty
            and p.kind not in (
                inspect.Parameter.VAR_POSITIONAL,
                inspect.Parameter.VAR_KEYWORD,
            )  # 排除可变参数
        ]
        if required_params and required_params[0].name in ("self", "cls"):
            required_params = required_params[1:]
        return len(required_params) > 0

    @staticmethod
    def _component_name(component) -> str:
        return component.objectName() or str(component)

from PyQt5.QtCore import QObject, pyqtSignal

class Mediator(QObject):
    switch_page = pyqtSignal(str)
    switch_team_setting = pyqtSignal(str)
    delete_team_setting = pyqtSignal(str)
    team_setting = pyqtSignal(dict)
    close_setting = pyqtSignal()
    refresh_teams_order = pyqtSignal()
    sinner_be_selected = pyqtSignal()

    # 单例实例（类变量）
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            # 创建新实例
            cls._instance = super().__new__(cls)
            # 显式调用父类构造函数
            super(cls, cls._instance).__init__()
            # 初始化标志
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if not hasattr(self, '_initialized') or not self._initialized:
            # 这里不需要再调用 super().__init__()，因为已经在 __new__ 中调用过了
            self._initialized = True
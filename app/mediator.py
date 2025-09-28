from PySide6.QtCore import QObject, Signal


class Mediator(QObject):
    switch_page = Signal(str)
    switch_team_setting = Signal(str)
    delete_team_setting = Signal(str)
    team_setting = Signal(dict)
    close_setting = Signal()
    refresh_teams_order = Signal()
    sinner_be_selected = Signal()
    scroll_log_show = Signal(str)
    link_start = Signal()
    save_warning = Signal()
    tasks_warning = Signal()
    update_progress = Signal(int)
    download_complete = Signal(str)
    warning = Signal(str)
    finished_signal = Signal()
    kill_signal = Signal()
    
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

class withOutAdminError(Exception):
    """未获取到管理员权限"""
    def __init__(self, ErrorInfo):
        super().__init__(ErrorInfo)
        self.errorInfo = ErrorInfo

    def __str__(self):
        return self.errorInfo


class withOutPicError(Exception):
    """图片读取失败"""
    def __init__(self, ErrorInfo):
        super().__init__(ErrorInfo)
        self.errorInfo = ErrorInfo

    def __str__(self):
        return self.errorInfo


class notWaitError(Exception):
    """点击开始下载后不等待下载进程
    \n*未使用*"""
    def __init__(self, ErrorInfo):
        super().__init__(ErrorInfo)
        self.errorInfo = ErrorInfo

    def __str__(self):
        return self.errorInfo


class withOutGameWinError(Exception):
    """没有检测到游戏窗口"""
    def __init__(self, ErrorInfo):
        super().__init__(ErrorInfo)
        self.errorInfo = ErrorInfo

    def __str__(self):
        return self.errorInfo


class backMainWinError(Exception):
    """无法回到初始主界面"""
    def __init__(self, ErrorInfo):
        super().__init__(ErrorInfo)
        self.errorInfo = ErrorInfo

    def __str__(self):
        return self.errorInfo


class netWorkUnstableError(Exception):
    """检测到网络不稳只能退出的反馈
    \n*未使用*"""
    def __init__(self, ErrorInfo):
        super().__init__(ErrorInfo)
        self.errorInfo = ErrorInfo

    def __str__(self):
        return self.errorInfo


class cannotOperateGameError(Exception):
    """重试失败过多反馈"""
    def __init__(self, ErrorInfo):
        super().__init__(ErrorInfo)
        self.errorInfo = ErrorInfo

    def __str__(self):
        return self.errorInfo


class unexpectNumError(Exception):
    """出现未知选择
    \n*未使用*"""
    def __init__(self, ErrorInfo):
        super().__init__(ErrorInfo)
        self.errorInfo = ErrorInfo

    def __str__(self):
        return self.errorInfo


class unableToFindTeamError(Exception):
    """队伍配置名称可能有误，无法寻得队伍"""
    def __init__(self, ErrorInfo):
        super().__init__(ErrorInfo)
        self.errorInfo = ErrorInfo

    def __str__(self):
        return self.errorInfo


class userStopError(Exception):
    """用户主动终止，不算错误，但要保持队列"""
    def __init__(self, ErrorInfo):
        super().__init__(ErrorInfo)
        self.errorInfo = ErrorInfo

    def __str__(self):
        return self.errorInfo


class logTypeError(Exception):
    """日志级别不在可选范围内，或没有设置"""
    def __init__(self, ErrorInfo):
        super().__init__(ErrorInfo)
        self.errorInfo = ErrorInfo

    def __str__(self):
        return self.errorInfo


class serverCloseError(Exception):
    """服务器关闭
    \n*未使用*"""
    def __init__(self, ErrorInfo):
        super().__init__(ErrorInfo)
        self.errorInfo = ErrorInfo

    def __str__(self):
        return self.errorInfo


class resolutionSettingError(Exception):
    """分辨率设置错误"""
    def __init__(self, ErrorInfo):
        super().__init__(ErrorInfo)
        self.errorInfo = ErrorInfo

    def __str__(self):
        return self.errorInfo

class settingsTypeError(Exception):
    """设置类型错误 设置的格式不符合AALC的设置格式"""
    def __init__(self, ErrorInfo):
        super().__init__(ErrorInfo)
        self.errorInfo = ErrorInfo

    def __str__(self):
        return self.errorInfo
    
class InputAttributeError(Exception):
    """输入类属性错误 该属性不存在或被废弃"""
    def __init__(self, ErrorInfo):
        super().__init__(ErrorInfo)
        self.errorInfo = ErrorInfo

    def __str__(self):
        return self.errorInfo
# 未获取到管理员权限
class withOutAdminError(Exception):
    def __init__(self, ErrorInfo):
        super().__init__(ErrorInfo)
        self.errorInfo = ErrorInfo

    def __str__(self):
        return self.errorInfo


# 图片读取失败
class withOutPicError(Exception):
    def __init__(self, ErrorInfo):
        super().__init__(ErrorInfo)
        self.errorInfo = ErrorInfo

    def __str__(self):
        return self.errorInfo


# 暂时没有这个:点击开始下载后不等待下载进程
class notWaitError(Exception):
    def __init__(self, ErrorInfo):
        super().__init__(ErrorInfo)
        self.errorInfo = ErrorInfo

    def __str__(self):
        return self.errorInfo


# 没有检测到游戏窗口
class withOutGameWinError(Exception):
    def __init__(self, ErrorInfo):
        super().__init__(ErrorInfo)
        self.errorInfo = ErrorInfo

    def __str__(self):
        return self.errorInfo


# 无法回到初始主界面
class backMainWinError(Exception):
    def __init__(self, ErrorInfo):
        super().__init__(ErrorInfo)
        self.errorInfo = ErrorInfo

    def __str__(self):
        return self.errorInfo


# 暂时没有这个:检测到网络不稳只能退出的反馈
class netWorkUnstableError(Exception):
    def __init__(self, ErrorInfo):
        super().__init__(ErrorInfo)
        self.errorInfo = ErrorInfo

    def __str__(self):
        return self.errorInfo


# 暂时没有这个:重试失败过多反馈
class cannotOperateGameError(Exception):
    def __init__(self, ErrorInfo):
        super().__init__(ErrorInfo)
        self.errorInfo = ErrorInfo

    def __str__(self):
        return self.errorInfo


# 暂时没有这个:出现未知选择
class unexpectNumError(Exception):
    def __init__(self, ErrorInfo):
        super().__init__(ErrorInfo)
        self.errorInfo = ErrorInfo

    def __str__(self):
        return self.errorInfo


# 队伍配置名称可能有误，无法寻得队伍
class unableToFindTeamError(Exception):
    def __init__(self, ErrorInfo):
        super().__init__(ErrorInfo)
        self.errorInfo = ErrorInfo

    def __str__(self):
        return self.errorInfo


# 用户主动终止，不算错误，但要保持队列
class userStopError(Exception):
    def __init__(self, ErrorInfo):
        super().__init__(ErrorInfo)
        self.errorInfo = ErrorInfo

    def __str__(self):
        return self.errorInfo


# 日志级别不在可选范围内，或没有设置
class logTypeError(Exception):
    def __init__(self, ErrorInfo):
        super().__init__(ErrorInfo)
        self.errorInfo = ErrorInfo

    def __str__(self):
        return self.errorInfo


# 暂时没有这个:服务器关闭
class serverCloseError(Exception):
    def __init__(self, ErrorInfo):
        super().__init__(ErrorInfo)
        self.errorInfo = ErrorInfo

    def __str__(self):
        return self.errorInfo


# 分辨率设置错误
class resolutionSettingError(Exception):
    def __init__(self, ErrorInfo):
        super().__init__(ErrorInfo)
        self.errorInfo = ErrorInfo

    def __str__(self):
        return self.errorInfo

# 设置类型错误 设置的格式不符合AALC的设置格式
class settingsTypeError(Exception):
    def __init__(self, ErrorInfo):
        super().__init__(ErrorInfo)
        self.errorInfo = ErrorInfo

    def __str__(self):
        return self.errorInfo
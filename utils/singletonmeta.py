import threading


class SingletonMeta(type):
    """线程安全的单例元类。

    通过在 __call__ 中实现双检锁来确保一个类只有一个实例。
    """

    # 存储创建的实例
    _instances = {}
    _lock = threading.RLock()

    def __call__(cls, *args, **kwargs):
        # 检查类是否已经有实例
        if cls not in cls._instances:
            with cls._lock:
                if cls not in cls._instances:
                    # 如果没有实例，使用super调用基类的__call__方法创建实例，并存储
                    cls._instances[cls] = super().__call__(*args, **kwargs)
        # 返回实例
        return cls._instances[cls]

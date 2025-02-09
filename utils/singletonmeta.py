class SingletonMeta(type):
    """
    一个用于创建单例的元类。

    该元类通过在类的__call__方法中实现实例的复用来确保一个类只有一个实例。
    """

    # 存储创建的实例
    _instances = {}

    def __call__(cls, *args, **kwargs):
        """
        调用类时执行的方法。

        如果类没有被实例化，则创建一个新的实例并存储。
        如果类已经被实例化，则返回之前的实例。

        参数:
        - *args: 允许的位置参数。
        - **kwargs: 允许的关键字参数。

        返回:
        类的单个实例。
        """
        # 检查类是否已经有实例
        if cls not in cls._instances:
            # 如果没有实例，使用super调用基类的__call__方法创建实例，并存储
            cls._instances[cls] = super().__call__(*args, **kwargs)
        # 返回实例
        return cls._instances[cls]

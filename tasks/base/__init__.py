def update_model_for_retry(remaining: int, normal_at: int = 20, aggressive_at: int = 10):
    """根据剩余重试次数渐进切换 auto.model: clam → normal → aggressive。"""
    from module.automation import auto
    if remaining < aggressive_at:
        auto.model = "aggressive"
    elif remaining < normal_at:
        auto.model = "normal"

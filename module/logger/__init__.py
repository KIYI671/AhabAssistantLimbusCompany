from .my_log import Logger, ui_log_dispatcher

log = Logger().get_logger()

__all__ = ["log", "ui_log_dispatcher"]

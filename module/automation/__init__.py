from module.automation.automation import Automation
from module.config import cfg

auto = Automation(cfg.get_value("game_title_name"))

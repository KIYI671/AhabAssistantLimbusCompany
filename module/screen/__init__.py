from module.config import cfg
from module.logger import log
from module.screen.screen import Screen

screen = Screen(title=cfg.game_title_name, logger=log)

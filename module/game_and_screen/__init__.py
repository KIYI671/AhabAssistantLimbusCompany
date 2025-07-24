from module.config import cfg
from module.game_and_screen.screen import Screen
from module.logger import log

screen = Screen(title=cfg.game_title_name, logger=log)

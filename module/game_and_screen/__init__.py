from module.config import cfg
from module.game_and_screen.game import Game
from module.game_and_screen.screen import Screen
from module.logger import log

game_process = Game(logger=log)

screen = Screen(title=cfg.game_title_name, logger=log,game = game_process)
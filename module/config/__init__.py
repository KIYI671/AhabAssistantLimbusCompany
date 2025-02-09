import os

from module.config.config import Config, Theme_pack_list

VERSION_PATH = "./assets/config/version.txt"
EXAMPLE_PATH = "./assets/config/config.example.yaml"
CONFIG_PATH = "./config.yaml"

cfg = Config(VERSION_PATH, EXAMPLE_PATH, CONFIG_PATH)

# 复制当前环境变量，以便在不修改原始环境变量的情况下进行后续操作
cfg.env = os.environ.copy()
# 更新环境变量中的PATH，将Python可执行文件所在目录添加到PATH的开头
# 这样做是为了确保在调用外部命令时，Python解释器能够正确找到所需的可执行文件
# cfg.env['PATH'] = os.path.dirname(cfg.python_exe_path) + ';' + cfg.env['PATH']
# 构建用户代理字符串，用于标识此AALC的版本信息
# 用户代理是HTTP请求中的一部分，服务器可以使用它来识别客户端的类型和特性
cfg.useragent = {"User-Agent": f"AhabLimbusCompany/{cfg.version}"}

THEME_PACK_LIST_EXAMPLE_PATH = "./assets/config/theme_pack_list.example.yaml"
THEME_PACK_LIST_PATH = "./theme_pack_list.yaml"

theme_list = Theme_pack_list(THEME_PACK_LIST_EXAMPLE_PATH, THEME_PACK_LIST_PATH)

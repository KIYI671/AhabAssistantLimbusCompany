# coding=utf8
"""
此文件nb_log_config.py是自动生成到python项目的根目录的,因为是自动生成到 sys.path[1]。
在这里面写的变量会覆盖此文件nb_log_config_default中的值。对nb_log包进行默认的配置。用户是无需修改nb_log安装包位置里面的配置文件的。

但最终配置方式是由get_logger_and_add_handlers方法的各种传参决定，如果方法相应的传参为None则使用这里面的配置。
"""

"""
如果反对日志有各种彩色，可以设置 DEFAULUT_USE_COLOR_HANDLER = False
如果反对日志有块状背景彩色，可以设置 DISPLAY_BACKGROUD_COLOR_IN_CONSOLE = False
如果想屏蔽nb_log包对怎么设置pycahrm的颜色的提示，可以设置 WARNING_PYCHARM_COLOR_SETINGS = False
如果想改变日志模板，可以设置 FORMATTER_KIND 参数，只带了7种模板，可以自定义添加喜欢的模板
LOG_PATH 配置文件日志的保存路径的文件夹。
"""
import sys
# noinspection PyUnresolvedReferences
import logging
import os
# noinspection PyUnresolvedReferences
from pathlib import Path  # noqa
import socket
from pythonjsonlogger.jsonlogger import JsonFormatter

# 项目中的print是否自动写入到文件中。值为None则不重定向print到文件中。 自动每天一个文件， 2023-06-30.my_proj.print,生成的文件位置在定义的LOG_PATH
# 如果你设置了环境变量，export PRINT_WRTIE_FILE_NAME="my_proj.print" (linux临时环境变量语法，windows语法自己百度这里不举例),那就优先使用环境变量中设置的文件名字，而不是nb_log_config.py中设置的名字
PRINT_WRTIE_FILE_NAME = os.environ.get("PRINT_WRTIE_FILE_NAME") or Path(sys.path[1]).name + '.print'

# 项目中的所有标准输出（不仅包括print，还包括了streamHandler日志）都写入到这个文件，为None将不把标准输出重定向到文件。自动每天一个文件， 2023-06-30.my_proj.std,生成的文件位置在定义的LOG_PATH
# 如果你设置了环境变量，export SYS_STD_FILE_NAME="my_proj.std"  (linux临时环境变量语法，windows语法自己百度这里不举例),那就优先使用环境变量中设置的文件名字，，而不是nb_log_config.py中设置的名字
# 这个相当于是 nohup 自动重定向所有屏幕输出流到一个nohup.out文件的功能了,这个是nb_log日志包的独有黑科技功能,logging 和loguru没这种功能.
SYS_STD_FILE_NAME = os.environ.get("SYS_STD_FILE_NAME") or Path(sys.path[1]).name + '.std'

USE_BULK_STDOUT_ON_WINDOWS = False  # 在win上是否每隔0.1秒批量stdout,win的io太差了

DEFAULUT_USE_COLOR_HANDLER = True  # 是否默认使用有彩的日志。
DEFAULUT_IS_USE_LOGURU_STREAM_HANDLER = False  # 是否默认使用 loguru的控制台日志，而非是nb_log的ColorHandler
DISPLAY_BACKGROUD_COLOR_IN_CONSOLE = False  # 在控制台是否显示彩色块状的日志。为False则不使用大块的背景颜色。
AUTO_PATCH_PRINT = False  # 是否自动打print的猴子补丁，如果打了猴子补丁，print自动变色和可点击跳转。

# 以下是屏蔽控制台所谓的烦人提示项,如果要关闭,先了解下这三个提示是什么,有的pythoner又菜又爱屏蔽提示,然后不知道为什么,这样的人太烦人了.
SHOW_PYCHARM_COLOR_SETINGS = False  # 有的人很反感启动代码时候提示教你怎么优化pycahrm控制台颜色，可以把这里设置为False  (怕提示颜色设置打扰你又不懂pycharm和python的颜色原理,就别抱怨颜色瞎眼)
SHOW_NB_LOG_LOGO = False  # 有的人反感启动代码时候打印nb_log 的logo图形,可以设置为False
SHOW_IMPORT_NB_LOG_CONFIG_PATH = True  # 是否打印读取的nb_log_config.py的文件位置.不懂pythonpath,不懂python导入模块机制的人,别屏蔽了,学习下  https://github.com/ydf0509/pythonpathdemo

WHITE_COLOR_CODE = 37  # 不同pycharm版本和主题,有的对白颜色生效的代号是97,有的是37, 这里可以设置 37和97, 如2023 pycahrm的console color,白颜色捕获的是97,如果这里写37,调节pycharm颜色没法调.

DEFAULT_ADD_MULTIPROCESSING_SAFE_ROATING_FILE_HANDLER = False  # 是否默认同时将日志记录到记log文件记事本中，就是用户不指定 log_filename的值，会自动写入日志命名空间.log文件中。
AUTO_WRITE_ERROR_LEVEL_TO_SEPARATE_FILE = True  # 自动把错误error级别以上日志写到单独的文件，根据log_filename名字自动生成错误文件日志名字。
LOG_FILE_SIZE = 1000  # 单位是M,每个文件的切片大小，超过多少后就自动切割
LOG_FILE_BACKUP_COUNT = 10  # 对同一个日志文件，默认最多备份几个文件，超过就删除了。

LOG_PATH = os.getenv("LOG_PATH")  # 优先从环境变量获取,启动代码之前可以 export LOG_PATH = '/你的日志目录/'
if not LOG_PATH:
    LOG_PATH = '/pythonlogs'  # 默认的日志文件夹,如果不写明磁盘名，则是项目代码所在磁盘的根目录下的/pythonlogs
    # LOG_PATH = Path(__file__).absolute().parent / Path("pythonlogs")   #这么配置就会自动在你项目的根目录下创建pythonlogs文件夹了并写入。
    if os.name == 'posix':  # linux非root用户和mac用户无法操作 /pythonlogs 文件夹，没有权限，默认修改为   home/[username]  下面了。例如你的linux用户名是  xiaomin，那么默认会创建并在 /home/xiaomin/pythonlogs文件夹下写入日志文件。
        home_path = os.environ.get("HOME", '/')  # 这个是获取linux系统的当前用户的主目录，不需要亲自设置
        LOG_PATH = Path(home_path) / Path('pythonlogs')  # linux mac 权限很严格，非root权限不能在/pythonlogs写入，修改一下默认值。
# print('LOG_PATH:',LOG_PATH)

LOG_FILE_HANDLER_TYPE = 6  # 1 2 3 4 5 6 7   # nb_log 的日志切割,全都追求多进程下切割正常.
"""
LOG_FILE_HANDLER_TYPE 这个值可以设置为 1 2 3 4 5 四种值，
1为使用多进程安全按日志文件大小切割的文件日志,这是本人实现的批量写入日志，减少操作文件锁次数，测试10进程快速写入文件，win上性能比第5种提高了100倍，linux提升5倍
2为多进程安全按天自动切割的文件日志，同一个文件，每天生成一个新的日志文件。日志文件名字后缀自动加上日期。
3为不自动切割的单个文件的日志(不切割文件就不会出现所谓进程安不安全的问题) 
4为 WatchedFileHandler，这个是需要在linux下才能使用，需要借助lograte外力进行日志文件的切割，多进程安全。
5 为第三方的concurrent_log_handler.ConcurrentRotatingFileHandler按日志文件大小切割的文件日志，
   这个是采用了文件锁，多进程安全切割，文件锁在linux上使用fcntl性能还行，win上使用win32con性能非常惨。按大小切割建议不要选第5个个filehandler而是选择第1个。
6 BothDayAndSizeRotatingFileHandler 使用本人完全彻底开发的，同时按照时间和大小切割，无论是文件的大小、还是时间达到了需要切割的条件就切割。
7 LoguruFileHandler ,使用知名的 loguru 包的文件日志记录器来写文件。
"""

LOG_LEVEL_FILTER = logging.DEBUG  # 默认日志级别，低于此级别的日志不记录了。例如设置为INFO，那么logger.debug的不会记录，只会记录logger.info以上级别的。
# 强烈不建议调高这里的级别为INFO，日志是有命名空间的，单独提高打印啰嗦的日志命名空间的日志级别就可以了，不要全局提高日志级别。
# https://nb-log-doc.readthedocs.io/zh_CN/latest/articles/c9.html#id2  文档9.5里面讲了几百次 python logging的命名空间的作用了，有些人到现在还不知道日志的name作用。

# 屏蔽的字符串显示，用 if in {打印信息} 来判断实现的,如果打印的消息中包括 FILTER_WORDS_PRINT 数组中的任何一个字符串，那么消息就不执行打印。
# 这个配置对 print 和 logger的控制台输出都生效。这个可以过滤某些啰嗦的print信息，也可以过滤同级别日志中的某些烦人的日志。可以用来过滤三方包中某些控制台打印。数组不要配置过多，否则有一丝丝影响性能会。
FILTER_WORDS_PRINT = []  # 例如， 你希望消息中包括阿弥陀佛 或者 包括善哉善哉 就不打印，那么可以设置  FILTER_WORDS_PRINT = ['阿弥陀佛','善哉善哉']


def get_host_ip():
    ip = ''
    host_name = ''
    # noinspection PyBroadException
    try:
        sc = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sc.connect(('8.8.8.8', 80))
        ip = sc.getsockname()[0]
        host_name = socket.gethostname()
        sc.close()
    except Exception:
        pass
    return ip, host_name


computer_ip, computer_name = get_host_ip()


class JsonFormatterJumpAble(JsonFormatter):
    def add_fields(self, log_record, record, message_dict):
        # log_record['jump_click']   = f"""File '{record.__dict__.get('pathname')}', line {record.__dict__.get('lineno')}"""
        log_record[f"{record.__dict__.get('pathname')}:{record.__dict__.get('lineno')}"] = ''  # 加个能点击跳转的字段。
        log_record['ip'] = computer_ip
        log_record['host_name'] = computer_name
        super().add_fields(log_record, record, message_dict)
        if 'for_segmentation_color' in log_record:
            del log_record['for_segmentation_color']


DING_TALK_TOKEN = '3dd0eexxxxxadab014bd604XXXXXXXXXXXX'  # 钉钉报警机器人

EMAIL_HOST = ('smtp.sohu.com', 465)
EMAIL_FROMADDR = 'aaa0509@sohu.com'  # 'matafyhotel-techl@matafy.com',
EMAIL_TOADDRS = ('cccc.cheng@silknets.com', 'yan@dingtalk.com',)
EMAIL_CREDENTIALS = ('aaa0509@sohu.com', 'abcdefg')

ELASTIC_HOST = '127.0.0.1'
ELASTIC_PORT = 9200

KAFKA_BOOTSTRAP_SERVERS = ['192.168.199.202:9092']
ALWAYS_ADD_KAFKA_HANDLER_IN_TEST_ENVIRONENT = False

MONGO_URL = 'mongodb://myUserAdmin:mimamiama@127.0.0.1:27016/admin'

RUN_ENV = 'test'

FORMATTER_DICT = {
    1: logging.Formatter(
        '日志时间【%(asctime)s】 - 日志名称【%(name)s】 - 文件【%(filename)s】 - 第【%(lineno)d】行 - 日志等级【%(levelname)s】 - 日志信息【%(message)s】',
        "%Y-%m-%d %H:%M:%S"),
    2: logging.Formatter(
        '%(asctime)s - %(name)s - %(filename)s - %(funcName)s - %(lineno)d - %(levelname)s - %(message)s',
        "%Y-%m-%d %H:%M:%S"),
    3: logging.Formatter(
        '%(asctime)s - %(name)s - 【 File "%(pathname)s", line %(lineno)d, in %(funcName)s 】 - %(levelname)s - %(message)s',
        "%Y-%m-%d %H:%M:%S"),  # 一个模仿traceback异常的可跳转到打印日志地方的模板
    4: logging.Formatter(
        '%(asctime)s - %(name)s - "%(filename)s" - %(funcName)s - %(lineno)d - %(levelname)s - %(message)s -               File "%(pathname)s", line %(lineno)d ',
        "%Y-%m-%d %H:%M:%S"),  # 这个也支持日志跳转
    5: logging.Formatter(
        '%(asctime)s - %(name)s - "%(pathname)s:%(lineno)d" - %(funcName)s - %(levelname)s - %(message)s',
        "%Y-%m-%d %H:%M:%S"),  # 我认为的最好的模板,推荐
    6: logging.Formatter('%(name)s - %(asctime)-15s - %(filename)s - %(lineno)d - %(levelname)s: %(message)s',
                         "%Y-%m-%d %H:%M:%S"),
    7: logging.Formatter('%(asctime)s - %(name)s - "%(filename)s:%(lineno)d" - %(levelname)s - %(message)s', "%Y-%m-%d %H:%M:%S"),  # 一个只显示简短文件名和所处行数的日志模板

    8: JsonFormatterJumpAble('%(asctime)s - %(name)s - %(levelname)s - %(message)s - %(filename)s %(lineno)d  %(process)d %(thread)d', "%Y-%m-%d %H:%M:%S.%f",
                             json_ensure_ascii=False),  # 这个是json日志，方便elk采集分析.

    9: logging.Formatter(
        '[p%(process)d_t%(thread)d] %(asctime)s - %(name)s - "%(pathname)s:%(lineno)d" - %(funcName)s - %(levelname)s - %(message)s',
        "%Y-%m-%d %H:%M:%S"),  # 对5改进，带进程和线程显示的日志模板。
    10: logging.Formatter(
        '[p%(process)d_t%(thread)d] %(asctime)s - %(name)s - "%(filename)s:%(lineno)d" - %(levelname)s - %(message)s', "%Y-%m-%d %H:%M:%S"),  # 对7改进，带进程和线程显示的日志模板。
    11: logging.Formatter(
        f'%(asctime)s-({computer_ip},{computer_name})-[p%(process)d_t%(thread)d] - %(name)s - "%(filename)s:%(lineno)d" - %(funcName)s - %(levelname)s - %(message)s', "%Y-%m-%d %H:%M:%S"),  # 对7改进，带进程和线程显示的日志模板以及ip和主机名。
}

FORMATTER_KIND = 5  # 如果get_logger不指定日志模板，则默认选择第几个模板

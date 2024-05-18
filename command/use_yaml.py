# import yaml
from ruamel.yaml import YAML

from my_log.my_log import my_log

yaml = YAML()


def get_yaml_information():
    with open('config.yaml', 'r', encoding='utf-8') as file:
        config_data = yaml.load(file)
        return config_data


def save_yaml(config_data):
    with open('config.yaml', 'w', encoding='utf-8') as file:
        msg = f"保存yaml配置文件"
        my_log("debug", msg)
        yaml.dump(config_data, file)


def get_black_list_keyword_yaml():
    with open('black_list_keyword.yaml', 'r', encoding='utf-8') as file:
        msg = f"读取镜牢主题包黑名单"
        my_log("debug", msg)
        config_data = yaml.load(file)
        return config_data

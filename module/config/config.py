import copy
import sys

from ruamel.yaml import YAML

from utils.singletonmeta import SingletonMeta


class Config(metaclass=SingletonMeta):

    def __init__(self, version_path, example_path, config_path):
        self.yaml = YAML()
        # 加载版本信息
        self.version = self._load_version(version_path)
        # 加载默认配置
        self.config = self._load_default_config(example_path)
        # 获取用户的配置文件路径
        self.config_path = config_path
        # 加载实际配置，此方法会根据实际配置覆盖默认配置
        self._load_config()

    def _load_version(self, version_path):
        """加载版本信息"""
        try:
            with open(version_path, 'r', encoding='utf-8') as file:
                return file.read().strip()
        except FileNotFoundError:
            sys.exit("版本文件未找到")

    def _load_default_config(self, example_path):
        """加载默认配置信息"""
        try:
            with open(example_path, 'r', encoding='utf-8') as file:
                return self.yaml.load(file) or {}
        except FileNotFoundError:
            sys.exit("默认配置文件未找到")

    def _load_config(self, path=None):
        """加载用户配置文件，如未找到则保存默认配置"""
        path = path or self.config_path
        try:
            with open(path, 'r', encoding='utf-8') as file:
                loaded_config = self.yaml.load(file)
                if loaded_config:
                    self._update_config(self.config, loaded_config)
                    self.save_config()
        except FileNotFoundError:
            self.save_config()
        except Exception as e:
            sys.exit(f"配置文件{path}加载错误: {e}")

    def _update_config(self, config, new_config):
        """递归更新配置信息"""
        for key, value in new_config.items():
            if key in config:
                if isinstance(config[key], dict) and isinstance(value, dict):
                    self._update_config(config[key], value)
                else:
                    config[key] = value

    def save_config(self):
        """保存到配置文件"""
        with open(self.config_path, 'w', encoding='utf-8') as file:
            self.yaml.dump(self.config, file)

    def get_value(self, key, default=None):
        """获取配置项的值，如果是可变对象，则返回其拷贝"""
        value = self.config.get(key, default)
        # 如果是可变对象，则返回其拷贝
        if isinstance(value, (list, dict, set)):
            return copy.deepcopy(value)  # 使用深拷贝确保嵌套对象安全
        return value

    def set_value(self, key, value):
        """设置配置项的值并保存"""
        self._load_config()
        if isinstance(value, (list, dict, set)):
            self.config[key] = copy.deepcopy(value)
        else:
            self.config[key] = value
        self.save_config()

    def __getattr__(self, attr):
        """允许通过属性访问配置项的值"""
        if attr in self.config:
            value = self.config[attr]
            if isinstance(value, (list, dict, set)):
                return copy.deepcopy(value)
            return value
        raise AttributeError(f"'{type(self).__name__}' 对象没有属性 ‘{attr}'")


class Blacklist(metaclass=SingletonMeta):

    def __init__(self, example_path, blacklist_path):
        self.yaml = YAML()
        # 加载默认配置
        self.config = self._load_default_config(example_path)
        # 获取用户的配置文件路径
        self.blacklist_path = blacklist_path
        # 加载实际配置，此方法会根据实际配置覆盖默认配置
        self._load_config()

    def _load_version(self, version_path):
        """加载版本信息"""
        try:
            with open(version_path, 'r', encoding='utf-8') as file:
                return file.read().strip()
        except FileNotFoundError:
            sys.exit("黑名单文件未找到")

    def _load_default_config(self, example_path):
        """加载默认配置信息"""
        try:
            with open(example_path, 'r', encoding='utf-8') as file:
                return self.yaml.load(file) or {}
        except FileNotFoundError:
            sys.exit("默认配置文件未找到")

    def _load_config(self, path=None):
        """加载用户配置文件，如未找到则保存默认配置"""
        path = path or self.blacklist_path
        try:
            with open(path, 'r', encoding='utf-8') as file:
                loaded_config = self.yaml.load(file)
                if loaded_config:
                    self._update_config(self.config, loaded_config)
                    self.save_config()
        except FileNotFoundError:
            self.save_config()
        except Exception as e:
            sys.exit(f"配置文件{path}加载错误: {e}")

    def _update_config(self, config, new_config):
        """递归更新配置信息"""
        for key, value in new_config.items():
            if key in config:
                if isinstance(config[key], dict) and isinstance(value, dict):
                    self._update_config(config[key], value)
                else:
                    config[key] = value

    def save_config(self):
        """保存到配置文件"""
        with open(self.blacklist_path, 'w', encoding='utf-8') as file:
            self.yaml.dump(self.config, file)

    def get_value(self, key, default=None):
        """获取配置项的值，如果是可变对象，则返回其拷贝"""
        value = self.config.get(key, default)
        # 如果是可变对象，则返回其拷贝
        if isinstance(value, (list, dict, set)):
            return copy.deepcopy(value)  # 使用深拷贝确保嵌套对象安全
        return value

    def set_value(self, key, value):
        """设置配置项的值并保存"""
        self._load_config()
        if isinstance(value, (list, dict, set)):
            self.config[key] = copy.deepcopy(value)
        else:
            self.config[key] = value
        self.save_config()

    def __getattr__(self, attr):
        """允许通过属性访问配置项的值"""
        if attr in self.config:
            value = self.config[attr]
            if isinstance(value, (list, dict, set)):
                return copy.deepcopy(value)
            return value
        raise AttributeError(f"'{type(self).__name__}' 对象没有属性 ‘{attr}'")

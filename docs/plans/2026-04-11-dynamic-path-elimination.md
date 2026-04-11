# 动态路径淘汰机制实现方案

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 实现运行时动态路径淘汰机制：当dark主题图片匹配失败而default主题图片匹配成功时，自动淘汰所有dark路径

**Architecture:** 创建PathManager管理路径状态，修改image_utils.py返回加载路径信息，在automation.py的find_image_element中实现淘汰逻辑，移除script_task_scheme.py中的一次性主题检测

**Tech Stack:** Python, OpenCV, PIL, 现有AALC框架

---

## 前置分析

当前系统路径逻辑：
1. `utils/__init__.py` 定义全局 `pic_path = ["en", "share"]`
2. `tasks/base/script_task_scheme.py:305-361` 根据语言和主题检测重新配置路径
3. `utils/image_utils.py:15-66` 的 `load_image()` 按 `pic_path` 顺序搜索加载图片
4. `module/automation/automation.py:490-534` 的 `find_image_element()` 调用 `load_image()` 加载模板并进行匹配

需要改造：
1. 移除 `script_task_scheme.py` 的主题检测逻辑（第312-361行）
2. 改为根据语言初始化包含所有dark和default路径
3. 在运行时检测dark失败/default成功的情况，淘汰dark路径

### Task 1: 创建路径管理器 (PathManager)

**Files:**
- Create: `utils/path_manager.py`
- Modify: `utils/__init__.py`
- Test: 手动验证路径管理功能

**Step 1: 创建路径管理器基础类**

```python
# utils/path_manager.py
import logging
from typing import List

log = logging.getLogger(__name__)

from utils.singletonmeta import SingletonMeta

class PathManager(metaclass=SingletonMeta):
    """管理图片搜索路径和淘汰逻辑，并同步更新全局pic_path"""

    def __init__(self):
        self.all_paths = []  # 所有可能的路径
        self.active_paths = []  # 当前活跃路径
        self.dark_paths = []  # dark路径列表
        self.is_dark_eliminated = False  # dark路径是否已被淘汰
        self._pic_path_reference = None  # 全局pic_path的引用
        self.dynamic_optimization = True  # 动态优化开关

    def initialize_paths(self, language: str, pic_path_ref=None, config=None) -> None:
        """根据语言初始化路径并设置全局pic_path引用"""
        if language == "zh_cn":
            self.all_paths = ["zh_cn_dark", "en_dark", "share_dark", "zh_cn", "en", "share"]
        else:  # en或其他
            self.all_paths = ["en_dark", "share_dark", "en", "share"]

        self.active_paths = self.all_paths.copy()
        self.dark_paths = [p for p in self.all_paths if "_dark" in p]
        self.is_dark_eliminated = False

        # 设置全局pic_path引用
        # 如果没有显式传入 pic_path_ref，自动获取全局 pic_path
        # 这确保无论调用方是否传入引用，PathManager 都能同步实际查图路径
        if pic_path_ref is None:
            from utils import pic_path
            pic_path_ref = pic_path
        self._pic_path_reference = pic_path_ref

        # 同步更新全局pic_path
        self._pic_path_reference.clear()
        self._pic_path_reference.extend(self.active_paths)

        # 读取配置
        if config and hasattr(config, 'get_value'):
            self.dynamic_optimization = config.get_value("dynamic_path_optimization", True)
        else:
            self.dynamic_optimization = True

        from module.logger import log
        log.info(f"路径管理器初始化完成，语言: {language}, 路径: {self.active_paths}, 动态优化: {self.dynamic_optimization}")

    def eliminate_dark_paths(self) -> bool:
        """淘汰所有dark路径，并同步更新全局pic_path"""
        if not self.is_dark_eliminated and self.dynamic_optimization:
            new_active_paths = [p for p in self.active_paths if "_dark" not in p]
            if new_active_paths != self.active_paths:
                self.active_paths = new_active_paths
                self.is_dark_eliminated = True

                # 同步更新全局pic_path
                self._pic_path_reference.clear()
                self._pic_path_reference.extend(self.active_paths)

                # 注意：缓存清理不在此处执行，由调用方（find_image_element）
                # 在确认淘汰后对自身实例执行 self.clear_img_cache()，
                # 避免与全局 auto 单例硬耦合

                from module.logger import log
                log.info(f"淘汰所有dark路径，当前路径: {self.active_paths}")
                return True
        return False

    def get_active_paths(self) -> List[str]:
        """获取当前活跃路径"""
        return self.active_paths.copy()

    def is_path_dark(self, path: str) -> bool:
        """判断路径是否为dark路径"""
        return "_dark" in path

    def get_dark_paths(self) -> List[str]:
        """获取所有dark路径"""
        return self.dark_paths.copy()

    def ensure_language_priority(self, language: str) -> None:
        """确保指定语言路径在搜索顺序中优先（兼容现有逻辑）"""
        if not self.active_paths:
            return

        # 根据语言确定优先级
        if language == "zh_cn":
            priority_paths = ["zh_cn", "en", "share"]
        else:
            priority_paths = ["en", "share"]

        # 重新排序：优先语言路径在前，其他保持原有相对顺序
        sorted_paths = []
        for priority in priority_paths:
            for path in self.active_paths:
                if path == priority and path not in sorted_paths:
                    sorted_paths.append(path)

        # 添加剩余路径
        for path in self.active_paths:
            if path not in sorted_paths:
                sorted_paths.append(path)

        if sorted_paths != self.active_paths:
            self.active_paths = sorted_paths
            # 同步更新全局pic_path
            if self._pic_path_reference is not None:
                self._pic_path_reference.clear()
                self._pic_path_reference.extend(self.active_paths)

            from module.logger import log
            log.debug(f"已调整语言优先级，当前路径: {self.active_paths}")

# 全局实例
path_manager = PathManager()
```

**Step 2: 更新utils/__init__.py导入路径管理器**

```python
# utils/__init__.py
from .path_manager import path_manager

# 全局路径列表，由PathManager管理
pic_path = ["en", "share"]  # 默认值，启动后由PathManager更新

# 导出path_manager以便其他模块访问
__all__ = ["pic_path", "path_manager"]
```

**Step 3: 手动验证路径管理器功能**

创建测试脚本验证：
```python
# test_path_manager.py
import sys
sys.path.insert(0, '.')
from utils import pic_path, path_manager

# 测试中文初始化（传递pic_path引用）
path_manager.initialize_paths("zh_cn", pic_path_ref=pic_path)
print("中文路径:", path_manager.get_active_paths())
print("全局pic_path:", pic_path)
print("Dark路径:", path_manager.get_dark_paths())

# 测试淘汰
path_manager.eliminate_dark_paths()
print("淘汰后路径:", path_manager.get_active_paths())
print("淘汰后全局pic_path:", pic_path)

# 测试英文初始化
path_manager.initialize_paths("en", pic_path_ref=pic_path)
print("英文路径:", path_manager.get_active_paths())
print("全局pic_path:", pic_path)
path_manager.eliminate_dark_paths()
print("淘汰后路径:", path_manager.get_active_paths())
print("淘汰后全局pic_path:", pic_path)

# 测试语言优先级调整
path_manager.ensure_language_priority("zh_cn")
print("调整语言优先级后路径:", path_manager.get_active_paths())
```

运行测试：
```bash
cd C:\Users\12192\AhabAssistantLimbusCompany
python test_path_manager.py
```

期望输出：
```
中文路径: ['zh_cn_dark', 'en_dark', 'share_dark', 'zh_cn', 'en', 'share']
全局pic_path: ['zh_cn_dark', 'en_dark', 'share_dark', 'zh_cn', 'en', 'share']
Dark路径: ['zh_cn_dark', 'en_dark', 'share_dark']
淘汰后路径: ['zh_cn', 'en', 'share']
淘汰后全局pic_path: ['zh_cn', 'en', 'share']
英文路径: ['en_dark', 'share_dark', 'en', 'share']
全局pic_path: ['en_dark', 'share_dark', 'en', 'share']
淘汰后路径: ['en', 'share']
淘汰后全局pic_path: ['en', 'share']
调整语言优先级后路径: ['en', 'share']  # 英文环境下en已在首位
```

**Step 4: 提交更改**

```bash
git add utils/path_manager.py utils/__init__.py
git commit -m "feat: 添加路径管理器PathManager"
```

### Task 2: 修改image_utils.py支持路径追踪

**Files:**
- Modify: `utils/image_utils.py:15-66`
- Test: 手动验证修改后的load_image功能

**Step 1: 修改load_image函数返回路径信息**

```python
# utils/image_utils.py 修改load_image函数
@staticmethod
def load_image(image_path, resize=True, return_path=False):
    """
    加载图片，并根据指定区域裁剪图片。
    :param image_path: 图片文件路径。
    :param resize: 是否根据窗口大小调整图片尺寸。
    :param return_path: 是否返回图片加载的路径。
    :return: 如果return_path为True，返回(图片数组, 路径)；否则返回图片数组。
    """
    try:
        img_path = None
        selected_path = None

        # 仍然从全局 pic_path 读取路径顺序
        # 重要：不能改为 path_manager.get_active_paths()，
        # 因为 infinite_battle.py 和 production_module.py 等模块
        # 仍会直接修改 pic_path 来调整搜索优先级
        from utils import pic_path as search_paths

        for path in search_paths:
            img_path = os.path.join(f"./assets/images/{path}/{image_path}")
            if os.path.exists(img_path):
                selected_path = path
                break

        if img_path is None or not os.path.exists(img_path):
            log.error(f"未找到图片： {image_path}")
            return (None, None) if return_path else None

        # 使用上下文管理器打开图片文件，确保文件对象及时关闭
        with Image.open(img_path) as img:
            # 将图片转换为numpy数组
            image = np.array(img)
            # 获取图片的通道数，如果图片为多通道（如RGB）则获取，否则默认为1（如灰度图）
            channel = image.shape[2] if len(image.shape) > 2 else 1
            # 如果图片通道数大于3，只保留前三个通道（如RGB）
            if channel > 3:
                image = image[:, :, :3].copy()
            if resize:
                win_size = cfg.set_win_size
                # 如果win_size 为2560*1440，则不变，否则将图片缩放到对应的16：9大小
                if win_size < 1440:
                    image = cv2.resize(
                        image,
                        None,
                        fx=win_size / 1440,
                        fy=win_size / 1440,
                        interpolation=cv2.INTER_AREA,
                    )
                elif win_size > 1440:
                    image = cv2.resize(
                        image,
                        None,
                        fx=win_size / 1440,
                        fy=win_size / 1440,
                        interpolation=cv2.INTER_LINEAR,
                    )
            # 返回处理后的图片数组
            image = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
            if return_path:
                return image, selected_path
            return image
    except FileNotFoundError:
        log.error(f"未找到图片： {image_path}")
        return (None, None) if return_path else None
    except IOError:
        log.error(f"无法读取图片： {image_path}")
        return (None, None) if return_path else None
    except Exception as e:
        log.error(f"加载图片时发生错误： {e}")
        return (None, None) if return_path else None
```

**Step 2: 添加辅助函数检查默认路径是否存在**

```python
# utils/image_utils.py 添加新函数
@staticmethod
def check_default_path_exists(image_path):
    """检查图片在默认路径（非dark）是否存在"""
    from utils import path_manager

    # 获取所有非dark路径
    active_paths = path_manager.get_active_paths()
    default_paths = [p for p in active_paths if not path_manager.is_path_dark(p)]

    for path in default_paths:
        img_path = os.path.join(f"./assets/images/{path}/{image_path}")
        if os.path.exists(img_path):
            return True, path

    return False, None

@staticmethod
def load_from_specific_path(image_path, target_path, resize=True):
    """从指定路径加载图片"""
    import os
    from PIL import Image
    import cv2
    import numpy as np
    from module.config import cfg

    img_path = os.path.join(f"./assets/images/{target_path}/{image_path}")
    if not os.path.exists(img_path):
        return None

    try:
        with Image.open(img_path) as img:
            image = np.array(img)
            channel = image.shape[2] if len(image.shape) > 2 else 1
            if channel > 3:
                image = image[:, :, :3].copy()
            if resize:
                win_size = cfg.set_win_size
                if win_size < 1440:
                    image = cv2.resize(
                        image,
                        None,
                        fx=win_size / 1440,
                        fy=win_size / 1440,
                        interpolation=cv2.INTER_AREA,
                    )
                elif win_size > 1440:
                    image = cv2.resize(
                        image,
                        None,
                        fx=win_size / 1440,
                        fy=win_size / 1440,
                        interpolation=cv2.INTER_LINEAR,
                    )
            image = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
            return image
    except Exception as e:
        from module.logger import log
        log.error(f"从指定路径加载图片失败: {e}")
        return None
```

**Step 3: 手动测试修改后的功能**

创建测试脚本：
```python
# test_image_utils.py
import sys
import os
import tempfile
import shutil
sys.path.insert(0, '.')
from utils.path_manager import path_manager
from utils.image_utils import ImageUtils

# 创建临时目录结构
temp_dir = tempfile.mkdtemp()
original_cwd = os.getcwd()
os.chdir(temp_dir)

try:
    # 创建测试目录结构（模拟）
    os.makedirs("assets/images/zh_cn_dark/test", exist_ok=True)
    os.makedirs("assets/images/zh_cn/test", exist_ok=True)

    # 创建测试图片（3通道RGB图片，load_image会调用cv2.cvtColor(COLOR_RGB2GRAY)）
    def _create_rgb_image(filepath):
        from PIL import Image
        img = Image.new("RGB", (50, 50), color=(128, 128, 128))
        img.save(filepath)
    _create_rgb_image("assets/images/zh_cn_dark/test/test.png")
    _create_rgb_image("assets/images/zh_cn/test/test.png")

    # 初始化路径管理器
    # 无需传 pic_path_ref，initialize_paths 会自动获取全局 pic_path 并同步
    path_manager.initialize_paths("zh_cn")

    # 测试load_image返回路径
    image, path = ImageUtils.load_image("test/test.png", return_path=True)
    print(f"加载图片路径: {path}")  # 应该返回 zh_cn_dark

    # 测试检查默认路径
    exists, default_path = ImageUtils.check_default_path_exists("test/test.png")
    print(f"默认路径存在: {exists}, 路径: {default_path}")  # 应该返回 True, zh_cn

finally:
    # 切换回原始目录并清理临时目录
    os.chdir(original_cwd)
    shutil.rmtree(temp_dir, ignore_errors=True)
```

运行测试：
```bash
cd C:\Users\12192\AhabAssistantLimbusCompany
python test_image_utils.py
```

**Step 4: 提交更改**

```bash
git add utils/image_utils.py
git commit -m "feat: 修改image_utils支持路径追踪和检查"
```

### Task 3: 修改automation.py实现淘汰逻辑

**Files:**
- Modify: `module/automation/automation.py:490-534`
- Test: 手动验证淘汰逻辑

**Step 1: 修改find_image_element实现淘汰检测**

```python
# module/automation/automation.py 修改find_image_element函数
def find_image_element(
    self,
    target,
    threshold,
    cacheable=True,
    model="clam",
    my_crop=None,
    addtional_stack=0,
):
    """
    在当前截图中查找目标图像的位置
    """
    try:
        if self.memory_protection:
            memory = psutil.virtual_memory()
            # memory.percent 直接返回当前已使用的百分比 (0.0 到 100.0)
            current_percent = memory.percent
            if current_percent > 90:
                log.debug(f"当前系统内存总占用率: {current_percent}%，释放图片缓存")
                self.clear_img_cache()

        from utils import path_manager
        from utils.image_utils import ImageUtils

        # 缓存命中：从缓存中读取模板和路径信息
        if cacheable and target in self.img_cache:
            bbox = self.img_cache[target]["bbox"]
            template = self.img_cache[target]["template"]
            loaded_path = self.img_cache[target]["loaded_path"]
        else:
            # 加载图片并获取路径信息
            template, loaded_path = ImageUtils.load_image(target, return_path=True)
            if template is None:
                log.debug(f"无法加载图片: {target}", stacklevel=addtional_stack + 3)
                return None

            if "assets" in target:
                bbox = ImageUtils.get_bbox(template)
                template = ImageUtils.crop(template, bbox)
            else:
                bbox = None

            # 缓存处理（包含路径信息）
            if cacheable:
                self.img_cache[target] = {"bbox": bbox, "template": template, "loaded_path": loaded_path}

        screenshot = np.array(self.screenshot)
        if my_crop:
            screenshot = ImageUtils.crop(screenshot, my_crop)

        center, matchVal = ImageUtils.match_template(screenshot, template, bbox, model)  # 匹配模板
        log.debug(
            f"目标图片：{target.replace('./assets/images/', '')}, 路径: {loaded_path}, 相似度：{matchVal:.2f}, 目标位置：{center}",
            stacklevel=addtional_stack + 3,
        )

        # 检查匹配结果
        if isinstance(matchVal, (int, float)) and not math.isinf(matchVal) and matchVal >= threshold:
            return center
        else:
            # 匹配失败，检查是否需要淘汰dark路径
            # 仅当 dynamic_optimization 为 True 且尚未淘汰时才进入 default 回退逻辑
            if (path_manager.dynamic_optimization
                and not path_manager.is_dark_eliminated
                and loaded_path
                and path_manager.is_path_dark(loaded_path)):
                # 检查默认路径是否存在
                default_exists, default_path = ImageUtils.check_default_path_exists(target)
                if default_exists:
                    # 尝试使用默认路径的图片进行匹配
                    default_template = ImageUtils.load_from_specific_path(target, default_path)
                    if default_template is not None:
                        if "assets" in target:
                            default_bbox = ImageUtils.get_bbox(default_template)
                            default_template = ImageUtils.crop(default_template, default_bbox)
                        else:
                            default_bbox = None

                        # 使用默认模板重新匹配
                        default_center, default_matchVal = ImageUtils.match_template(
                            screenshot, default_template, default_bbox, model
                        )

                        log.debug(
                            f"尝试默认路径图片：{target}, 路径: {default_path}, 相似度：{default_matchVal:.2f}",
                            stacklevel=addtional_stack + 3,
                        )

                        # 如果默认路径匹配成功，淘汰dark路径
                        if (isinstance(default_matchVal, (int, float)) and
                            not math.isinf(default_matchVal) and
                            default_matchVal >= threshold):

                            if path_manager.eliminate_dark_paths():
                                log.info(f"检测到dark路径失败但default路径成功，淘汰所有dark路径，图片: {target}")
                                self.clear_img_cache()  # 清除当前实例的缓存，避免使用过期的dark图片

                            return default_center
    except Exception as e:
        log.error(f"寻找图片失败:{e}")
    return None
```

**Step 2: 缓存清理说明**

`clear_img_cache` 方法本身**不需要修改**，保持原样。缓存清理由 `find_image_element` 在确认淘汰成功后，直接对 `self` 调用 `self.clear_img_cache()`，避免与全局 `auto` 单例硬耦合。

**Step 3: 手动测试淘汰逻辑**

创建模拟测试：
```python
# test_elimination.py
import sys
sys.path.insert(0, '.')
from module.automation.automation import Automation
from utils.path_manager import path_manager
import numpy as np

# 模拟测试环境
class MockScreen:
    screenshot = np.random.rand(100, 100) * 255

class MockConfig:
    set_win_size = 1080
    memory_protection = False
    screenshot_interval = 0.85

# 初始化
path_manager.initialize_paths("zh_cn")
print("初始路径:", path_manager.get_active_paths())

# 创建模拟的automation实例（简化）
auto = Automation.__new__(Automation)
auto.screenshot = MockScreen.screenshot
auto.img_cache = {}
auto.model = "clam"

# 模拟find_image_element逻辑（简化版）
def mock_find_image(target, dark_success=False, default_success=True):
    print(f"\n测试图片: {target}")
    print(f"模拟: dark匹配成功={dark_success}, default匹配成功={default_success}")

    if not dark_success and default_success:
        # 触发淘汰
        if path_manager.eliminate_dark_paths():
            print("触发dark路径淘汰")

    return default_success

# 测试淘汰触发
mock_find_image("test.png", dark_success=False, default_success=True)
print("淘汰后路径:", path_manager.get_active_paths())

# 测试不会重复淘汰
mock_find_image("test2.png", dark_success=False, default_success=True)
print("二次淘汰后路径:", path_manager.get_active_paths())  # 应该不变
```

运行测试：
```bash
cd C:\Users\12192\AhabAssistantLimbusCompany
python test_elimination.py
```

**Step 4: 提交更改**

```bash
git add module/automation/automation.py
git commit -m "feat: 在find_image_element中添加dark路径淘汰逻辑"
```

### Task 4: 修改script_task_scheme.py移除主题检测

**Files:**
- Modify: `tasks/base/script_task_scheme.py:305-361`
- Test: 验证脚本启动流程

**Step 1: 移除主题检测逻辑，改用路径管理器**

完全删除 `script_task_scheme.py` 第305-361行（旧路径初始化 + 主题检测逻辑），替换为：

```python
# tasks/base/script_task_scheme.py 删除第305-361行，替换为：

# 初始化路径管理器（传递pic_path引用实现自动同步）
from utils import path_manager, pic_path
path_manager.initialize_paths(cfg.language_in_game, pic_path_ref=pic_path, config=cfg)
log.info(f"初始化图片路径: {pic_path}")

# 如果是战斗中，先处理战斗
if cfg.resonate_with_Ahab:
    Resonate_with_Ahab()

get_reward = None
if auto.click_element("battle/turn_assets.png", take_screenshot=True):
    get_reward = battle.fight()
```

**删除的内容包括：**
- `pic_path.clear()` 和 `pic_path.extend([...])` 旧路径初始化（第305-309行）
- `theme_detected = None` 和 `for loop_idx in range(2):` 主题检测循环（第312-354行）
- `if theme_detected == "dark":` 条件块（第356-361行）

**注意：** `script_task_scheme.py` 中不再需要手动 `pic_path.clear()/extend()`，PathManager 通过 `pic_path_ref` 自动同步全局 `pic_path`。

**⚠️ 兼容性说明：现有直接修改 `pic_path` 的模块**

以下模块在运行时直接修改全局 `pic_path` 来调整图片搜索优先级，此行为**必须继续生效**：

- **`tasks/tools/infinite_battle.py:58-63`**：根据语言 `insert(0, "zh_cn")` 或 `pop(0)` + `insert(0, "en")` 确保语言路径优先
- **`tasks/tools/production_module.py:50-51`**：`insert(0, "zh_cn")` 确保中文路径优先

其能正常工作的前提是 `load_image()` 仍然从全局 `pic_path` 读取路径顺序（而非 `path_manager.get_active_paths()`）。方案已确保这一点：PathManager 通过 `pic_path_ref` 引用同步 `pic_path`，而 `load_image` 始终通过 `from utils import pic_path` 读取当前路径列表。因此外部模块对 `pic_path` 的直接修改与 PathManager 的淘汰操作都能正确反映到图片加载中。

> **后续优化建议**：将 `infinite_battle.py` 和 `production_module.py` 的路径操作迁移为 PathManager API 调用，例如 `path_manager.prioritize_language("zh_cn")`，集中管理路径状态。但这不在本次变更范围内。

**Step 3: 测试脚本启动**

创建简单启动测试：
```python
# test_script_start.py
import sys
sys.path.insert(0, '.')
from tasks.base.script_task_scheme import script_task
from module.config import cfg

# 模拟配置
cfg.language_in_game = "zh_cn"
cfg.resonate_with_Ahab = False
cfg.set_windows = False

# 测试路径初始化逻辑
print("测试路径初始化...")
# 注意：实际测试需要更复杂的环境模拟
```

**Step 4: 提交更改**

```bash
git add tasks/base/script_task_scheme.py
git commit -m "refactor: 移除主题检测逻辑，改用路径管理器初始化"
```

### Task 5: 添加配置选项和文档

**Files:**
- Modify: `assets/config/config.example.yaml`
- Create: `docs/动态路径淘汰机制说明.md`
- Test: 验证配置读取

**Step 1: 添加配置选项**

```yaml
# assets/config/config.example.yaml 在合适位置添加
# 路径管理设置
dynamic_path_optimization: True  # 启用动态路径优化（设为False则完全禁用运行时 default 回退匹配和 dark 路径淘汰）
```

**Step 2: PathManager 配置读取**

配置读取逻辑已集成到 Task 1 的 `PathManager.initialize_paths` 中，通过 `config` 参数读取 `dynamic_path_optimization` 配置项。无需额外修改。

**Step 3: 修改script_task_scheme.py传递配置**

已在 Task 4 Step 1 中完成，调用方式为：

```python
from utils import path_manager, pic_path
path_manager.initialize_paths(cfg.language_in_game, pic_path_ref=pic_path, config=cfg)
```

**Step 4: 创建说明文档**

```markdown
# 动态路径淘汰机制说明

## 功能概述
本功能实现了运行时动态路径淘汰机制，当检测到dark主题图片匹配失败而default主题图片匹配成功时，自动淘汰所有dark路径。

## 工作流程
1. 脚本启动时，根据游戏语言初始化包含所有dark和default的路径
   - 中文: `["zh_cn_dark", "en_dark", "share_dark", "zh_cn", "en", "share"]`
   - 英文: `["en_dark", "share_dark", "en", "share"]`
2. 图片识别时，按路径顺序尝试（dark路径优先）
3. 当dark路径图片匹配失败（相似度低于阈值），但同图片的default路径匹配成功时
4. 触发淘汰机制，移除所有dark路径
5. 后续识别使用优化后的路径列表

## 配置选项
- `dynamic_path_optimization`: 是否启用动态路径优化（默认: True）

## 优势
1. 避免一次性主题检测失败导致的路径错误
2. 运行时自适应，处理剧情动画等无UI场景
3. 单张图片触发，响应迅速
4. 保持default路径作为兜底，确保基本功能

## 注意事项
- 淘汰是永久性的（单次运行内），重启后重置
- 需要确保assets/images目录下有完整的图片资源
- 首次运行可能因尝试dark路径而稍慢
```

**Step 5: 测试配置读取**

```python
# test_config.py
import sys
sys.path.insert(0, '.')
from utils.path_manager import path_manager
from module.config import cfg

# 测试配置传递
print("测试配置读取...")
# 需要实际配置文件
```

**Step 6: 提交更改**

```bash
git add assets/config/config.example.yaml docs/动态路径淘汰机制说明.md utils/path_manager.py tasks/base/script_task_scheme.py
git commit -m "feat: 添加动态路径优化配置选项和文档"
```

### Task 6: 集成测试和验证

**Files:**
- Create: `test_integration.py`
- Test: 完整功能集成测试

**Step 1: 创建集成测试脚本**

```python
# test_integration.py
"""
动态路径淘汰机制集成测试
"""
import sys
import os
sys.path.insert(0, '.')

from utils.path_manager import path_manager
from utils.image_utils import ImageUtils
from module.automation.automation import Automation
import numpy as np
import tempfile
import shutil

def setup_test_environment():
    """设置测试环境"""
    # 创建临时目录结构
    temp_dir = tempfile.mkdtemp()
    os.makedirs(os.path.join(temp_dir, "assets/images/zh_cn_dark/test"), exist_ok=True)
    os.makedirs(os.path.join(temp_dir, "assets/images/zh_cn/test"), exist_ok=True)
    os.makedirs(os.path.join(temp_dir, "assets/images/en_dark/test"), exist_ok=True)
    os.makedirs(os.path.join(temp_dir, "assets/images/en/test"), exist_ok=True)

    # 创建测试图片（3通道RGB图片，因为load_image会无条件调用cv2.cvtColor(COLOR_RGB2GRAY)）
    def create_test_image(path, value=100):
        img = np.ones((50, 50, 3), dtype=np.uint8) * value
        from PIL import Image
        Image.fromarray(img, mode='RGB').save(path)

    # dark图片（较暗）
    create_test_image(os.path.join(temp_dir, "assets/images/zh_cn_dark/test/test1.png"), 50)
    create_test_image(os.path.join(temp_dir, "assets/images/en_dark/test/test1.png"), 50)

    # default图片（较亮）
    create_test_image(os.path.join(temp_dir, "assets/images/zh_cn/test/test1.png"), 150)
    create_test_image(os.path.join(temp_dir, "assets/images/en/test/test1.png"), 150)

    # 只有default的图片
    create_test_image(os.path.join(temp_dir, "assets/images/zh_cn/test/test2.png"), 150)

    return temp_dir

def test_path_initialization():
    """测试路径初始化"""
    print("=== 测试路径初始化 ===")

    # 测试中文
    path_manager.initialize_paths("zh_cn")
    paths = path_manager.get_active_paths()
    print(f"中文路径: {paths}")
    assert len(paths) == 6, "中文应该6个路径"
    assert "zh_cn_dark" in paths, "应包含zh_cn_dark"

    # 测试英文
    path_manager.initialize_paths("en")
    paths = path_manager.get_active_paths()
    print(f"英文路径: {paths}")
    assert len(paths) == 4, "英文应该4个路径"
    assert "en_dark" in paths, "应包含en_dark"

    print("✓ 路径初始化测试通过")

def test_dark_elimination():
    """测试dark路径淘汰"""
    print("\n=== 测试dark路径淘汰 ===")

    path_manager.initialize_paths("zh_cn")
    print(f"淘汰前路径: {path_manager.get_active_paths()}")

    # 首次淘汰
    result1 = path_manager.eliminate_dark_paths()
    print(f"首次淘汰结果: {result1}, 路径: {path_manager.get_active_paths()}")
    assert result1 == True, "首次淘汰应成功"
    assert len(path_manager.get_active_paths()) == 3, "淘汰后应剩3个路径"
    assert all("_dark" not in p for p in path_manager.get_active_paths()), "不应包含dark路径"

    # 二次淘汰（应无变化）
    result2 = path_manager.eliminate_dark_paths()
    print(f"二次淘汰结果: {result2}, 路径: {path_manager.get_active_paths()}")
    assert result2 == False, "二次淘汰应失败（已淘汰）"

    print("✓ dark路径淘汰测试通过")

def test_image_loading():
    """测试图片加载"""
    print("\n=== 测试图片加载 ===")

    temp_dir = setup_test_environment()
    original_cwd = os.getcwd()
    os.chdir(temp_dir)

    try:
        path_manager.initialize_paths("zh_cn")

        # 测试加载并返回路径
        image, path = ImageUtils.load_image("test/test1.png", return_path=True)
        print(f"加载图片路径: {path}")
        assert path == "zh_cn_dark", "应优先加载dark路径"
        assert image is not None, "应成功加载图片"

        # 测试检查默认路径
        exists, default_path = ImageUtils.check_default_path_exists("test/test1.png")
        print(f"默认路径检查: 存在={exists}, 路径={default_path}")
        assert exists == True, "默认路径应存在"
        assert default_path == "zh_cn", "默认路径应为zh_cn"

    finally:
        os.chdir(original_cwd)
        shutil.rmtree(temp_dir)

    print("✓ 图片加载测试通过")

def main():
    """主测试函数"""
    print("开始动态路径淘汰机制集成测试")

    test_path_initialization()
    test_dark_elimination()
    test_image_loading()

    print("\n✅ 所有集成测试通过")

if __name__ == "__main__":
    main()
```

**Step 2: 运行集成测试**

```bash
cd C:\Users\12192\AhabAssistantLimbusCompany
python test_integration.py
```

期望输出：
```
开始动态路径淘汰机制集成测试
=== 测试路径初始化 ===
中文路径: ['zh_cn_dark', 'en_dark', 'share_dark', 'zh_cn', 'en', 'share']
英文路径: ['en_dark', 'share_dark', 'en', 'share']
✓ 路径初始化测试通过

=== 测试dark路径淘汰 ===
淘汰前路径: ['zh_cn_dark', 'en_dark', 'share_dark', 'zh_cn', 'en', 'share']
首次淘汰结果: True, 路径: ['zh_cn', 'en', 'share']
二次淘汰结果: False, 路径: ['zh_cn', 'en', 'share']
✓ dark路径淘汰测试通过

=== 测试图片加载 ===
加载图片路径: zh_cn_dark
默认路径检查: 存在=True, 路径=zh_cn
✓ 图片加载测试通过

✅ 所有集成测试通过
```

**Step 3: 最终验证和清理**

```bash
# 清理测试文件
rm -f test_path_manager.py test_image_utils.py test_elimination.py test_script_start.py test_config.py test_integration.py

# 验证代码可以导入
python -c "from utils.path_manager import path_manager; from utils.image_utils import ImageUtils; print('导入成功')"
```

**Step 4: 最终提交**

```bash
git add test_integration.py
git commit -m "test: 添加动态路径淘汰机制集成测试"
```

## 执行选项

**计划已完成并保存到 `docs/plans/2026-04-11-dynamic-path-elimination.md`。**

**两个执行选项：**

**1. 子代理驱动（本次会话）** - 我为每个任务派遣新的子代理，任务间进行代码审查，快速迭代

**2. 并行会话（独立）** - 在新工作树中打开新会话，使用executing-plans进行批量执行和检查点

**选择哪种方式？**

**如果选择子代理驱动：**
- **必需子技能：** 使用superpowers:subagent-driven-development
- 保持本次会话
- 每个任务使用新的子代理 + 代码审查

**如果选择并行会话：**
- 指导用户在工作树中打开新会话
- **必需子技能：** 新会话使用superpowers:executing-plans
# 项目图片识别机制文档

## 坐标系统

图片的坐标原点为 **游戏窗口客户区的左上角**。

find_element 返回的坐标是当前游戏窗口客户区坐标，而硬编码的坐标基于 2560×1440 分辨率。因此，在使用find_element返回的坐标时需要**缩放**。

## 图片查找路径机制

1. dark 存在且命中，那么当前主题是dark
2. dark 不存在，default命中，那么当前主题不确定，依然需要检查两种主题
3. dark存在且没命中，default 存在且命中，那么当前主题是default，移除dark路径
4. dark存在且没命中，default 存在但没有命中，那么当前主题无法确定，依然需要检查两种主题


5. zh_cn 存在且命中，那么当前语言是zh_cn
6. zh_cn 不存在，en或share 存在且命中，那么当前语言不能确定
7. zh_cn 存在且没有命中，en或者share存在且命中，那么当前语言是en
8. zh_cn 存在且没有命中，en或share 存在且没有命中，那么当前语言无法确定

主题和语言判断逻辑相互独立：

dark/ zh_cn 不存在，dark/ en 存在但没有命中 = 3 or 4
dark/ zh_cn  存在但没有命中， dark/ en或dark / share 存在且命中 = 1 and 7
dark/ zh_cn 存在但没有命中，dark/ en share存在但没有命中 = 3 or 4

主题判断后：
default：移除dark路径
dark：dark路径匹配成功，不再考虑default
语言判断后：
en：移除zh_cn路径
zh_cn：zh_cn路径匹配成功，不再考虑en和share路径


主题dark，语言zh_cn，首个命中即停止后续匹配
主题default，语言zh_cn，移除dark的三个路径，zh_cn 存在，停止后续匹配
主题dark，语言en，移除dark/zh_cn, default/zh_cn路径，en存在，停止后续匹配
主题default，语言en，移除dark的三个路径 和 default/zh_cn路径，en存在，停止后续匹配


查找到首个匹配文件即停止搜索。

## 图像路径更新机制

启动时根据游戏语言初始化图片搜索路径。

当 `dark` 模板匹配失败会尝试 `default` 模板，若成功则移除 `dark` 路径。

## 图像识别

### 图片模板

在使用 `find_element` 方法时，可以使用两种类型的图片模板：

1. **含黑幕的核心图像元素** - 2560×1440 等大尺寸图片，包含黑幕背景和核心UI元素
2. **仅核心图像元素** - 仅包含核心UI元素的裁剪后图片

e.g.
![window_assets](../../images/share/home/window_assets.png) ![pass_coin](../../images/share/pass/pass_coin.png)

### 图片处理逻辑

| 对比维度 | 黑幕+核心图像元素 | 仅核心图像元素 |
|----------|-------------------|----------------|
| **搜索区域** | 自动选择 bbox(非黑幕区域) | 默认全屏 |

### 图片制作准则

1. **基准分辨率**：所有图片资源steam端**全屏 2560×1440** 分辨率下截取
2. **文件命名**：含黑幕的完整截图使用 `assets` 后缀，只有核心图像的截图不使用 `assets` 后缀
3. **优先使用含黑幕的完整截图**：便于系统自动计算有效区域，适应UI变化

### 参数

- 匹配阈值：`threshold=0.8` (80% 相似度)

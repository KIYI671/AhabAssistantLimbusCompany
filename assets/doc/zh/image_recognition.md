# 项目图片识别机制文档

## 坐标系统

图片的坐标原点为 **游戏窗口客户区的左上角**。

find_element 返回的坐标是当前游戏窗口客户区坐标，而硬编码的坐标基于 2560×1440 分辨率。因此，在使用find_element返回的坐标时需要**缩放**。

## 图片路径与匹配机制

### 路径结构

图片按 **主题**（`dark` / `default`）和 **语言**（`zh_cn` / `en` / `share`）组织，目录层级为 `{主题}/{语言}/`。

搜索优先级如下（按顺序尝试，命中即停）：
`dark/zh_cn` $\to$ `dark/en` $\to$ `dark/share` $\to$ `default/zh_cn` $\to$ `default/en` $\to$ `default/share`

### 主题判定

1. `dark` 存在且命中 → 主题为 `dark`
2. `dark` 不存在，`default` 命中 → 主题无法确定，仍需检查两种主题
3. `dark` 存在但未命中，`default` 存在且命中 → 主题为 `default`，移除 `dark` 路径
4. `dark` 存在但未命中，`default` 存在但未命中 → 主题无法确定

### 语言判定

5. `zh_cn` 存在且命中 → 语言为 `zh_cn`
6. `zh_cn` 不存在，`en` 存在且命中 → 语言为 `en`；仅 `share` 存在且命中 → 语言无法确定
7. `zh_cn` 存在但未命中，`en` 或 `share` 存在且命中 → 语言为 `en`
8. `zh_cn` 存在但未命中，`en` 和 `share` 均未命中 → 语言无法确定

### 判定流程

**主题和语言判断相互独立**，但优先使用已确定的维度缩小搜索范围：

| 场景 | 行为 |
|------|------|
| 主题 `dark`，语言 `zh_cn` | 直接匹配 `dark/zh_cn`，命中即停 |
| 主题 `default`，语言 `zh_cn` | 移除 `dark/*`路径，匹配 `default/zh_cn` |
| 主题 `dark`，语言 `en` | 移除 `dark/zh_cn` 和 `default/zh_cn`，匹配 `dark/en` |
| 主题 `default`，语言 `en` | 移除 `dark/*` 和 `default/zh_cn`，匹配 `default/en` |

主题和语言均已确定时，首个匹配即停止搜索；否则收集所有路径的匹配结果，汇总后进行主题/语言判定，再返回首个命中。

### 并发匹配机制

启动时根据游戏语言初始化图片搜索路径。

匹配并非串行"先 `dark` 后 `default`"：所有存在目标图片的路径**并发匹配**，汇总结果后比较 `dark` 与 `default` 的得分：
- 仅 `dark` 命中 → 主题为 `dark`
- `dark` 存在但未命中、`default` 命中 → 主题为 `default`，移除 `dark` 路径
- 两者均命中 → 比较最高匹配值，差距超过阈值（0.15）时胜出方确定为当前主题

## 图像识别

### 图片模板

在使用 `find_element` 方法时，可以使用两种类型的图片模板：

1. **含黑幕的核心图像元素** - 2560×1440 等大尺寸图片，包含黑幕背景和核心UI元素
2. **仅核心图像元素** - 仅包含核心UI元素的矩形图片

例如：
![window_assets](../../images/default/share/home/window_assets.png) ![pass_coin](../../images/default/share/pass/pass_coin.png)

### 图片处理逻辑

| 对比维度 | 黑幕+核心图像元素 | 仅核心图像元素 |
|----------|-------------------|----------------|
| **搜索区域** | 自动选择 bbox(非黑幕区域) | 默认全屏 |

### 图片制作准则

1. **基准分辨率**：所有图片资源steam端**全屏 2560×1440** 分辨率下截取
2. **文件命名**：含黑幕的完整截图使用 `assets` 后缀，如果只需要bbox用 `bbox` 后缀，只有核心图像的截图不使用 `assets` 后缀
3. **优先使用含黑幕的完整截图**：便于系统自动计算有效区域，适应UI变化

### 参数

- 匹配阈值：`threshold=0.8` (80% 相似度)

### 脚本
- `scripts/match_steam_image.py`：运行游戏，在终端中运行。截图保存在项目根目录下 `screenshot.png`
- `scripts/image_similarity.py`: 检查图片相似度

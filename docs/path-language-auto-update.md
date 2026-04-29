# 图片路径语言自动更新

## 目标

图片识别不再读取用户设置、游戏语言配置文件或注册表来决定图片语言路径。

每次任务启动时，路径管理器都会初始化完整候选路径：

```text
dark/zh_cn
dark/en
dark/share
default/zh_cn
default/en
default/share
```

后续路径收敛只依赖实际图片匹配结果。

`PathManager.initialize_paths(reset_eliminations=False)` 会重新构建路径列表，但保留已淘汰的路径状态。无限战斗等长运行循环使用该模式，避免在战斗间隙重新激活已确认失败的语言或主题路径。

## 查找顺序

`ImageUtils.load_image()` 仍按 `PathManager.pic_path` 顺序加载第一个存在的同名图片。

如果当前加载的是中文路径图片，例如 `dark/zh_cn/foo.png`，但该模板匹配低于阈值，`Automation.find_image_element()` 会尝试同主题下的英文同名图片，例如 `dark/en/foo.png`。

如果英文同名图片匹配成功：

1. 返回英文图片的匹配坐标。
2. 调用 `PathManager.eliminate_zh_cn_paths()`。
3. 从当前运行的图片搜索路径中移除所有 `*/zh_cn` 路径。
4. 将运行期 `cfg.language_in_game` 同步为 `en`。
5. 清空图片缓存，避免继续复用中文模板。

如果中文图片匹配成功，则不会尝试英文图片，并将运行期 `cfg.language_in_game` 同步为 `zh_cn`。

语言同步只影响当前运行期，不写回 `config.yaml`。

## 与主题路径的关系

主题路径淘汰逻辑保持不变：当 `dark/*` 图片匹配失败，而对应 `default/*` 图片匹配成功时，会移除所有 `dark/*` 路径。

语言路径淘汰和主题路径淘汰互相独立，二者都只在实际匹配失败后的复检成功时触发。

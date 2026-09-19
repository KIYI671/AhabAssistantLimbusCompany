<div align="center">

![image](./assets/logo/my_icon.png)

### AhabAssistantLimbusCompany

### FACE THE <font color= #ff0000>S</font><font color= #b40001>I</font><font color= #690001>N</font>,SAVE THE <font color=#ffd700>E</font><font color=#f8da39>.</font><font color=#f1dd72>G</font><font color=#eae0aa>.</font><font color= #e3e3e3>O</font>

---
<br>
<div>
    <a href="https://discord.gg/vUAw98cEVe">
        <img src="https://cdn.simpleicons.org/discord" alt="Discord" width="24" height="24">
    </a>
</div>
<div>
    <img alt="version" src="https://img.shields.io/github/v/release/KIYI671/AhabAssistantLimbusCompany?color=%239c080b&style=flat-square">
    <img alt="download" src="https://img.shields.io/github/downloads/KIYI671/AhabAssistantLimbusCompany/total?style=flat-square&color=4096d8">
</div>
<div>
    <img alt="language" src="https://img.shields.io/badge/Language-Python-blue">
    <img alt="platform" src="https://img.shields.io/badge/platform-Windows-blue?style=flat-square&color=4096d8">
</div>

**简体中文** | [English](assets/doc/en/README_EN.md)

遇到问题，请在提问前查看：[FAQ](assets/doc/zh/FAQ.md)

  ---

本项目为非科班出身、非计算机从业人员心血来潮的作品

是一个掺杂了第三方项目、基于图像识别和文字识别技术实现的

手游Limbus Company的PC端小助手

可以帮助玩家自动完成日常任务、镜牢挑战等操作，一键护肝（~~除了写代码的~~）

此项目旨在帮助大家减少Limbus游玩过程中反复枯燥的部分，从而更好地享受里面精彩的剧情、演出和机制

</div>

## 功能简介

- **自动日常**：自动刷经验本、纽本，领取日常/周常奖励，领取邮件
- **狂气换体**：自动识别并使用狂气换体力，自动合成脑啡肽模块（饼）
- **自动镜牢**：全自动坐牢
  - 支持多队伍轮换、循环战斗
  - 支持自定义队伍饰品体系选择
  - 支持镜牢主题包根据权重自动识别筛选
  - 配置智能路线规划（优先选择事件节点）

- 仿MAA式GUI
- 自动检查版本更新
  - 自动下载最新版本
  - 自动执行更新操作
- 所见即所得，操作简单
- 支持多分辨率游戏窗口执行
- 支持在任务完成后，执行自动关闭游戏或关机等操作

### 特色功能

- 自动选队，有两种模式：
  - 根据OCR获取队伍名称选择队伍（必须保持初始队伍名称，如【TEAM #1】）
  - 根据队伍序号选择队伍
- 镜牢根据权重自动选择主题包
- 支持使用英语（EN），简体中文（zh_cn）作为游戏语言时运行
- 客制化的镜牢刷取体验

关于镜牢配队的自定义设置和流程加速，请见[AALC进阶使用指南](/assets/doc/zh/Custom_setting.md)

---

## 下载方式

点击[Releases](https://github.com/KIYI671/AhabAssistantLimbusCompany/releases)
并下载最新版中命名为【AALC-Vx.x.x】的文件，解压后运行AALC.exe即可。

因为技术力不足，还搞了GUI和使用第三方OCR，所以导致文件比较大

**注意**：Release基于x86_64架构，Windows系统；另有macOS（Apple Silicon / arm64）版本，见下方说明。对于Arm架构Linux设备（如树莓派），RISCV架构和Intel芯片的Mac暂无Release。如果需要在非支持的平台上运行AALC请参考**源码运行**和**构建指南**章节进行操作，也欢迎作为开发者提交PR进行多平台适配。

> **macOS 打包版（Apple Silicon）**：下载 Release 里命名为 `AALC_<版本>_macos_arm64.zip` 的文件，解压得到 `AALC.app`。
>
> 1. 把 `AALC.app` 放到 `/Applications` 或 `~/Applications` 等**有写入权限**的目录。
> 2. **首次打开前**在「终端」执行一次（路径按实际位置替换）：`xattr -dr com.apple.quarantine /Applications/AALC.app`。
>    打包版没有签名与公证，不去掉下载隔离标记会被 Gatekeeper 拦下；直接右键「打开」虽然能启动，但系统会以只读的随机路径运行应用（App Translocation），数据无法保存。
> 3. 打开 AALC.app，在 系统设置 → 隐私与安全性 里给 **AALC.app** 授予屏幕录制与辅助功能权限（前台模式截图/输入、PlayCover 键盘注入需要）。
> 4. 配置、日志、图片资源都在数据目录 `~/Library/Application Support/AALC`（首次启动时从应用内复制过去，约 90 MB）；因此**替换 AALC.app 升级不会丢配置**。程序内检查到新版本后会把更新包下载到该目录的 `update_temp` 并在访达里定位，手动解压替换 `AALC.app` 即可（macOS 暂不提供自动更新器）。
> 5. 使用模拟器（ADB）或 PlayCover 需要 `adb`：`brew install android-platform-tools`；打包版已把 `/opt/homebrew/bin`、`/usr/local/bin` 加入 PATH。

> macOS（Apple Silicon/Intel）：自源码运行已可用（GUI 正常）。依赖 Windows API 的能力在 macOS 上不可用：后台点击/截图（win32）、窗口句柄管理、HDR 检测、计划任务、Toast 通知与管理员提权。安装依赖时 `uv sync` 或 `pip install -r requirements.txt` 会自动跳过 Windows 专用包（pywin32/pyuac/windows-toasts）。首次运行 GUI 时请在 系统设置 → 隐私与安全性 中为终端授予屏幕录制与辅助功能权限，前台模式（pyautogui）的输入与截图才可生效。
>
> **macOS 上运行自动化：使用模拟器后台模式**。在 设置 → 模拟器设置 中开启「使用模拟器」，类型选择「其他模拟器」(10)，并按模拟器的实际 ADB 地址填写主机/端口（本机一般为 `127.0.0.1:16384`（MuMu 多开按实例 +32 递增）或 `127.0.0.1:5555`，可用 `adb devices` 确认）。截图与输入均走 ADB（screencap / minitouch），与 Windows 行为一致。MuMu(0)/BlueStacks 5(1) 为 Windows 桌面驱动，macOS 上不可用，请选择「其他」。模拟器需手动启动并保持 ADB 开启，脚本不会自动拉起模拟器进程。
>
> 也可走 **PlayCover** 直连 iOS 版游戏：在 PlayCover 中启用 MaaTools（游戏窗口标题显示 `[localhost:1717]`），AALC 类型选「PlayCover (MaaTools)」(20)、主机 `127.0.0.1`、端口 `1717`，截图与触摸经 MaaTools TCP 协议直接作用于游戏窗口，无需 Android 模拟器。键盘方面（MaaTools 协议没有键盘指令）：**Enter / P / ESC** 通过 `CGEventPostToPid` 直接注入游戏进程，游戏不必在前台、也不影响你同时用电脑；这需要在 系统设置 → 隐私与安全性 → 辅助功能 中勾选**运行 AALC 的程序**（源码运行即终端，打包版即 `AALC.app`），未授权时这三个键自动回退为触摸操作。方向键与文本输入仍走触摸兜底（见使用说明）。

---

## 使用说明

### [堂吉诃德都能学会的操作方法](/assets/doc/zh/How_to_use.md)

### 其他说明

在脚本执行过程可以使用 **CTRL+Q** 按键终止脚本进程（此操作可能导致脚本再次启动时出现问题，可以通过重启脚本程序解决）

同时 **ALT+P** 可以暂停脚本，**ALT+R** 可以恢复脚本

以上快捷键均可以通过设置界面内的**快捷键设置**选项卡更改

其他没什么需要说明的，所见即所得

如果发现问题，可以通过 [Issue](https://github.com/KIYI671/AhabAssistantLimbusCompany/issues) 反馈

当然也欢迎提交 [PR](https://github.com/KIYI671/AhabAssistantLimbusCompany/pulls)

### 主题包权重设置

运行一次脚本后，会自动创建一个 **_“theme_pack_list.yaml”_** 文件，该文件用于设置主题包的权重</br>
使用记事本或者其他文本编辑器打开后，可以仿照格式自行配置主题包权重，或自行添加主题包识别文字

#### 修改流程

- 先运行一次AALC.exe（新用户）
- AALC文件夹下出现theme_pack_list.yaml文件
- 修改theme_pack_list.yaml文件
- 修改后重新启动AALC

文件格式参考以下图片所示

![image](/assets/doc/image/theme_list.png)

### 后台运行

- **需要后台运行或多显示器可以尝试 [远程本地多用户桌面](https://www.bilibili.com/read/cv24286313/)**
- **以上教程中所有相关文件：[下载链接](https://github.com/CHNZYX/asu_version_latest/releases)**
- **相关文件也可以前往教程作者 [主页-动态页](https://space.bilibili.com/26715033/dynamic) 从置顶中获取**

## 注意事项

- 建议使用 1920 \* 1080 和 2160 \* 1440 的分辨率运行</br> 未测试屏幕小于1920 * 1080的情况，不太建议在小于该分辨率下使用
- **请将设置-图像中的材质质量和渲染比例设为高，普通FPS和战斗FPS均设为60，后处理设为关闭**以便于软件进行识别。若设备性能无法满足也请尽量将
  **渲染比例设为高**，否则软件识别可能存在困难。
- 游戏程序将在脚本启动后，被设置为窗口模式，中间如果出现切换全屏后又退出的行为，是正常的行为，无需担心
- 如果您启动了 steam 或其他软件的性能展示功能，应尽量避免遮盖游戏画面，否则可能导致脚本使用过程出现问题
- 脚本支持使用简体中文作为游戏语言时运行，但仅支持使用零协的中文本地化语言包与字体

---

## 声明

本软件开源、免费，仅供学习交流使用。

若您遇到商家使用本软件进行代练并收费，可能是设备与时间等费用，产生的问题及后果与本软件无关。

配置了获取管理员权限的代码，是为了确保运行顺利

该项目除了检查更新与公告展示功能外，纯离线运行

软件图标素材来源网图，不属于 AGPL v3 协议开源的内容，如有侵权，请及时联系作者删除

部分图像与音频素材来自 [边狱巴士中文WIKI](https://limbuscompany.huijiwiki.com/wiki/)
与 [月海伦娜](https://yuehailunna.lofter.com/) ，应要求进行声明

用户在使用过程中需自行遵守相关平台的使用规则与服务条款。因使用本软件可能导致的游戏账号封禁、违规行为等一切后果，作者概不负责。用户需对自身行为负责，并承担使用本软件可能带来的所有风险。

---

## 图示样例

（图片仅供参考，还请以实例为准）

### 开始界面

![image](/assets/doc/image/README1_zh_CN.png)

### 镜牢队伍设置界面

![image](/assets/doc/image/README2_zh_CN.png)

---

## 致谢

### 单独致谢

AALC的项目离不开以下开源项目的帮助

| 项目      | 链接                                                                                | -                                         |
|---------|-----------------------------------------------------------------------------------|-------------------------------------------|
| LALC    | [LixAssistantLimbusCompany](https://github.com/HSLix/LixAssistantLimbusCompany)   | 感谢大佬的开源，让我能通过一步步跟进重写大佬的项目，从而学习、开始自己的项目    |
| OCR文字识别 | [PaddleOCR-json](https://github.com/hiroi-sora/PaddleOCR-json)                    | 没有它就没有自动识别队伍、自动识别镜牢主题包的功能                 |
| 图形界面组件库 | [PyQt-Fluent-Widgets](https://github.com/zhiyiYo/PyQt-Fluent-Widgets)             | 虽然只是用到了基础的部件，没怎么开发潜力，但是基础的部件已经让GUI的美观性UP了 |
| 三月七小助手  | [March7thAssistant](https://github.com/moesnow/March7thAssistant)                 | 从大佬这里学到了挺多                                |
| BAAS    | [blue_archive_auto_script](https://github.com/pur1fying/blue_archive_auto_script) | 从大佬这里学习了模拟器相关代码                           |

[ChineseFont.ttf](./assets/app/fonts/ChineseFont.ttf)文件来源于[更纱黑体](https://github.com/be5invis/Sarasa-Gothic)，该部分代码遵循 **SIL Open Font License** 许可证。

### 统一致谢

直接或间接参与到本软件开发的所有人员

包括在网络上分享各种教程的大佬们

还有开源自己代码的巨佬们！

---

## 贡献者

感谢以下开发者对 AALC 作出的卓越贡献：

<a href="https://github.com/KIYI671/AhabAssistantLimbusCompany/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=KIYI671/AhabAssistantLimbusCompany" />
</a>

## 未来计划

- [ ] 运行结束后统计获取的通行证等级和经验卡数量、纽数量
- [ ] 自适应窗口位置，可以不用左上角
- [ ] 将运行期间的统计生成为excel文件或图表，提高可阅读性
- [ ] 完善代码函数注释文档
- [ ] 针对主题包配置提供GUI
- [ ] 持续修复BUG
- [ ] ……

---

## 源码运行

如果你是完全不懂的小白，请通过上面的方式下载安装，不用往下看了。

### 使用 uv (推荐)

```ps1
# 克隆仓库
git clone https://github.com/KIYI671/AhabAssistantLimbusCompany
cd AhabAssistantLimbusCompany
# 通过uv下载依赖, uv工具自行下载
uv sync --frozen
uv run main.py

# 更新
git pull
```

> 终端日志默认输出 DEBUG 级别，跑起来比较吵。用环境变量调级别（进程启动前设置）：
> `AALC_LOG_LEVEL=INFO uv run main.py`（可选 DEBUG/INFO/WARNING/ERROR/CRITICAL 或数字）。
> `logs/debugLog.log` 仍默认记录 DEBUG，便于反馈问题时附日志；需要一起降噪时再加
> `AALC_LOG_FILE_LEVEL=INFO`。

### 使用 pip (不包含dev工具)

```ps1
# 克隆仓库
git clone https://github.com/KIYI671/AhabAssistantLimbusCompany
cd AhabAssistantLimbusCompany
# 请使用版本高于 3.13 的 Python 二进制程序 (含GIL)
pip install -r requirements.txt
python main.py

# 更新
git pull
```

---

## 构建指南

- 参考 [构建指南](assets/doc/zh/build_guide.md)

---

## 参与开发

- 参与程序[开发](assets/doc/zh/develop_guide.md)（施工中）
- 多语言 (i18n)：参考 [多语言支持](assets/doc/zh/translateGuide.md)

---

## 最后

如果你觉得该软件对你有帮助，请点个Star吧。

希望有大佬对这个项目进行一波指点或者优化，或者更进一步一起完善这个项目。

希望这个软件能帮助大家减少Limbus游玩过程中反复乏味的部分，享受里面精彩的剧情、演出和机制。

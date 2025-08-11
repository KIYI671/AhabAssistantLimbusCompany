<div align="center">

![image](./assets/logo/my_icon.png)

### AhabAssistantLimbusCompany

### FACE THE <font color= #ff0000>S</font><font color= #b40001>I</font><font color= #690001>N</font>,SAVE THE <font color=#ffd700>E</font><font color=#f8da39>.</font><font color=#f1dd72>G</font><font color=#eae0aa>.</font><font color= #e3e3e3>O</font>

---

<br>
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

- 仿MAA式GUI （~~做得很菜~~）
- 所见即所得，操作简单
- 支持多分辨率游戏窗口执行
  
### 特色功能

- 自动选队（必须保持初始队伍名称，如【TEAM #1】）
- 镜牢根据权重自动选择主题包
- 支持使用英语（EN），简体中文（zh_cn）作为游戏语言时运行
- 自动远离镜牢饰品：白棉花

---

## 下载方式

点击[Releases](https://github.com/KIYI671/AhabAssistantLimbusCompany/releases)并下载最新版中命名为【AALC-Vx.x.x】的文件，解压后运行AALC.exe即可。

因为技术力不足，还搞了GUI和使用第三方OCR，所以导致文件比较大

---

## 使用说明

### [堂吉诃德都能学会的操作方法](/assets/doc/zh/How_to_use.md)

### 其他说明

在脚本执行过程可以使用 **CTRL+Q** 按键终止脚本进程（此操作可能导致脚本再次启动时出现问题，可以通过重启脚本程序解决）

同时 **ALT+P** 可以暂停脚本，**ALT+R** 可以恢复脚本

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

- 暂时只建议使用 1920 * 1080 和 2160 * 1440 的分辨率运行</br> 未测试屏幕小于1920 * 1080的情况，不太建议在小于该分辨率下使用
- **请将设置-图像中的材质质量和渲染比例设为高，普通FPS和战斗FPS均设为60，后处理设为关闭**以便于软件进行识别。若设备性能无法满足也请尽量将**渲染比例设为高**，否则软件识别可能存在困难。
- 游戏程序将在脚本启动后，被设置为窗口模式，中间如果出现切换全屏后又退出的行为，是正常的行为，无需担心
- 如果您启动了 steam 或其他软件的性能展示功能，应尽量避免遮盖游戏画面，否则可能导致脚本使用过程出现问题
- 脚本支持使用简体中文作为游戏语言时运行，但仅支持使用零协的中文本地化语言包与字体
- 在使用软件较长时间后请定期清理程序文件夹下的 `logs` 文件夹，避免占用过多空间

---

## 声明

本软件开源、免费，仅供学习交流使用。

若您遇到商家使用本软件进行代练并收费，可能是设备与时间等费用，产生的问题及后果与本软件无关。

配置了获取管理员权限的代码，是为了确保运行顺利

该项目除了检查更新功能外，纯离线运行

软件图标素材来源网图，不属于 AGPL v3 协议开源的内容，如有侵权，请及时联系作者删除

部分图像与音频素材来自 [边狱巴士中文WIKI](https://limbuscompany.huijiwiki.com/wiki/) 与 [月海伦娜](https://yuehailunna.lofter.com/) ，应要求进行声明

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

| 项目      | 链接                                                                              | -                                         |
|---------|---------------------------------------------------------------------------------|-------------------------------------------|
| LALC    | [LixAssistantLimbusCompany](https://github.com/HSLix/LixAssistantLimbusCompany) | 感谢大佬的开源，让我能通过一步步跟进重写大佬的项目，从而学习、开始自己的项目    |
| OCR文字识别 | [PaddleOCR-json](https://github.com/hiroi-sora/PaddleOCR-json)                  | 没有它就没有自动识别队伍、自动识别镜牢主题包的功能                 |
| 图形界面组件库 | [PyQt-Fluent-Widgets](https://github.com/zhiyiYo/PyQt-Fluent-Widgets)           | 虽然只是用到了基础的部件，没怎么开发潜力，但是基础的部件已经让GUI的美观性UP了 |
| 三月七小助手  | [March7thAssistant](https://github.com/moesnow/March7thAssistant)               | 从大佬这里学到了挺多                                |


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
- [ ] 重构GUI
- [ ] 实现软件对新版本压缩包进行自动更新功能
- [ ] 修复自动战斗bug和主题包无法自设定bug
- [ ] 增加对狂气换体力的葛朗台模式的支持
- [ ] 运行结束后统计获取的通行证等级和经验卡数量、纽数量
- [ ] 自适应窗口位置，可以不用左上角
- [ ] 提高镜牢自定义自由度，开局饰品、是否只激进合成、合成四级后行为、第二体系等等等等
- [ ] 将运行期间的统计生成为excel文件或图表，提高可阅读性
- [ ] 持续修复BUG
- [ ] ……

---

## 源码运行

如果你是完全不懂的小白，请通过上面的方式下载安装，不用往下看了。

```cmd
# Installation (using venv is recommended)
git clone https://github.com/KIYI671/AhabAssistantLimbusCompany
cd AhabAssistantLimbusCompany
pip install -r requirements.txt
python main.py

# Update
git pull
```

---

## 构建指南

- 参考 [构建指南](assets/doc/zh/build_guide.md)

---

## 最后

如果你觉得该软件对你有帮助，请点个Star吧。

希望有大佬对这个项目进行一波指点或者优化，或者更进一步一起完善这个项目。

希望这个软件能帮助大家减少Limbus游玩过程中反复乏味的部分，享受里面精彩的剧情、演出和机制。
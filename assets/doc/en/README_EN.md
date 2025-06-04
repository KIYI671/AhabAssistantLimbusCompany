<div align="center">

![image](/assets/logo/my_icon.png)

<br>

# AhabAssistantLimbusCompany

## FACE THE <font color= #ff0000>S</font><font color= #b40001>I</font><font color= #690001>N</font>,SAVE THE <font color=#ffd700>E</font><font color=#f8da39>.</font><font color=#f1dd72>G</font><font color=#eae0aa>.</font><font color= #e3e3e3>O</font>

<br>
<div>
    <img alt="version" src="https://img.shields.io/github/v/release/KIYI671/AhabAssistantLimbusCompany?color=%239c080b&style=flat-square">
    <img alt="download" src="https://img.shields.io/github/downloads/KIYI671/AhabAssistantLimbusCompany/total?style=flat-square&color=4096d8">
</div>
<div>
    <img alt="language" src="https://img.shields.io/badge/Language-Python-blue">
    <img alt="platform" src="https://img.shields.io/badge/platform-Windows-blue?style=flat-square&color=4096d8">
</div>

  [简体中文](/README.md) | **English**

  This project is the brainchild of a non-computer professional.

  It is a third-party project based on image recognition and text recognition technology
  
  A PC assistant for the mobile game Limbus Company
  
  It can help players automatically complete daily tasks, mirror dungeon challenges and other operations, one-click liver protection 

  This project aims to help you reduce the repetitive and boring parts of Limbus's gameplay, so that you can better enjoy the exciting story, performances, and mechanics inside


<br>



</div>

## Function Introduction

- **Automatic Daily**: Automatically swipe experience books, new books, receive daily/weekly rewards, and receive emails
- **LUNACY to physical**: Automatically identify and use LUNACY for physical strength, and automatically synthesize enkephalin module (cake)
- **Automatic Mirror Dungeons**: fully automatic Dungeons time
  - Support multi-team rotation and round-robin battles
  - Supports custom team accessories system selection
  - Support mirror dungeon theme pack to automatically identify and filter based on weight
  - Configure intelligent route planning (prioritize event nodes)

- Imitation of MAA style GUI 
- What You See Is What You Get.
- Supports multi-resolution window execution.
  
### Special Features

- Automatic team selection (must keep initial team name, e.g. [TEAM #1])
- The Mirror Dungeon automatically selects theme packs based on weights
- Supports running with English (EN) and Chinese Simplified (zh_cn) as the game language
- Automatically stay away from the mirror prison ornament: white cotton

---

## How to download

Click [Releases](https://github.com/KIYI671/AhabAssistantLimbusCompany/releases) and download the file called 【AALC-Vx.x.x】 in the latest version, unzip it and run AALC.exe.

Because of the lack of technical power, I also engaged in GUI and used third-party OCR, so the file size is relatively large

---

## Instructions for use

### [A maneuver that even Don Quixote could learn](/assets/doc/en/How_to_use_EN.md)

### Other Notes

During script execution you can use **CTRL+Q** keys to terminate the script process (this may cause problems when the script is restarted, which can be solved by restarting the script program).

At the same time **ALT+P** can pause the script, **ALT+R** can resume the script

There is nothing to explain, what you see is what you get.

If you find any problems (except for the team numbering problem below), you can report them to [Issue](https://github.com/KIYI671/AhabAssistantLimbusCompany/issues).

Of course, you are also welcome to submit [Pull Request](https://github.com/KIYI671/AhabAssistantLimbusCompany/pulls)

### Theme package weight setting

When the script is run once, a _"theme_pack_list.yaml"_ file is automatically created, which is used to set the weight of the theme package</br>
After opening it with Notepad or other text editors, you can configure the weight of the theme package according to the format, or add the theme package to recognize the text

#### Modify the process
- Run the AALC.exe once first (for new users)
- A theme_pack_list.yaml file appears in the AALC folder
- Modify theme_pack_list.yaml file
- Restart AALC after modification

The file format is shown in the following picture.

![image](/assets/doc/image/theme_list.png)


### Running in the background

- This section is currently unsupported for this language.
- **Need to run in the background or have multiple monitors try [Remote Local Multi-User Desktop](https://www.bilibili.com/read/cv24286313/)**
- **All related files in the above tutorials: [download link](https://github.com/CHNZYX/asu_version_latest/releases)**
- **Related files can also be obtained by going to the tutorial author's [Home - Dynamic Page](https://space.bilibili.com/26715033/dynamic) from the top**.

## Attention!!!

- For the time being, it is only recommended to run at resolutions of 1920 * 1080 and 2160 * 1440</br> If the screen is less than 1920 * 1080, it is not recommended to use it at a resolution smaller than that
- **Please set Material Quality and Render Ratio in Settings-Image to High, Normal FPS and Combat FPS to 60, and Post-Processing to Off** to facilitate software recognition. If the performance of the device cannot be met, please also try to set the **rendering ratio to high**, otherwise the software may have difficulty in recognizing it.
- The game program will be set to window mode after the script starts, and if there is a behavior of switching to the full screen and then exiting in the middle, it is normal behavior, so there is no need to worry
- If you have enabled the performance display feature of Steam or other software, you should try not to obscure the game screen, as this may cause problems with the scripting process
- After using the software for a long time, please clean up the `logs` folder under the program folder regularly to avoid taking up too much space.

---

## Declaration

This software is open source, free of charge, for learning and communication purposes only.

If you encounter merchants use this software to practice on behalf of and charge, may be equipment and time and other costs, problems and consequences have nothing to do with this software.

The code to get administrator privileges is configured to ensure smooth operation

The project runs purely offline, except for checking for update functions

Software icon material from the source of network graphics, does not belong to the AGPL v3 agreement open source content, if any infringement, please contact the author to delete in a timely manner

Some images and audio materials are from [Limbus Company Chinese WIKI](https://limbuscompany.huijiwiki.com/wiki/) and [Yue Helena](https://yuehailunna.lofter.com/), and are disclosed upon request

Users are required to comply with the rules of use and terms of service of the relevant platform in the process of use. Due to the use of this software may lead to the game account ban, illegal behavior and all the consequences, the author is not responsible. Users are responsible for their own behavior and bear all risks that may be brought about by the use of this software.

---


## Sample Diagrams

(The picture is for reference only, please refer to the example)

### Start screen

![image](/assets/doc/image/README1.png)

### The Mirror Dungeon team setup screen 

![image](/assets/doc/image/README2.png)

---
## Acknowledgements

### Individual acknowledgements

The AALC project could not have been possible without the help of the following open source projects

| projects                              | links                                                                           | introduction                                                                                                                                |
|---------------------------------------|---------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------|
| LALC                                  | [LixAssistantLimbusCompany](https://github.com/HSLix/LixAssistantLimbusCompany) | Thanks to the big guy's open source, so I can learn and start my own project by rewriting the big guy's project with step-by-step follow-up |
| OCR Text Recognition                  | [PaddleOCR-json](https://github.com/hiroi-sora/PaddleOCR-json)                  | Without it there would be no auto-recognition of teams, auto-recognition of Mirror Jail theme packs                                         |
| Graphical Interface Component Library | [PyQt-Fluent-Widgets](https://github.com/zhiyiYo/PyQt-Fluent-Widgets)           | Although only used the basic components, not much development potential, but the basic components have made the GUI aesthetics UP           |
| March7thAssistant                     | [March7thAssistant](https://github.com/moesnow/March7thAssistant)               | Learned quite a bit from the big guy here                                                                                                   |


### Uniform acknowledgements
All the people who are directly or indirectly involved in the development of this software

Including the people who shared their tutorials on the web.

And the giants who open-sourced their own code!

---

## Contributors

Thanks to the following developers for their outstanding contributions to AALC:

<a href="https://github.com/KIYI671/AhabAssistantLimbusCompany/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=KIYI671/AhabAssistantLimbusCompany" />
</a>

## Future plans
- [ ] Refactor the GUI
- [ ] Realize the automatic update function of the software for the new version of the zip file.
- [ ] Fix the bug of auto-battle and the bug that theme packs can't be customized.
- [ ] Add support for the Grampian mode
- [ ] Count the number of pass levels after the run.
- [ ] Adapt more window position.
- [ ] Increase the freedom of customization of the mirror dungeon.
- [ ] Generate excel file or chart for stats during runtime to improve readability.
- [ ] Continuously fix bugs
- [ ] ......

---

## Run the source code

If you don't understand it at all, please download and install it through the above method, and you don't have to look down.

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

## Build guide

- References [build guide](build_guide_EN.md)

---

## At last

If you found the software helpful, please click Star.

I hope that there will be a big guy to guide or optimize this project, or further improve this project together.

Hopefully, this app will help you reduce the tedious part of playing Limbus and enjoy the wonderful story, performances, and mechanics inside.
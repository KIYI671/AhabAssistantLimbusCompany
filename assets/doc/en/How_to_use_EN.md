<div align="center">

# How To Use

[简体中文](/assets/doc/zh/How_to_use.md) | **English**

[*项目说明*](/README.md) | [*常见问题*](/assets/doc/zh/FAQ.md) | [*README*](/assets/doc/en/README_EN.md) | [
*FAQ_EN*](/assets/doc/en/FAQ_EN.md)

</div>

<div align="center">

You can use the **CTRL+Q** keys to terminate the script process during script execution (this may cause problems when
the script starts again, which can be solved by restarting the script program)

You can use the **ALT+P** keys to pause the script and the **ALT+R** keys to resume the script

The method of using the simulator is at the [bottom of this article](#simulator-usage)
</div>

---

![image](/assets/doc/image/main_page.png)

#### ① Used to display the current AALC version number, which can be stated when raising ISSUES

#### ② The main page, where all game automation content is set

#### ③ Help documentation (where you are)

#### ④ Some gadgets that are split separately

#### ⑤ Some other settings (including using the team name to identify or choosing the team serial number)

#### ⑥ Click to select/deselect the tasks that will be executed when the script is launched

#### ⑦ Click to jump to the settings page of each task (see below for the explanation of each page)

#### ⑧ A small feature that doesn't matter

#### ⑨ Tap to select all or clear all tasks

#### ⑩ The action to be performed after the script runs

#### ⑪ Click to start executing the script task

#### ⑫ Set the resolution of the window, choose according to the computer configuration (1920*1080 or
2560*1440 is recommended)

#### ⑬ Modify the language used in the game

#### ⑭ More settings

#### ⑮ Log bar

![image](/assets/doc/image/page_01.png)

#### ⑯ Speed up/slow down script operations appropriately according to your computer configuration, and just keep the default under normal circumstances

---

![image](/assets/doc/image/page_1.png)

#### ⑰ Set the formation to be used (you can set the use of team name recognition or select the team serial number in ⑤

#### ⑱ Configure different teams for different EXP levels at different times，If not checked, the team set in ⑰ will be used

#### ⑲ Configure different teams for different Thread levels at different times，If not checked, the team set in ⑰ will be used

---

![image](/assets/doc/image/page_2.png)

---

![image](/assets/doc/image/page_3.png)

#### ⑳ In Dr.Grande mode, when the time to generate the next amount of stamina exceeds 5 minutes and 20 seconds, the Lunacy is converted into Enkephalin

---

![image](/assets/doc/image/page_4.png)

#### ㉑ Check to enable this formation

#### ㉒ The name of the team's notes can be set at ㉖

#### ㉓ When this formation is enabled, the order of mirror dungeons for this formation will be displayed

#### ㉔ Click the gear to enter the detailed settings

#### ㉕ Add a new team

#### ㉖ Set the name of the team's notes

#### ㉗ Delete this team (when there is only one team, it cannot be deleted)

#### ㉘ Check to enable difficult mirror dungeon (only valid for this AALC run, invalid after restart)

#### ㉙ Check to not use weekly reward bonus (only valid for this AALC run, invalid after restart)

#### ㉚ Check to only perform three layers of mirror dungeons, and exit at the fourth layer

#### ㉛ Check to ignore the number of times to be imprisoned below, and automatically execute 9999 times

#### ㉜ If the Mirror Dungeon is a Hard Mirror Dungeon, the reward will not be settled and you will be returned to the main page

#### ㉝ Check to only get one weekly reward bonus per settlement when enabling difficult mirror dungeons

---

![image](/assets/doc/image/page_5.png)

#### When the store policy is "Fuse: Level IV First", the aggressive synthesis option below and the synthesis level IV option of the second system will take effect

---

# Simulator Usage

In the Settings screen, turn on the "Use Emulator" option, and it is recommended to use the MUMU emulator.

### Selection and Acquisition of Emulator Port Number:

#### mumu emulator: menu bar in the upper right corner of the emulator - Problem diagnosis - find "ADB debug port"

- If using the default port number 0, the default initial emulator will be used

#### Other emulators: find the port number according to your own situation, the following are some default ports

- LDPlayer Simulator 5555
- BlueStacks Simulator 5555
- MEmu Simulator 21503
- NOX Simulator 62001 / 59865

### Note：

- Different emulators may have different port numbers, which need to be selected according to the actual situation
- Some emulators may require enabling adb port debugging in settings, such as BlueStacks Simulator, LDPlayer Simulator
- Some emulators may require disabling "Application Keep Alive" in settings, such as MUMU Simulator.(Auto-off
  configured, but may not work)
- When using an emulator, you need to make sure that the emulator's resolution is consistent with the resolution set
  in "Windows Setting" in AALC
- Emulators may cause the script to run slowly, so it is recommended to use a higher configuration computer and give the
  emulator enough memory and CPU resources

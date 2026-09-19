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

For additional support regarding external scripts, please refer to [Third-Party Script Support](#third-party-script-support)

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

### Selection and Acquisition of Emulator Port Number

#### mumu emulator: menu bar in the upper right corner of the emulator - Problem diagnosis - find "ADB debug port"

- If using the default port number 0, the default initial emulator will be used

#### Other emulators: find the port number according to your own situation, the following are some default ports

- LDPlayer Simulator 5555
- BlueStacks Simulator 5555
- MEmu Simulator 21503
- NOX Simulator 62001 / 59865

### Note

- Different emulators may have different port numbers, which need to be selected according to the actual situation
- Some emulators may require enabling adb port debugging in settings, such as BlueStacks Simulator, LDPlayer Simulator
- Some emulators may require disabling "Application Keep Alive" in settings, such as MUMU Simulator.(Auto-off
  configured, but may not work)
- When using an emulator, you need to make sure that the emulator's resolution is consistent with the resolution set
  in "Windows Setting" in AALC
- Emulators may cause the script to run slowly, so it is recommended to use a higher configuration computer and give the
  emulator enough memory and CPU resources

### macOS users

- On macOS, use the **emulator background mode**: Settings → Emulator settings → enable "Use Emulator", and select
  **"Other emulator" (10)** as the type.
- The MuMu (0) and BlueStacks 5 (1) drivers depend on Windows (registry / MuMuManager.exe) and are unavailable on
  macOS.
- Fill in the emulator's ADB address as host/port: usually `127.0.0.1:16384` on macOS (MuMu instances increment by +32)
  or `127.0.0.1:5555`; when unsure, run `adb devices` on the machine.
- Screenshots and input go through ADB (screencap / minitouch), same as on Windows. Start the emulator manually and keep
  its ADB enabled; the script will not launch the emulator process itself.
- The packaged build (`AALC.app`) keeps configuration, logs and image resources in the data directory
  `~/Library/Application Support/AALC`, so replacing `AALC.app` to upgrade keeps your settings. The macOS build is
  neither signed nor notarized: run `xattr -cr /Applications/AALC.app` once before the first launch, as described in
  the README.

#### PlayCover (Apple Silicon, no Android emulator needed)

- Use the community fork [hguandl/PlayCover](https://github.com/hguandl/PlayCover) (version `3.1.0.maa.N` or later),
  which bundles the PlayTools build that provides the MaaTools TCP service. Install the iOS build of Limbus Company
  there, turn on **MaaTools** in that game's settings (the "Port:" field next to it defaults to `1717`), then start the
  game — the game window title shows `[localhost:port]` once the service is ready.
- AALC Settings → Emulator settings: enable "Use Emulator", pick **"PlayCover (MaaTools)" (20)**, host `127.0.0.1`,
  port = the one in the window title (default `1717`, must match the "Port:" setting in PlayCover).
- Screenshots and touches go through the MaaTools TCP protocol straight to the game window (native pixels), same as on
  Windows/emulators. Start the game in PlayCover manually; AALC will not launch it.
- **Keyboard**: the MaaTools protocol has no keyboard command, but the game itself (a PlayTools-injected process) reads
  the hardware keyboard directly, so **Enter (confirm / start round), P (auto-select skills) and ESC (back / pause)**
  are injected into the game process by AALC with `CGEventPostToPid` — the game does not need to be focused, and you can
  keep using your Mac meanwhile. This requires the Accessibility permission for **the program running AALC** (the
  terminal for source runs, `AALC.app` for packaged builds) in System Settings → Privacy & Security → Accessibility;
  without it those three keys fall back to touches automatically.
- **Starting a round**: with the keyboard available it uses **P+Enter**, same as on Windows; if the round is not
  detected as started (e.g. the game missed the keys), later rounds automatically use the touch fallback (tap the
  win-rate panel so the game auto-assigns skills, then tap the start button), which **overrides manual guards /
  chain-battle lines** (a warning is logged).
- **Still touch-only**: **arrow keys** (`mirror_keyboard_navigation` and simple keyboard pathfinding fall back to click
  pathfinding, logged once), **Mirror map zoom** (mouse wheel on PC becomes a two-finger pinch), and **text input**
  ("Use team code" cannot type the code: AALC logs `编队码加载失败，继续使用当前队伍配置` and continues with the
  current team configuration without interrupting the task; set up the team manually in game if you need it, or use the
  emulator background mode (ADB) described above).

#### Known limitations

- Playover has limited support for OAuth logins due to signature-related issues: it does not support Sign in with Apple, and for Google logins, the user is required to log in again upon restarting the game.

### Third-Party Script Support

## Command Line Launch

Launch method:

```ps1
# < > indicates required content
# [ ] indicates optional parameters
# Parameters without brackets should be filled according to the corresponding command description
AALC.exe <command_name> command_args extra_args

# The following examples omit "AALC.exe"
```

Currently supported commands:

- `start [--exit [int]]`
  - `start`
    AALC will automatically run tasks after startup; tasks need to be set in advance
  - `[--exit]` Optional parameter, comes with an additional parameter
    - `[int]` An integer string representing the index of the `combobox` on the AALC One-Click Grass interface. If not specified, the default is `5`, which means **Exit AALC**

Example: `AALC.exe start --exit 6`

In the current version, this will exit both AALC and the game after completion.

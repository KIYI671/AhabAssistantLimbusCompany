# AALC Development Mode - Quick Start Guide

## 🔥 Hot Reload Development Script

### Installation

First, install the required dependency:

```bash
pip install watchdog
```

Or add to your project:
```bash
pip install -r requirements-dev.txt
```

### Usage

Simply run the development script:

```bash
python main_dev.py
```

### Features

✅ **Auto Hot Reload** - Automatically restarts when you save any `.py` file  
✅ **Skip Admin Checks** - No UAC prompts during development  
✅ **Multi-Instance** - Allows multiple instances for testing  
✅ **Keyboard Shortcuts**:
- **Ctrl+R** - Manual reload
- **Ctrl+C** - Exit

### Watched Directories

The script monitors these directories for changes:
- `app/` - Application UI and logic
- `module/` - Core modules
- `tasks/` - Task automation scripts
- `utils/` - Utility functions
- `i18n/` - Internationalization files
- Root `.py` files

### How It Works

1. **Save any Python file** → Script detects change
2. **Automatic restart** → Old instance killed, new one started
3. **See changes immediately** → No manual restart needed

### Development Workflow

```
1. Edit your code in app/my_app.py
2. Save file (Ctrl+S)
3. ✨ Application automatically reloads
4. Test your changes
5. Repeat!
```

### Console Output

```
============================================================
  AALC Development Mode - Hot Reload Enabled
============================================================
📁 Watching directory: C:\Users\ls\AhabAssistantLimbusCompany
🔥 Hot reload: ENABLED
⌨️  Ctrl+R: Manual reload | Ctrl+C: Exit
────────────────────────────────────────────────────────────

🚀 Starting AALC...
────────────────────────────────────────────────────────────
✅ Application started (PID: 12345)

📝 File changed: app\my_app.py
🔄 Stopping previous instance...
🚀 Starting AALC...
✅ Application started (PID: 12346)
```

### Troubleshooting

**Q: watchdog not installed?**  
A: Run `pip install watchdog` - the script will auto-install if missing

**Q: Application keeps restarting?**  
A: Check for auto-save features in your editor that might trigger multiple saves

**Q: Changes not detected?**  
A: Make sure you're editing files in the watched directories listed above

### Switching Between Production and Development

**Development** (with hot reload):
```bash
python main_dev.py
```

**Production** (original):
```bash
python main.py
```

Or use the packaged exe:
```bash
AALC.exe
```

### Notes

- The script creates a temporary `__main_dev_temp__.py` file - do not edit it
- Admin permission checks are bypassed in dev mode
- Mutex lock is disabled to allow multiple instances
- 1-second cooldown prevents rapid restarts from multiple file saves

---

**Happy coding with hot reload! 🚀**

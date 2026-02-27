"""
AALC Development Mode with Hot Reload
======================================
This script provides automatic hot reload functionality for development.

Usage:
    python main_dev.py              # with hot reload
    python main_dev.py --no-reload  # dev mode without auto-restart

Features:
- Auto-restarts when .py files are modified
- Skips admin permission checks
- Disables mutex lock (allows multiple instances)
- Press Ctrl+R to manually reload
- Press Ctrl+C to exit
"""

import os
import subprocess
import sys
import threading
import time
from pathlib import Path

from module.logger import log

try:
    from watchdog.events import FileSystemEventHandler
    from watchdog.observers import Observer
except ImportError:
    log.critical(
        "watchdog not installed. Please run `uv sync` to install dependencies."
    )
    sys.exit(1)

try:
    from pynput import keyboard
except ImportError:
    log.warning("pynput not available, keyboard shortcuts disabled")
    keyboard = None


class AALCReloader:
    """Main hot reload manager"""

    def __init__(self, no_reload=False):
        self.process = None
        self.observer = None
        self.should_restart = False
        self.restart_lock = threading.Lock()
        self.last_restart_time = 0
        self.restart_cooldown = 1.0  # seconds
        self.no_reload = no_reload

    def start(self):
        """Start the development mode"""
        if self.no_reload:
            log.info("AALC Development Mode - Hot Reload Disabled (manual Ctrl+R only)")
        else:
            log.info("AALC Development Mode - Hot Reload Enabled")
            log.info(f"Watching directory: {Path.cwd()}")

        # Set development environment variables
        os.environ["AALC_DEV_MODE"] = "1"
        os.environ["AALC_SKIP_ADMIN"] = "1"
        os.environ["AALC_FAST_START"] = "1"

        # Start file watcher (skip when --no-reload)
        if not self.no_reload:
            self.start_file_watcher()

        # Start keyboard listener if available (always allow manual reload)
        if keyboard:
            self.start_keyboard_listener()

        # Initial start
        self.restart_app()

        try:
            while True:
                time.sleep(0.5)

                # Check if process is still running
                if self.process and self.process.poll() is not None:
                    # Process has exited
                    exit_code = self.process.returncode
                    if not self.should_restart:
                        # User closed the window, exit dev mode
                        log.warning(f"Application exited with code {exit_code}")
                        log.info("Exiting development mode...")
                        self.cleanup()
                        return

                if self.should_restart and self.can_restart():
                    with self.restart_lock:
                        self.should_restart = False
                        self.restart_app()
        except KeyboardInterrupt:
            self.cleanup()

    def can_restart(self):
        """Check if enough time has passed since last restart"""
        current_time = time.time()
        if current_time - self.last_restart_time >= self.restart_cooldown:
            self.last_restart_time = current_time
            return True
        return False

    def start_file_watcher(self):
        """Start watching for file changes"""
        event_handler = FileChangeHandler(self)
        self.observer = Observer()

        # Watch main directories
        watch_dirs = ["app", "module", "tasks", "utils", "i18n"]
        for dirname in watch_dirs:
            dir_path = Path.cwd() / dirname
            if dir_path.exists():
                self.observer.schedule(event_handler, str(dir_path), recursive=True)

        # Watch root directory (non-recursive)
        self.observer.schedule(event_handler, str(Path.cwd()), recursive=False)

        self.observer.start()

    def start_keyboard_listener(self):
        """Start keyboard shortcut listener"""

        def on_press(key):
            try:
                if hasattr(key, "char"):
                    # Ctrl+R for manual reload
                    if key.char == "\x12":  # Ctrl+R
                        log.info("Manual reload triggered")
                        self.should_restart = True
            except AttributeError:
                pass

        listener = keyboard.Listener(on_press=on_press)
        listener.daemon = True
        listener.start()

    def restart_app(self):
        """Restart the main application"""
        # Kill existing process
        if self.process:
            log.info("Stopping previous instance...")
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                log.warning("Force killing process...")
                self.process.kill()
                self.process.wait()

        # Start new process
        log.info("Starting AALC...")

        # Create modified main.py startup
        startup_script = self.create_dev_main()

        try:
            self.process = subprocess.Popen(
                [sys.executable, "-u", startup_script],
                cwd=Path.cwd(),
                env=os.environ.copy(),
            )
            log.info(f"Application started (PID: {self.process.pid})")
        except Exception as e:
            log.error(f"Failed to start: {e}")

    def create_dev_main(self):
        """Create a temporary development version of main.py"""
        dev_main_path = Path.cwd() / "__main_dev_temp__.py"

        # Read original main.py
        main_content = (Path.cwd() / "main.py").read_text(encoding="utf-8")

        # Modify to skip admin checks and mutex
        dev_content = f"""# Auto-generated development main script
import os
os.environ['AALC_DEV_MODE'] = '1'

# Original main.py content with modifications
{main_content}
"""

        # Replace admin check
        dev_content = dev_content.replace(
            "if not pyuac.isUserAdmin():", "if False and not pyuac.isUserAdmin():"
        )

        # Replace mutex check
        dev_content = dev_content.replace(
            "if not mutex or last_error > 0:",
            "if False and (not mutex or last_error > 0):",
        )

        dev_main_path.write_text(dev_content, encoding="utf-8")
        return str(dev_main_path)

    def cleanup(self):
        """Cleanup resources"""
        log.info("Shutting down...")

        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()

        if self.observer:
            self.observer.stop()
            self.observer.join()

        # Clean up temp file
        temp_file = Path.cwd() / "__main_dev_temp__.py"
        if temp_file.exists():
            temp_file.unlink()

        if temp_file.exists():
            temp_file.unlink()

        log.info("Cleanup complete")
        sys.exit(0)


class FileChangeHandler(FileSystemEventHandler):
    """Handle file system events"""

    def __init__(self, reloader):
        self.reloader = reloader
        self.ignored_patterns = {
            "__pycache__",
            ".pyc",
            ".git",
            ".idea",
            "venv",
            "env",
            ".egg-info",
            "__main_dev_temp__.py",
        }

    def should_ignore(self, path):
        """Check if file should be ignored"""
        path_str = str(path)
        return any(pattern in path_str for pattern in self.ignored_patterns)

    def on_modified(self, event):
        """Handle file modification"""
        if event.is_directory or self.should_ignore(event.src_path):
            return

        if event.src_path.endswith(".py"):
            rel_path = Path(event.src_path).relative_to(Path.cwd())
            log.info(f"File changed: {rel_path}")
            self.reloader.should_restart = True

    def on_created(self, event):
        """Handle file creation"""
        if not event.is_directory and event.src_path.endswith(".py"):
            rel_path = Path(event.src_path).relative_to(Path.cwd())
            log.info(f"File created: {rel_path}")
            self.reloader.should_restart = True


def main():
    """Entry point"""
    no_reload = "--no-reload" in sys.argv

    # Check Python version
    if sys.version_info < (3, 12):
        log.warning(f"Python 3.12+ recommended (current: {sys.version})")

    # Check if main.py exists
    if not Path("main.py").exists():
        log.error("main.py not found in current directory")
        sys.exit(1)

    reloader = AALCReloader(no_reload=no_reload)
    reloader.start()


if __name__ == "__main__":
    main()

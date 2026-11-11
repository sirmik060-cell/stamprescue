# main.py  (диагностическая версия — ловит нативный крах Qt)
import faulthandler
import os
import sys
import traceback

# --- лог-файл рядом с main.py ---
if getattr(sys, "frozen", False):
    _BASE = os.path.dirname(sys.executable)
else:
    _BASE = os.path.dirname(os.path.abspath(__file__))
LOG_PATH = os.path.join(_BASE, "crash_log.txt")
_logf = open(LOG_PATH, "w", encoding="utf-8", buffering=1)

# faulthandler пишет сюда даже при падении в C++
try:
    faulthandler.enable(file=_logf, all_threads=True)
except Exception as e:
    _logf.write(f"[faulthandler enable failed: {e}]\n")


def log(msg):
    _logf.write(msg + "\n")
    _logf.flush()
    try:
        print(msg)
    except Exception:
        pass


log("=== StampRescue launch ===")
log(f"python={sys.version}")
log(f"cwd={os.getcwd()}")
log(f"base={_BASE}")


class _Tee:
    """Дублирует stderr и в консоль, и в лог-файл."""
    def __init__(self, *streams):
        self._s = streams
    def write(self, d):
        for s in self._s:
            try:
                s.write(d)
            except Exception:
                pass
    def flush(self):
        for s in self._s:
            try:
                s.flush()
            except Exception:
                pass


_orig_stderr = sys.stderr
sys.stderr = _Tee(_orig_stderr, _logf)


def excepthook(t, v, tb):
    text = "".join(traceback.format_exception(t, v, tb))
    log("=== PYTHON EXCEPTION ===\n" + text)
    try:
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.critical(None, "StampRescue", text[:2000])
    except Exception:
        pass


sys.excepthook = excepthook

try:
    log("importing PySide6...")
    from PySide6.QtWidgets import QApplication
    log("importing MainWindow, THEME...")
    from ui.main_window import THEME, MainWindow
    log("imports OK")

    log("creating QApplication...")
    app = QApplication(sys.argv)
    log("setStyle Fusion...")
    app.setStyle("Fusion")
    log("setStyleSheet(THEME)...")
    app.setStyleSheet(THEME)
    log("setStyleSheet OK")

    log("before splash ...")
    splash = None
    if os.environ.get("STAMPRESCUE_NO_SPLASH") != "1":
        try:
            from ui.splash import Splash, play_intro_sound
            dur = int(os.environ.get("STAMPRESCUE_SPLASH_MS", "5000"))
            splash = Splash(duration_ms=dur)
            splash.start()
            log("splash shown")
        except Exception as e:
            log(f"splash skipped: {e}")

    log("before MainWindow() ...")
    win = MainWindow()
    log("MainWindow() constructed OK")

    log("before win.show() ...")
    win.show()
    log("win.show() OK")
    if splash is not None:
        play_intro_sound()  # музыка синхронна с таймлайном заставки

    log("entering app.exec() ...")
    _logf.flush()
    sys.exit(app.exec())

except Exception:
    log("=== TOP-LEVEL EXCEPTION ===")
    log(traceback.format_exc())
    raise
import sys
import os
import ctypes

# --- THÊM ĐOẠN NÀY ĐỂ FIX LỖI DPI SCALING TRÊN LAPTOP ---
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2) # PROCESS_PER_MONITOR_DPI_AWARE
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass
# --------------------------------------------------------

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "modules"))

from admin_deps import ensure_admin, install_deps
ensure_admin()
install_deps()

import tkinter as tk
from ui_app import App

if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
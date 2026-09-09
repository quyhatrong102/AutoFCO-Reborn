"""
admin_deps.py - Kiểm tra quyền Admin và cài đặt thư viện phụ thuộc
"""
import os
import subprocess
import sys
import ctypes


def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


def ensure_admin():
    if not is_admin():
        exe_path = sys.executable
        if exe_path.lower().endswith("python.exe"):
            exe_path = exe_path[:-10] + "pythonw.exe"
        ctypes.windll.shell32.ShellExecuteW(None, "runas", exe_path, " ".join(sys.argv), None, 1)
        sys.exit()


def install_deps():
    pkgs = {
        "pyautogui": "pyautogui",
        "cv2": "opencv-python",
        "numpy": "numpy",
        "pygetwindow": "pygetwindow",
        "PIL": "Pillow",
        "win32gui": "pywin32",
        "pytesseract": "pytesseract",
        "pygame": "pygame-ce",
        "keyboard": "keyboard",
        "mss": "mss"
    }
    for mod, pkg in pkgs.items():
        try:
            __import__(mod)
        except ImportError:
            # Hiện thông báo
            print(f"Đang tải và cài đặt thư viện còn thiếu: {pkg}... Vui lòng đợi trong giây lát!")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", pkg, "--user"])
            except Exception as e:
                print(f"Lỗi khi cài đặt {pkg}: {e}")
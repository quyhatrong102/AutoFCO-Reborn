# Khôi phục file bot_insert_nownd.py (Auto Chèn KHÔNG chiếm chuột)
# Sử dụng Win32 API (PostMessage + PrintWindow) thay vì pyautogui + ImageGrab.

import os
import re
import time
import datetime
import ctypes
import struct
import numpy as np
import cv2
import win32gui
import win32con
import win32ui
import pytesseract
from PIL import Image

import sys
if getattr(sys, 'frozen', False):
    _PROOF_DIR = os.path.join(os.path.dirname(sys.executable), "chen_proof")
else:
    _PROOF_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "chen_proof")

def _ensure_proof_dir():
    if not os.path.exists(_PROOF_DIR):
        os.makedirs(_PROOF_DIR)

def _make_lparam(x, y):
    return (y << 16) | x

def _post_click(hwnd, x, y):
    lparam = _make_lparam(x, y)
    win32gui.PostMessage(hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lparam)
    time.sleep(0.02)
    win32gui.PostMessage(hwnd, win32con.WM_LBUTTONUP, 0, lparam)

def _post_key(hwnd, vk_code):
    win32gui.PostMessage(hwnd, win32con.WM_KEYDOWN, vk_code, 0)
    time.sleep(0.02)
    win32gui.PostMessage(hwnd, win32con.WM_KEYUP, vk_code, 0)

def _print_window(hwnd):
    # PrintWindow(hwnd, hdc, PW_CLIENTONLY | PW_RENDERFULLCONTENT)
    left, top, right, bottom = win32gui.GetClientRect(hwnd)
    width = right - left
    height = bottom - top

    hwndDC = win32gui.GetWindowDC(hwnd)
    mfcDC  = win32ui.CreateDCFromHandle(hwndDC)
    saveDC = mfcDC.CreateCompatibleDC()

    saveBitMap = win32ui.CreateBitmap()
    saveBitMap.CreateCompatibleBitmap(mfcDC, width, height)
    saveDC.SelectObject(saveBitMap)

    # 3 = PW_CLIENTONLY (1) | PW_RENDERFULLCONTENT (2)
    ctypes.windll.user32.PrintWindow(hwnd, saveDC.GetSafeHdc(), 3)

    bmpinfo = saveBitMap.GetInfo()
    bmpstr = saveBitMap.GetBitmapBits(True)

    img = Image.frombuffer(
        'RGB',
        (bmpinfo['bmWidth'], bmpinfo['bmHeight']),
        bmpstr, 'raw', 'BGRX', 0, 1)

    win32gui.DeleteObject(saveBitMap.GetHandle())
    saveDC.DeleteDC()
    mfcDC.DeleteDC()
    win32gui.ReleaseDC(hwnd, hwndDC)

    return img

def _grab_region(hwnd, rx1, ry1, rx2, ry2):
    img = _print_window(hwnd)
    return img.crop((rx1, ry1, rx2, ry2))

def _get_pixel(hwnd, x, y):
    img = _print_window(hwnd)
    return img.getpixel((x, y))

def _color_match(hwnd, x, y, hex_color, tol=15):
    try:
        r_tgt = int(hex_color[0:2], 16)
        g_tgt = int(hex_color[2:4], 16)
        b_tgt = int(hex_color[4:6], 16)
        r, g, b = _get_pixel(hwnd, x, y)
        return (abs(r - r_tgt) <= tol and 
                abs(g - g_tgt) <= tol and 
                abs(b - b_tgt) <= tol)
    except:
        return False

_SLOT_CLICK_POS = {
    1: (642, 245),
    2: (635, 274),
    3: (632, 304),
    4: (634, 340),
    5: (632, 369),
    6: (631, 409),
    7: (633, 435),
    8: (631, 473),
    9: (633, 498),
    10: (632, 532),
    11: (631, 563),
    12: (626, 600),
    13: (627, 630)
}

class InsertMixinNoWnd:
    def _ocr_from_img(self, img):
        if img is None: return None
        gray = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2GRAY)
        thresh = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY_INV)[1]
        text = pytesseract.image_to_string(
            thresh, config='--psm 7 -c tessedit_char_whitelist=0123456789MBmb,. '
        ).strip().upper().replace(' ', '')
        # Fix OCR misread: B (Billion) -> 8
        if text and text[-1] == '8' and '.' in text:
            dot_pos = text.rfind('.')
            after_dot = text[dot_pos+1:-1]  # phan giua '.' va '8' cuoi
            if after_dot.isdigit() and 1 <= len(after_dot) <= 2:
                text = text[:-1] + 'B'
        if any(c.isdigit() for c in text):
            return text
        return None

    def _grab_price_wnd(self, is_max):
        if is_max:
            return _grab_region(self.hwnd, 908, 319, 1063, 340)
        else:
            return _grab_region(self.hwnd, 908, 319, 1063, 340)

    def _wait_popup_close_wnd(self, timeout=1.5):
        t0 = time.time()
        while self.running and (time.time() - t0 < timeout):
            if not _color_match(self.hwnd, 679, 595, "FCFCF7", tol=20):
                return
            time.sleep(0.05)

    def _wait_color_appear_wnd(self, x, y, hex_col, timeout=2.0, click_if_match=True):
        t0 = time.time()
        while self.running and (time.time() - t0 < timeout):
            if _color_match(self.hwnd, x, y, hex_col, tol=20):
                if click_if_match:
                    _post_click(self.hwnd, x, y)
                return True
            time.sleep(0.05)
        return False

    def _get_clock_now(self):
        now = datetime.datetime.now()
        if getattr(self, "_insert_time_offset", None) is not None:
            now = now + self._insert_time_offset
        return now

    def _in_active_window(self):
        s = self._get_clock_now().second
        return s >= 50 or s <= 25

    def run_insert_nownd(self, slot_configs, do_notify=False):
        self.running = True
        self._last_log_was_wait = False
        _original_log = self.log
        def _wrapped_log(msg, tag=None, update_last=False):
            if "Qua :25" in msg:
                if self._last_log_was_wait:
                    update_last = True
                self._last_log_was_wait = True
            else:
                self._last_log_was_wait = False
            if tag is None:
                _original_log(msg, update_last=update_last)
            else:
                _original_log(msg, tag, update_last=update_last)
        self.log = _wrapped_log
        _ensure_proof_dir()

        def safe_finish(all_completed=False):
            self.running = False
            if all_completed and do_notify:
                self.play_success_sound()
            if hasattr(self, 'root') and self.root:
                def _ui_task():
                    self.on_finished()
                    if all_completed and do_notify:
                        import tkinter.messagebox as msgbox
                        msgbox.showinfo("Thông báo", "Chèn xong hết rồi")
                self.root.after(0, _ui_task)
            else:
                self.on_finished()

        if not self.arrange_game():
            self.log("❌ Không tìm thấy cửa sổ game!")
            safe_finish(False)
            return

        self.hwnd = win32gui.FindWindow(None, "FC ONLINE")
        if not self.hwnd:
            self.log("❌ Không lấy được handle cửa sổ!")
            safe_finish(False)
            return
        
        # Click vao tab "Danh sach yeu thich" luc bat dau start
        self.log("Đang chuyển sang tab Danh sách yêu thích...", "white")
        _post_click(self.hwnd, 532, 151)
        time.sleep(0.5)
        
        self.log(f"▶ Bắt đầu Auto Chèn ẨN - {len(slot_configs)} slot", "header")
        for cfg in slot_configs:
            slot_num = int(cfg["slot"])
            is_max   = (cfg["mua_ban"] == "Mua")
            self.log(f"  Slot {slot_num}: {'Chèn Max' if is_max else 'Chèn Min'}", "white")
        self.log("", "white")

        slot_states = {int(cfg["slot"]): {"init_price": None, "done": False}
                       for cfg in slot_configs}
        all_seen_prices = set()

        if not self._in_active_window():
            s_now = self._get_clock_now().second
            self.log(f"🕒 Chờ đến giây :50... (hiện tại :{s_now:02d})", "white")
            while self.running:
                if self._get_clock_now().second >= 50:
                    break
                time.sleep(0.05)

        while self.running:
            if not self._in_active_window():
                _wait_count = getattr(self, "_insert_wait_count", 0) + 1
                self._insert_wait_count = _wait_count
                self.log("⏸ Qua :25 -> chờ đến :50...", "orange")
                while self.running:
                    if self._get_clock_now().second >= 50:
                        break
                    time.sleep(0.05)
                continue

            active_slots = [cfg for cfg in slot_configs
                            if not slot_states[int(cfg["slot"])]["done"]]
            
            if not active_slots:
                break

            for cfg in active_slots:
                if not self.running:
                    break

                slot_num = int(cfg["slot"])
                is_max   = (cfg["mua_ban"] == "Mua")
                st       = slot_states[slot_num]

                rel_sx, rel_sy = _SLOT_CLICK_POS.get(slot_num, (338, 207))

                if is_max:
                    action_x, action_y = 924, 670
                    huy_x,  huy_y      = 997, 587
                    chen_x, chen_y     = 875, 588
                    chen_color         = "D03C23"
                    px, py             = 973, 321
                else:
                    action_x, action_y = 1062, 671
                    huy_x,  huy_y      = 1004, 617
                    chen_x, chen_y     = 882, 616
                    chen_color         = "0C8FF3"
                    px, py             = 975, 329

                if len(slot_configs) >= 2 or st["init_price"] is None:
                    _post_click(self.hwnd, rel_sx, rel_sy)
                    time.sleep(0.3)

                if is_max:
                    _post_click(self.hwnd, action_x, action_y)
                    time.sleep(0.1)
                else:
                    btn_ready = self._wait_color_appear_wnd(
                        action_x, action_y, "2554EA", timeout=30.0, click_if_match=True
                    )
                    if not btn_ready:
                        continue

                self._wait_popup_close_wnd()
                popup_opened = self._wait_color_appear_wnd(
                    679, 595, "FCFCF7", timeout=5.0, click_if_match=False
                )
                
                if not popup_opened:
                    if self.running:
                        self.log(f"⚠️ Slot {slot_num}: popup không hiện, thử lại...", "orange")
                    continue

                time.sleep(0.1)

                price_img = self._grab_price_wnd(is_max)
                price_now = self._ocr_from_img(price_img)

                own_init = slot_states[slot_num]["init_price"]
                suspicious = all_seen_prices - ({own_init} if own_init else set())
                if price_now and price_now in suspicious:
                    _post_click(self.hwnd, huy_x, huy_y)
                    self._wait_popup_close_wnd()
                    continue
                
                if price_now:
                    all_seen_prices.add(price_now)

                if st["init_price"] is None:
                    if price_now is None:
                        _post_click(self.hwnd, huy_x, huy_y)
                        self._wait_popup_close_wnd()
                        continue
                    st["init_price"] = price_now
                    mb_label = "Mua" if is_max else "Bán"
                    self.log(f"🎯 Slot {slot_num} ({mb_label}): giá gốc = {price_now}", "white")
                    _post_click(self.hwnd, huy_x, huy_y)
                    self._wait_popup_close_wnd()
                    continue

                if price_now == st["init_price"]:
                    _post_click(self.hwnd, huy_x, huy_y)
                    self._wait_popup_close_wnd()
                    continue

                if price_now and price_now != st["init_price"]:
                    old_price = st["init_price"]
                    now_ts   = self._get_clock_now()
                    ts_str   = f"{now_ts.hour}:{now_ts.minute:02d}:{now_ts.second:02d}"
                    mb_label = "Mua" if is_max else "Bán"
                    self.log(f"🔥 Đã chèn ẨN Slot {slot_num} ({mb_label}) lúc {ts_str}", "success")
                    self.log(f"   Giá: {old_price} -> {price_now}", "success")

                    _post_click(self.hwnd, px, py)
                    time.sleep(0.1)

                    clicked = self._wait_color_appear_wnd(
                        chen_x, chen_y, chen_color, timeout=1.0, click_if_match=True
                    )

                    if clicked:
                        time.sleep(4.0)
                        try:
                            ts_fname = f"{now_ts.hour}h{now_ts.minute:02d}p{now_ts.second:02d}s"
                            label_f  = "max" if is_max else "min"
                            fname    = f"YeuThich_Slot{slot_num}_{label_f}_{ts_fname}.png"
                            full_img = _print_window(self.hwnd)
                            full_img.save(os.path.join(_PROOF_DIR, fname))
                        except Exception:
                            pass
                        
                        self._wait_popup_close_wnd()
                    else:
                        _post_click(self.hwnd, huy_x, huy_y)
                        self._wait_popup_close_wnd()

                    st["done"] = True

                else:
                    _post_click(self.hwnd, huy_x, huy_y)
                    self._wait_popup_close_wnd()

        safe_finish(True)

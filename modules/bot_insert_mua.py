"""
bot_insert_mua.py - Logic Auto Chen DS Mua
"""
import os
import re
import time
import datetime
import numpy as np
import pyautogui
import pytesseract
import cv2
from PIL import ImageGrab, Image as PILImage

import sys
if getattr(sys, 'frozen', False):
    _PROOF_DIR = os.path.join(os.path.dirname(sys.executable), "chen_proof")
else:
    _PROOF_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "chen_proof")

_SLOT_CLICK_POS_MUA = {
    1: (999, 212),
    2: (999, 252),
    3: (999, 293),
    4: (999, 336),
    5: (999, 375),
    6: (999, 422),
    7: (999, 458),
    8: (999, 500),
    9: (999, 544),
    10: (999, 582),
    11: (999, 625),
}

def _ensure_proof_dir():
    os.makedirs(_PROOF_DIR, exist_ok=True)


class InsertMuaMixin:

    def _ocr_mua_from_img(self, img):
        iw, ih = img.size
        img_big = img.resize((iw * 4, ih * 4), PILImage.LANCZOS)
        arr = np.array(img_big.convert("L"))
        _, bw = cv2.threshold(arr, 180, 255, cv2.THRESH_BINARY)
        bw = cv2.copyMakeBorder(bw, 8, 8, 8, 8, cv2.BORDER_CONSTANT, value=255)
        pil = PILImage.fromarray(bw)
        
        # Ho tro doc gia moi: 1.6M, 9.97B, 112,000
        text = pytesseract.image_to_string(
            pil, config="--psm 7 -c tessedit_char_whitelist=0123456789MBmb,. "
        ).strip().upper()
        
        # Loc bo khoang trang
        text = text.replace(' ', '')
        
        # Fix OCR misread: B (Billion) -> 8
        if text and text[-1] == '8' and '.' in text:
            dot_pos = text.rfind('.')
            after_dot = text[dot_pos+1:-1]  # phan giua '.' va '8' cuoi
            if after_dot.isdigit() and 1 <= len(after_dot) <= 2:
                text = text[:-1] + 'B'
        
        # Tra ve nguyen chuoi (vd: "1.6M", "112,000", "9.97B")
        # Chi can co it nhat 1 ky tu so la hop le
        if any(c.isdigit() for c in text):
            return text
        return None

    def _wait_popup_close_mua(self, timeout=3.0):
        if not self.rect: return
        x1, y1 = self.rect[0], self.rect[1]
        deadline = time.time() + timeout
        while time.time() < deadline:
            if not self.running: return
            if not self.is_color_match("FCFCF7", x1 + 679, y1 + 595):
                return
            time.sleep(0.05)

    def _get_clock_now_mua(self):
        now = datetime.datetime.now()
        if getattr(self, "_insert_mua_time_offset", None) is not None:
            now = now + self._insert_mua_time_offset
        return now

    def _in_active_window_mua(self):
        s = self._get_clock_now_mua().second
        return s >= 50 or s <= 25

    def run_insert_mua(self, slot_configs, do_notify=False):
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
                self.trigger_success_alarm(1)
            
            if all_completed:
                self.log("\n✅ Hoàn tất tất cả slot!", "success")
            
            if hasattr(self, 'root') and self.root:
                def _ui_task():
                    self.on_finished(completed=all_completed)
                    if all_completed and do_notify:
                        import tkinter.messagebox as msgbox
                        msgbox.showinfo("Thông báo", "Chèn xong hết rồi")
                self.root.after(0, _ui_task)
            else:
                self.on_finished(completed=all_completed)

        if not self.arrange_game():
            self.log("❌ Không tìm thấy cửa sổ game!")
            safe_finish(False)
            return

        x1, y1, _, _ = self.rect

        self.log(f"🚀 Bắt đầu Auto Chèn DS Mua - {len(slot_configs)} slot", "header")
        for cfg in slot_configs:
            slot_num = int(cfg["slot"])
            is_max   = (cfg["mua_ban"] == "Mua")
            self.log(f"  Slot {slot_num}: {'Chèn Max' if is_max else 'Chèn Min'}", "white")
        self.log("", "white")

        slot_states = {int(cfg["slot"]): {"init_price": None, "done": False}
                       for cfg in slot_configs}
        all_seen_prices = set()

        if not self._in_active_window_mua():
            s_now = self._get_clock_now_mua().second
            self.log(f"⏳ Chờ đến giây :50... (hiện tại :{s_now:02d})", "white")
            while self.running:
                if self._get_clock_now_mua().second >= 50:
                    break
                time.sleep(0.05)

        while self.running:
            if not self._in_active_window_mua():
                self.log("⏸ Qua :25 — chờ đến :50...", "orange")
                while self.running:
                    if self._get_clock_now_mua().second >= 50:
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

                rel_sx, rel_sy = _SLOT_CLICK_POS_MUA.get(slot_num, (999, 212))

                pyautogui.moveTo(x1 + rel_sx, y1 + rel_sy)
                time.sleep(0.2)
                pyautogui.click(x1 + rel_sx, y1 + rel_sy)
                time.sleep(0.1)

                popup_opened = self.hover_and_wait_color(
                    679, 595, "FCFCF7", timeout=5.0, click_if_match=False
                )
                
                if not popup_opened:
                    if self.running:
                        self.log(f"⚠️ Slot {slot_num}: popup không hiện, thử lại...", "orange")
                    continue

                time.sleep(0.1)

                if is_max:
                    bbox_price     = (x1 + 908, y1 + 319, x1 + 1063, y1 + 340)
                    price_x, price_y = 973, 321
                    huy_x, huy_y   = 942, 605
                    chen_x, chen_y = 786, 605
                    chen_color     = "D03C23"
                else:
                    bbox_price     = (x1 + 908, y1 + 319, x1 + 1063, y1 + 340)
                    price_x, price_y = 975, 329
                    huy_x, huy_y   = 949, 619
                    chen_x, chen_y = 791, 619
                    chen_color     = "0C8FF3"

                price_img = ImageGrab.grab(bbox=bbox_price)
                price_now = self._ocr_mua_from_img(price_img)

                own_init = slot_states[slot_num]["init_price"]
                suspicious = all_seen_prices - ({own_init} if own_init else set())
                if price_now and price_now in suspicious:
                    pyautogui.click(x1 + huy_x, y1 + huy_y)
                    self._wait_popup_close_mua()
                    continue
                if price_now:
                    all_seen_prices.add(price_now)

                if st["init_price"] is None:
                    if price_now is None:
                        pyautogui.click(x1 + huy_x, y1 + huy_y)
                        self._wait_popup_close_mua()
                        continue
                    st["init_price"] = price_now
                    mb_label = "Mua" if is_max else "Bán"
                    self.log(f"📌 Slot {slot_num} ({mb_label}): giá gốc = {price_now}", "white")
                    pyautogui.click(x1 + huy_x, y1 + huy_y)
                    self._wait_popup_close_mua()
                    continue

                if price_now == st["init_price"]:
                    pyautogui.click(x1 + huy_x, y1 + huy_y)
                    self._wait_popup_close_mua()
                    continue

                if price_now and price_now != st["init_price"]:
                    old_price = st["init_price"]
                    now_ts   = self._get_clock_now_mua()
                    ts_str   = f"{now_ts.hour}:{now_ts.minute:02d}:{now_ts.second:02d}"
                    mb_label = "Mua" if is_max else "Bán"
                    self.log(f"✅ Đã chèn Slot {slot_num} ({mb_label}) lúc {ts_str}", "success")
                    self.log(f"   Giá: {old_price} → {price_now}", "success")

                    try:
                        ts_fname = f"{now_ts.hour}h{now_ts.minute:02d}p{now_ts.second:02d}s"
                        label_f  = "max" if is_max else "min"
                        fname    = f"Mua_Slot{slot_num}_{label_f}_{ts_fname}.png"
                        ImageGrab.grab(bbox=(x1, y1, x1+1280, y1+720)).save(
                            os.path.join(_PROOF_DIR, fname))
                    except Exception:
                        pass

                    pyautogui.click(x1 + price_x, y1 + price_y)
                    time.sleep(0.1)

                    clicked = self.hover_and_wait_color(
                        chen_x, chen_y, chen_color, timeout=1.0, click_if_match=True
                    )

                    if not clicked:
                        pyautogui.click(x1 + huy_x, y1 + huy_y)
                    self._wait_popup_close_mua()

                    st["done"] = True

                else:
                    pyautogui.click(x1 + huy_x, y1 + huy_y)
                    self._wait_popup_close_mua()

        all_done = all(st["done"] for st in slot_states.values())
        safe_finish(all_done)

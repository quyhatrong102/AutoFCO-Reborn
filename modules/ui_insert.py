"""
ui_insert.py - UI cho tab Auto Chèn (Yêu thích)
"""
import threading
import tkinter as tk
from tkinter import scrolledtext, messagebox

from ui_helpers import add_hover_effect, prevent_typing, configure_log_tags


def _fetch_internet_time():
    import datetime
    try:
        import urllib.request, json
        with urllib.request.urlopen(
            "http://worldtimeapi.org/api/timezone/Asia/Ho_Chi_Minh", timeout=3
        ) as resp:
            data = json.loads(resp.read().decode())
            return datetime.datetime.strptime(data["datetime"][:19], "%Y-%m-%dT%H:%M:%S")
    except: pass
    return datetime.datetime.now()


class InsertUI:

    def build_insert_ui(self):
        self.btn_back_insert = tk.Button(
            self.insert_frame, text="< Menu",
            font=("Consolas", 8, "bold"), bg="#21262d", fg="#c9d1d9",
            bd=0, command=self.show_menu
        )
        self.btn_back_insert.place(x=5, y=5)
        add_hover_effect(self.btn_back_insert, "#30363d", "#21262d")

        tk.Label(self.insert_frame, text="Auto Chèn (DS yêu thích)",
                 font=("Consolas", 14, "bold"), fg="#ff79c6", bg="#0d1117"
                 ).pack(pady=(22, 0))
        tk.Label(self.insert_frame, text="By Quybodoivodichvutru",
                 font=("Consolas", 10, "bold"), fg="#58a6ff", bg="#0d1117"
                 ).pack(pady=(2, 6))

        time_frame = tk.Frame(self.insert_frame, bg="#161b22",
                              highlightthickness=1, highlightbackground="#30363d")
        time_frame.pack(pady=(4, 0), padx=20, fill="x")

        self.lbl_clock = tk.Label(time_frame, text="--:--:--",
                                  font=("Consolas", 22, "bold"), fg="#f1c40f", bg="#161b22")
        self.lbl_clock.pack(pady=(8, 2))

        self.lbl_chan_le = tk.Label(time_frame, text="",
                                    font=("Consolas", 9), fg="#8b949e", bg="#161b22")
        self.lbl_chan_le.pack(pady=(0, 8))

        self.insert_rows_data = []
        outer_wrap = tk.Frame(self.insert_frame, bg="#0d1117")
        outer_wrap.pack(pady=(10, 0), fill="x")
        table_wrap = tk.Frame(outer_wrap, bg="#0d1117")
        table_wrap.pack(anchor="center")

        hdr = tk.Frame(table_wrap, bg="#0d1117")
        hdr.pack(anchor="w")

        from ui_insert_mua import _W_SLOT, _W_MB, _PAD_L, _PAD_MID, _W_DEL, _MAX_ROWS, _ROW_H, _WIN_H_BASE, _WIN_W

        def _hdr_cell(parent, text, w, padx_left=0):
            f = tk.Frame(parent, bg="#0d1117", width=w, height=18)
            f.pack_propagate(False)
            f.pack(side="left", padx=(padx_left, 0))
            tk.Label(f, text=text, font=("Consolas", 8, "bold"),
                     fg="#58a6ff", bg="#0d1117").pack(anchor="center")

        _hdr_cell(hdr, "Slot",      _W_SLOT, padx_left=_PAD_L)
        _hdr_cell(hdr, "Mua / Bán", _W_MB,   padx_left=_PAD_MID)

        self.insert_rows_container = tk.Frame(table_wrap, bg="#0d1117")
        self.insert_rows_container.pack(anchor="w", pady=(2, 0))
        self._add_insert_row(is_first=True)

        btn_add = tk.Button(self.insert_frame, text="+ THÊM",
                            font=("Consolas", 9, "bold"), bg="#21262d", fg="#c9d1d9",
                            width=10, bd=0, command=self._add_insert_row_auto)
        btn_add.pack(pady=(6, 2))
        add_hover_effect(btn_add, "#30363d", "#21262d")

        log_f = tk.Frame(self.insert_frame, bg="#0d1117")
        log_f.pack(fill="both", expand=True, padx=10, pady=(6, 0))

        self.insert_log_b = scrolledtext.ScrolledText(
            log_f, bg="#161b22", fg="#7ee787",
            font=("Consolas", 10), height=4, bd=0)
        self.insert_log_b.bind("<Key>", prevent_typing)
        self.insert_log_b.pack(fill="both", expand=True)
        configure_log_tags(self.insert_log_b)

        ctrl_f = tk.Frame(self.insert_frame, bg="#0d1117")
        ctrl_f.pack(side="bottom", fill="x", padx=10, pady=(5, 15))

        btn_row = tk.Frame(ctrl_f, bg="#0d1117")
        btn_row.pack(fill="x")

        self.btn_start_insert = tk.Button(
            btn_row, text="START", bg="#238636", fg="white",
            font=("Consolas", 10, "bold"), width=10, bd=0,
            activebackground="#2ea043", command=self.start_insert)
        self.btn_start_insert.pack(side="left")
        add_hover_effect(self.btn_start_insert, "#2ea043", "#238636")

        self.insert_notify_var = tk.BooleanVar(value=False)
        chk_notify = tk.Checkbutton(
            btn_row, text="Thông báo khi chèn xong",
            variable=self.insert_notify_var,
            bg="#0d1117", fg="#8b949e", selectcolor="#0d1117",
            activebackground="#0d1117", activeforeground="#c9d1d9",
            font=("Consolas", 8), bd=0, highlightthickness=0)
        chk_notify.pack(side="right")

        esc_row = tk.Frame(ctrl_f, bg="#0d1117")
        esc_row.pack(fill="x")
        self.lbl_esc_hint_insert = tk.Label(
            esc_row, text="ESC để Dừng",
            font=("Consolas", 7, "bold"), fg="#ff5555", bg="#0d1117")
        self.lbl_esc_hint_insert.pack(side="left", pady=(2, 0))
        self.lbl_esc_hint_insert.pack_forget()

        self._insert_clock_running = False
        self._insert_time_offset   = None
        self._insert_log_queue     = []
        self._fetch_time_offset_async()
        self.root.after(100, self._drain_insert_log)

    def _add_insert_row(self, is_first=False, slot_num=None, mua_ban_init="Bán"):
        from ui_insert_mua import _W_SLOT, _PAD_L, _W_MB, _PAD_MID, _W_DEL
        _MAX_ROWS_YT = 13
        if len(self.insert_rows_data) >= _MAX_ROWS_YT: return
        row_f = tk.Frame(self.insert_rows_container, bg="#0d1117")
        row_f.pack(anchor="w", pady=2)

        if slot_num is None:
            used = {int(r["slot"].get()) for r in self.insert_rows_data}
            slot_num = next((i for i in range(1, _MAX_ROWS_YT + 1) if i not in used), 1)
        slot_var = tk.StringVar(value=str(slot_num))

        slot_f = tk.Frame(row_f, bg="#0d1117", width=_W_SLOT, height=22)
        slot_f.pack_propagate(False); slot_f.pack(side="left", padx=(_PAD_L, 0))

        slot_btn = tk.Button(slot_f, textvariable=slot_var, bg="#21262d", fg="white", font=("Consolas", 9), bd=1, relief="flat")
        slot_btn.pack(fill="both", expand=True)
        
        def _open_slot_popup(b=slot_btn, v=slot_var):
            pop = tk.Toplevel(self.root); pop.overrideredirect(True); pop.attributes("-topmost", True); pop.configure(bg="#30363d")
            bx = b.winfo_rootx(); by = b.winfo_rooty() + b.winfo_height() - 1; bw = b.winfo_width(); bh = 22
            pop.geometry(f"{bw}x{13 * bh}+{bx}+{by}")
            def _pick(val, p=pop, sv=v): sv.set(str(val)); p.destroy()
            for i in range(1, 14):
                btn = tk.Button(pop, text=str(i), font=("Consolas", 9), bg="#21262d", fg="white", bd=0, command=lambda val=i: _pick(val))
                btn.place(x=0, y=(i-1)*bh, width=bw, height=bh)
                add_hover_effect(btn, "#30363d", "#21262d")
            pop.bind("<FocusOut>", lambda e: pop.destroy()); pop.after(50, pop.focus_set)

        slot_btn.config(command=_open_slot_popup)

        mua_ban_var = tk.StringVar(value=mua_ban_init)
        mb_f = tk.Frame(row_f, bg="#21262d", highlightthickness=1, highlightbackground="#484f58", width=_W_MB, height=22)
        mb_f.pack_propagate(False); mb_f.pack(side="left", padx=(_PAD_MID, 0))

        C_MUA_ON = "#da3633"; C_MUA_OFF = "#21262d"; C_BAN_ON = "#1f6feb"; C_BAN_OFF = "#21262d"
        btn_mua = tk.Button(mb_f, text="Mua", font=("Consolas", 8, "bold"), bg=C_MUA_ON if mua_ban_init=="Mua" else C_MUA_OFF, fg="white" if mua_ban_init=="Mua" else "#8b949e", bd=0)
        btn_ban = tk.Button(mb_f, text="Bán", font=("Consolas", 8, "bold"), bg=C_BAN_OFF if mua_ban_init=="Mua" else C_BAN_ON, fg="#8b949e" if mua_ban_init=="Mua" else "white", bd=0)
        btn_mua.place(relx=0, rely=0, relwidth=0.5, relheight=1); btn_ban.place(relx=0.5, rely=0, relwidth=0.5, relheight=1)

        btn_mua.config(command=lambda: (mua_ban_var.set("Mua"), btn_mua.config(bg=C_MUA_ON, fg="white"), btn_ban.config(bg=C_BAN_OFF, fg="#8b949e")))
        btn_ban.config(command=lambda: (mua_ban_var.set("Bán"), btn_mua.config(bg=C_MUA_OFF, fg="#8b949e"), btn_ban.config(bg=C_BAN_ON, fg="white")))

        row_data = {"frame": row_f, "slot": slot_var, "mua_ban": mua_ban_var, "pos": tk.StringVar(value="")}
        del_f = tk.Frame(row_f, bg="#0d1117", width=_W_DEL, height=22); del_f.pack_propagate(False); del_f.pack(side="left", padx=(_PAD_MID, 0))
        if not is_first:
            btn_del = tk.Button(del_f, text="X", font=("Consolas", 9, "bold"), bg="#da3633", fg="white", bd=0, command=lambda: self._remove_insert_row(row_data))
            btn_del.pack(fill="both", expand=True); add_hover_effect(btn_del, "#f85149", "#da3633")

        self.insert_rows_data.append(row_data)
        if not is_first: self._update_insert_window_height()

    def _add_insert_row_auto(self):
        _MAX_ROWS_YT = 13
        if len(self.insert_rows_data) >= _MAX_ROWS_YT: return
        used = {int(r["slot"].get()) for r in self.insert_rows_data}
        next_slot = next((i for i in range(1, _MAX_ROWS_YT + 1) if i not in used), 1)
        self._add_insert_row(is_first=False, slot_num=next_slot)

    def _remove_insert_row(self, rd):
        rd["frame"].destroy(); self.insert_rows_data.remove(rd); self._update_insert_window_height()

    def _update_insert_window_height(self):
        from ui_insert_mua import _WIN_W, _WIN_H_BASE, _ROW_H
        h = _WIN_H_BASE + max(0, len(self.insert_rows_data) - 1) * _ROW_H
        self.root.geometry(f"{_WIN_W}x{h}+{self.sw - _WIN_W}+0")

    def _fetch_time_offset_async(self):
        def _worker():
            import datetime
            try:
                inet = _fetch_internet_time()
                self._insert_time_offset = inet - datetime.datetime.now()
            except: self._insert_time_offset = None
            self.root.after(0, self._start_insert_clock)
        threading.Thread(target=_worker, daemon=True).start()

    def _start_insert_clock(self):
        self._insert_clock_running = True; self._tick_insert_clock()

    def _tick_insert_clock(self):
        if not self._insert_clock_running: return
        if not self.insert_frame.winfo_ismapped():
            self.root.after(500, self._tick_insert_clock); return
        import datetime
        now = datetime.datetime.now()
        if self._insert_time_offset: now = now + self._insert_time_offset
        h, m, s = now.hour, now.minute, now.second
        self.lbl_clock.config(text=f"{h:02d}:{m:02d}:{s:02d}")
        
        chan_le = "Chẵn" if h % 2 == 0 else "Lẻ"
        self.lbl_chan_le.config(text=f"{chan_le}  {m:02d}", fg="#50fa7b" if h % 2 == 0 else "#ff79c6")
        self.root.after(1000, self._tick_insert_clock)

    def log_insert(self, msg, tag=None, update_last=False): self._insert_log_queue.append((msg, tag, update_last))
    
    def _drain_insert_log(self):
        if self._insert_log_queue:
            batch = self._insert_log_queue[:20]; del self._insert_log_queue[:20]
            for item in batch: 
                msg, tag = item[0], item[1]
                update_last = item[2] if len(item) > 2 else False
                self._insert_log(self.insert_log_b, msg, tag, update_last)
        self.root.after(100, self._drain_insert_log)

    def on_insert_finished(self, completed=False):
        self.is_running = False
        if hasattr(self, 'btn_start_insert'):
            self.btn_start_insert.config(state="normal", bg="#238636")
        if hasattr(self, 'btn_start_insert_mua'):
            self.btn_start_insert_mua.config(state="normal", bg="#238636")
        if hasattr(self, 'unlock_ui'):
            self.unlock_ui()
        if hasattr(self, 'lbl_esc_hint_insert'):
            self.lbl_esc_hint_insert.pack_forget()
        if hasattr(self, 'lbl_esc_hint_insert_mua'):
            self.lbl_esc_hint_insert_mua.pack_forget()
        if not completed:
            if hasattr(self, 'log_insert'):
                self.log_insert("\n🛑 ĐANG DỪNG...", "orange")
            if hasattr(self, 'log_insert_mua'):
                self.log_insert_mua("\n🛑 ĐANG DỪNG...", "orange")

    def start_insert(self):
        if self.is_running: return
        if not self.insert_rows_data: return
        slot_configs = [{"slot": r["slot"].get(), "mua_ban": r["mua_ban"].get(), "pos_var": r["pos"]} for r in self.insert_rows_data]
        self.insert_log_b.delete("1.0", "end")
        self.is_running = True; self.btn_start_insert.config(state="disabled", bg="#484f58")
        if hasattr(self, 'lock_ui'): self.lock_ui()
        self.lbl_esc_hint_insert.pack(side="left", pady=(2, 0))

        from bot import FCOnlineBot
        
        # Bắt đúng hàm phát âm thanh từ giao diện gốc
        sound_func = getattr(self, 'play_success_sound', lambda *a, **kw: None)
        
        self.bot = FCOnlineBot(self.log_insert, lambda *a: None, self.on_insert_finished, {}, None, lambda ovr: None, sound_func, lambda *a: None, False)
        self.bot.root = self.root
        
        do_notify = self.insert_notify_var.get()
        target_func = self.bot.run_insert
        threading.Thread(target=target_func, args=(slot_configs,), kwargs={"do_notify": do_notify}, daemon=True).start()
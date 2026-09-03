import os
import sys

# Suppress MediaPipe / TensorFlow Lite C++ verbose logs
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["GLOG_minloglevel"] = "3"

import time
import webbrowser
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk

# High-DPI Awareness for Windows
try:
    import ctypes
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

from storage import StorageManager
from audio_alerts import AudioPlayer
from cv_tracker import AttentionTracker
from mini_widget import MiniWidget

APP_VERSION = "1.1.0"

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class FocusApp:
    def __init__(self, root):
        self.root = root
        self.root.title(f"Focus Widget v{APP_VERSION} 🎯")
        self.root.geometry("460x560")
        self.root.minsize(440, 520)
        self.root.resizable(True, True)

        # Initialize Engines
        self.storage = StorageManager()
        self.audio = AudioPlayer(storage=self.storage)
        self.tracker = AttentionTracker(storage=self.storage, on_status_change=self._on_tracker_status_change)
        
        # Color Palette
        self.colors = {
            "bg": "#121214",
            "card": "#1B1B1F",
            "border": "#2C2C35",
            "fg": "#FFFFFF",
            "fg_muted": "#8E8E9F",
            "accent": "#00FF41",      # Neon Green (Focused)
            "distracted": "#FF2A6D",  # Neon Red (Distracted)
            "pause": "#FFB000",       # Amber (Paused)
            "break": "#00CCFF",       # Cyan (Break)
            "button": "#27272F",
            "button_hover": "#363640",
            "stop": "#E05353"
        }

        self.root.configure(bg=self.colors["bg"])
        self.setup_styles()

        # State Machine
        self.is_running = False
        self.is_focused = True
        self.is_break = False           # Pomodoro break phase
        self.mode = self.storage.get_setting("mode", "stopwatch")  # stopwatch | pomodoro | countdown
        self.elapsed_time = 0.0         # Seconds focused
        self.remaining_time = 0.0       # For countdown / pomodoro
        self.last_tick_time = None
        self.pomodoro_cycle_count = 0
        
        # Stats accumulation buffer
        self.last_stat_sync_time = time.time()
        self.focused_buffer = 0.0
        self.distracted_buffer = 0.0

        # Calibration window reference
        self.calib_win = None
        self.calib_canvas = None
        self.calib_photo = None

        # Mini-Widget
        self.mini_widget = MiniWidget(
            parent=self.root,
            storage=self.storage,
            on_toggle=self.toggle_session,
            on_restore=self.restore_from_mini
        )

        # Build GUI
        self.build_ui()

        # Window state
        is_topmost = self.storage.get_setting("ui.always_on_top", False)
        self.root.wm_attributes("-topmost", is_topmost)
        if is_topmost:
            self.pin_btn.config(foreground=self.colors["accent"])

        # Start Camera Tracker
        self.tracker.start()

        # Main Update Loop
        self.update_loop()

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')

        style.configure("Main.TFrame", background=self.colors["bg"])
        style.configure("Card.TFrame", background=self.colors["card"])
        
        # Labels
        style.configure("Title.TLabel", background=self.colors["bg"], foreground=self.colors["fg"], font=("Segoe UI", 12, "bold"))
        style.configure("Status.TLabel", background=self.colors["card"], foreground=self.colors["fg"], font=("Segoe UI", 13, "bold"))
        style.configure("Timer.TLabel", background=self.colors["card"], foreground=self.colors["accent"], font=("Consolas", 42, "bold"))
        style.configure("ModeBadge.TLabel", background=self.colors["card"], foreground=self.colors["fg_muted"], font=("Segoe UI", 8, "bold"))
        style.configure("Muted.TLabel", background=self.colors["card"], foreground=self.colors["fg_muted"], font=("Segoe UI", 9))
        style.configure("StatValue.TLabel", background=self.colors["card"], foreground=self.colors["fg"], font=("Segoe UI", 11, "bold"))

        # Buttons
        style.configure("Action.TButton", 
                        background=self.colors["accent"], 
                        foreground="#000000", 
                        font=("Segoe UI", 11, "bold"),
                        borderwidth=0)
        style.map("Action.TButton", background=[("active", "#32CD32")])

        style.configure("Stop.TButton", 
                        background=self.colors["button"], 
                        foreground=self.colors["stop"], 
                        font=("Segoe UI", 12, "bold"),
                        borderwidth=0)
        style.map("Stop.TButton", 
                  background=[("active", self.colors["button_hover"]), ("disabled", "#1E1E24")],
                  foreground=[("disabled", "#44444E")])

        style.configure("Icon.TButton", 
                        background=self.colors["bg"], 
                        foreground=self.colors["fg_muted"], 
                        font=("Segoe UI", 10),
                        borderwidth=0)
        style.map("Icon.TButton", foreground=[("active", self.colors["fg"])])

        # Dialog styles
        style.configure("Dialog.TFrame", background=self.colors["bg"])
        style.configure("DialogTitle.TLabel", background=self.colors["bg"], foreground=self.colors["accent"], font=("Segoe UI", 14, "bold"))

    def build_ui(self):
        # 1. Top Navigation / Header Bar
        self.top_bar = tk.Frame(self.root, bg=self.colors["bg"])
        self.top_bar.pack(fill="x", padx=16, pady=(12, 6))

        title_frame = tk.Frame(self.top_bar, bg=self.colors["bg"])
        title_frame.pack(side="left")

        app_title = tk.Label(title_frame, text="FOCUS WIDGET", font=("Segoe UI", 11, "bold"),
                             bg=self.colors["bg"], fg=self.colors["fg"])
        app_title.pack(side="left")

        version_badge = tk.Label(title_frame, text=f"v{APP_VERSION}", font=("Segoe UI", 8),
                                 bg=self.colors["bg"], fg=self.colors["fg_muted"])
        version_badge.pack(side="left", padx=(5, 0))

        # Action icons on top right
        icons_frame = tk.Frame(self.top_bar, bg=self.colors["bg"])
        icons_frame.pack(side="right")

        self.pin_btn = tk.Button(icons_frame, text="📌", font=("Segoe UI Emoji", 10),
                                 bg=self.colors["bg"], fg=self.colors["fg_muted"],
                                 activebackground=self.colors["bg"], activeforeground=self.colors["accent"],
                                 bd=0, cursor="hand2", command=self.toggle_pin)
        self.pin_btn.pack(side="left", padx=3)

        self.mini_btn = tk.Button(icons_frame, text="🗗", font=("Segoe UI Emoji", 10),
                                  bg=self.colors["bg"], fg=self.colors["fg_muted"],
                                  activebackground=self.colors["bg"], activeforeground=self.colors["fg"],
                                  bd=0, cursor="hand2", command=self.switch_to_mini)
        self.mini_btn.pack(side="left", padx=3)

        self.calib_btn = tk.Button(icons_frame, text="📷", font=("Segoe UI Emoji", 10),
                                   bg=self.colors["bg"], fg=self.colors["fg_muted"],
                                   activebackground=self.colors["bg"], activeforeground=self.colors["fg"],
                                   bd=0, cursor="hand2", command=self.open_calibration)
        self.calib_btn.pack(side="left", padx=3)

        self.settings_btn = tk.Button(icons_frame, text="⚙", font=("Segoe UI", 10),
                                      bg=self.colors["bg"], fg=self.colors["fg_muted"],
                                      activebackground=self.colors["bg"], activeforeground=self.colors["fg"],
                                      bd=0, cursor="hand2", command=self.open_settings)
        self.settings_btn.pack(side="left", padx=3)

        self.about_btn = tk.Button(icons_frame, text="?", font=("Segoe UI", 10, "bold"),
                                   bg=self.colors["bg"], fg=self.colors["fg_muted"],
                                   activebackground=self.colors["bg"], activeforeground=self.colors["fg"],
                                   bd=0, cursor="hand2", command=self.show_about)
        self.about_btn.pack(side="left", padx=3)

        # 2. Mode Selector (Segmented Bar)
        self.mode_frame = tk.Frame(self.root, bg=self.colors["card"], highlightbackground=self.colors["border"], highlightthickness=1)
        self.mode_frame.pack(fill="x", padx=16, pady=(6, 10))

        self.mode_buttons = {}
        modes = [("stopwatch", "Stopwatch"), ("pomodoro", "Pomodoro"), ("countdown", "Countdown")]
        for m_key, m_label in modes:
            btn = tk.Button(self.mode_frame, text=m_label, font=("Segoe UI", 9, "bold"),
                            bg=self.colors["card"], fg=self.colors["fg_muted"],
                            activebackground=self.colors["button_hover"], activeforeground=self.colors["fg"],
                            bd=0, relief="flat", pady=6, cursor="hand2",
                            command=lambda k=m_key: self.set_mode(k))
            btn.pack(side="left", expand=True, fill="x")
            self.mode_buttons[m_key] = btn

        self._refresh_mode_buttons()

        # 3. Primary Center Card (Status + Timer + Controls)
        self.center_card = tk.Frame(self.root, bg=self.colors["card"], highlightbackground=self.colors["border"], highlightthickness=1)
        self.center_card.pack(fill="both", expand=True, padx=16, pady=(0, 10))

        # Status Header
        self.status_box = tk.Frame(self.center_card, bg=self.colors["card"])
        self.status_box.pack(pady=(20, 8))

        self.status_icon = tk.Label(self.status_box, text="⚪", font=("Segoe UI Emoji", 16),
                                    bg=self.colors["card"], fg="#888888")
        self.status_icon.pack(side="left", padx=(0, 8))

        self.status_text = tk.Label(self.status_box, text="Ready", font=("Segoe UI", 12, "bold"),
                                    bg=self.colors["card"], fg=self.colors["fg"])
        self.status_text.pack(side="left")

        # Mode Badge (e.g., "FOCUS SESSION" or "SHORT BREAK")
        self.mode_badge = tk.Label(self.center_card, text="CONTINUOUS DEEP WORK", font=("Segoe UI", 8, "bold"),
                                   bg=self.colors["card"], fg=self.colors["fg_muted"])
        self.mode_badge.pack(pady=(0, 4))

        # Timer Display
        self.timer_label = tk.Label(self.center_card, text="00:00:00", font=("Consolas", 42, "bold"),
                                    bg=self.colors["card"], fg=self.colors["accent"])
        self.timer_label.pack(pady=(4, 15))

        # Pomodoro Cycle Dots (Shown only in Pomodoro mode)
        self.dots_frame = tk.Frame(self.center_card, bg=self.colors["card"])
        self.dots_frame.pack(pady=(0, 15))
        self.cycle_dots_labels = []
        for i in range(4):
            lbl = tk.Label(self.dots_frame, text="○", font=("Segoe UI", 13),
                           bg=self.colors["card"], fg=self.colors["fg_muted"])
            lbl.pack(side="left", padx=4)
            self.cycle_dots_labels.append(lbl)

        # Control Buttons Row
        self.btn_row = tk.Frame(self.center_card, bg=self.colors["card"])
        self.btn_row.pack(side="bottom", pady=20, fill="x", padx=25)

        # Toggle Button (Start / Pause)
        self.toggle_btn = tk.Button(self.btn_row, text="START ▶", font=("Segoe UI", 11, "bold"),
                                    bg=self.colors["accent"], fg="#000000",
                                    activebackground="#32CD32", activeforeground="#000000",
                                    bd=0, relief="flat", pady=8, cursor="hand2",
                                    command=self.toggle_session)
        self.toggle_btn.pack(side="left", expand=True, fill="x", padx=(0, 8))

        # Stop / Reset Button
        self.stop_btn = tk.Button(self.btn_row, text="⏹", font=("Segoe UI", 12, "bold"),
                                  bg=self.colors["button"], fg=self.colors["stop"],
                                  activebackground=self.colors["button_hover"], activeforeground=self.colors["stop"],
                                  bd=0, relief="flat", width=4, pady=6, cursor="hand2",
                                  command=self.stop_session)
        self.stop_btn.pack(side="left", padx=(0, 8))
        self.stop_btn.config(state="disabled")

        # Skip Phase Button (for Pomodoro / Countdown)
        self.skip_btn = tk.Button(self.btn_row, text="⏭", font=("Segoe UI", 11, "bold"),
                                  bg=self.colors["button"], fg=self.colors["fg_muted"],
                                  activebackground=self.colors["button_hover"], activeforeground=self.colors["fg"],
                                  bd=0, relief="flat", width=4, pady=6, cursor="hand2",
                                  command=self.skip_phase)
        self.skip_btn.pack(side="left")

        # 4. Daily Statistics Card
        self.stats_card = tk.Frame(self.root, bg=self.colors["card"], highlightbackground=self.colors["border"], highlightthickness=1)
        self.stats_card.pack(fill="x", padx=16, pady=(0, 16))

        stats_inner = tk.Frame(self.stats_card, bg=self.colors["card"])
        stats_inner.pack(fill="x", padx=15, pady=10)

        # Stat Item 1: Focused Time
        col1 = tk.Frame(stats_inner, bg=self.colors["card"])
        col1.pack(side="left", expand=True)
        tk.Label(col1, text="TODAY'S FOCUS", font=("Segoe UI", 8, "bold"), bg=self.colors["card"], fg=self.colors["fg_muted"]).pack(anchor="w")
        self.stat_focus_val = tk.Label(col1, text="0h 00m", font=("Segoe UI", 11, "bold"), bg=self.colors["card"], fg=self.colors["accent"])
        self.stat_focus_val.pack(anchor="w")

        # Stat Item 2: Distracted
        col2 = tk.Frame(stats_inner, bg=self.colors["card"])
        col2.pack(side="left", expand=True)
        tk.Label(col2, text="DISTRACTED", font=("Segoe UI", 8, "bold"), bg=self.colors["card"], fg=self.colors["fg_muted"]).pack(anchor="w")
        self.stat_distract_val = tk.Label(col2, text="0m", font=("Segoe UI", 11, "bold"), bg=self.colors["card"], fg=self.colors["distracted"])
        self.stat_distract_val.pack(anchor="w")

        # Stat Item 3: Focus Score
        col3 = tk.Frame(stats_inner, bg=self.colors["card"])
        col3.pack(side="left", expand=True)
        tk.Label(col3, text="SCORE", font=("Segoe UI", 8, "bold"), bg=self.colors["card"], fg=self.colors["fg_muted"]).pack(anchor="w")
        self.stat_score_val = tk.Label(col3, text="100%", font=("Segoe UI", 11, "bold"), bg=self.colors["card"], fg=self.colors["fg"])
        self.stat_score_val.pack(anchor="w")

        # Stat Item 4: Pomodoros
        col4 = tk.Frame(stats_inner, bg=self.colors["card"])
        col4.pack(side="left", expand=True)
        tk.Label(col4, text="POMOS", font=("Segoe UI", 8, "bold"), bg=self.colors["card"], fg=self.colors["fg_muted"]).pack(anchor="w")
        self.stat_pomo_val = tk.Label(col4, text="0", font=("Segoe UI", 11, "bold"), bg=self.colors["card"], fg="#FFAA00")
        self.stat_pomo_val.pack(anchor="w")

        self.refresh_stats_ui()
        self._init_timer_for_mode()

    def _refresh_mode_buttons(self):
        for m_key, btn in self.mode_buttons.items():
            if m_key == self.mode:
                btn.config(bg=self.colors["border"], fg=self.colors["fg"])
            else:
                btn.config(bg=self.colors["card"], fg=self.colors["fg_muted"])

    def set_mode(self, new_mode):
        if self.is_running:
            if not messagebox.askyesno("Switch Mode", "Active session is running. Reset and change mode?"):
                return
            self.stop_session()

        self.mode = new_mode
        self.storage.set_setting("mode", new_mode)
        self._refresh_mode_buttons()
        self._init_timer_for_mode()

    def _init_timer_for_mode(self):
        self.is_break = False
        if self.mode == "stopwatch":
            self.elapsed_time = 0.0
            self.mode_badge.config(text="CONTINUOUS DEEP WORK")
            self.dots_frame.pack_forget()
            self.skip_btn.pack_forget()
            self.timer_label.config(text="00:00:00")
        elif self.mode == "pomodoro":
            work_mins = int(self.storage.get_setting("pomodoro.work_minutes", 25))
            self.remaining_time = work_mins * 60.0
            self.mode_badge.config(text=f"POMODORO FOCUS ({work_mins}m)")
            self.dots_frame.pack(pady=(0, 15))
            self.skip_btn.pack(side="left")
            self._update_pomodoro_dots()
            self._format_remaining_display()
        elif self.mode == "countdown":
            mins = int(self.storage.get_setting("countdown_minutes", 30))
            self.remaining_time = mins * 60.0
            self.mode_badge.config(text=f"TARGET COUNTDOWN ({mins}m)")
            self.dots_frame.pack_forget()
            self.skip_btn.pack_forget()
            self._format_remaining_display()

    def _format_remaining_display(self):
        rem = max(0, int(self.remaining_time))
        hours, remainder = divmod(rem, 3600)
        mins, secs = divmod(remainder, 60)
        if hours > 0:
            self.timer_label.config(text=f"{hours:02}:{mins:02}:{secs:02}")
        else:
            self.timer_label.config(text=f"{mins:02}:{secs:02}")

    def _update_pomodoro_dots(self):
        cycles = self.pomodoro_cycle_count % 4
        for i in range(4):
            if i < cycles:
                self.cycle_dots_labels[i].config(text="●", fg=self.colors["accent"])
            else:
                self.cycle_dots_labels[i].config(text="○", fg=self.colors["fg_muted"])

    def toggle_pin(self):
        current = self.storage.get_setting("ui.always_on_top", False)
        new_val = not current
        self.storage.set_setting("ui.always_on_top", new_val)
        self.root.wm_attributes("-topmost", new_val)
        self.pin_btn.config(foreground=self.colors["accent"] if new_val else self.colors["fg_muted"])

    def switch_to_mini(self):
        self.root.withdraw()
        self.mini_widget.show()

    def restore_from_mini(self):
        self.root.deiconify()
        self.root.lift()

    def toggle_session(self):
        if self.is_running:
            # === PAUSE ===
            self.is_running = False
            self.last_tick_time = None
            self.toggle_btn.config(text="RESUME ▶", bg=self.colors["accent"])
            self.status_text.config(text="PAUSED", fg=self.colors["pause"])
            self.status_icon.config(text="⏸️", fg=self.colors["pause"])
            self._sync_stats_to_storage()
        else:
            # === START ===
            self.is_running = True
            self.last_tick_time = time.time()
            self.toggle_btn.config(text="PAUSE ❚❚", bg=self.colors["pause"])
            self.stop_btn.config(state="normal")
            self._update_status_display()

    def stop_session(self):
        self.is_running = False
        self.last_tick_time = None
        self._sync_stats_to_storage()
        self._init_timer_for_mode()
        
        self.toggle_btn.config(text="START ▶", bg=self.colors["accent"])
        self.stop_btn.config(state="disabled")
        self.status_text.config(text="Ready", fg=self.colors["fg"])
        self.status_icon.config(text="⚪", fg="#888888")
        self.timer_label.config(fg=self.colors["accent"])

    def skip_phase(self):
        if self.mode != "pomodoro":
            return
        if not self.is_break:
            self._transition_to_break()
        else:
            self._transition_to_work()

    def _transition_to_break(self):
        self.is_break = True
        self.pomodoro_cycle_count += 1
        self.storage.record_pomodoro()
        self.refresh_stats_ui()
        self.audio.play_complete()

        # Check for long break
        cycles_before_long = int(self.storage.get_setting("pomodoro.cycles_before_long", 4))
        if self.pomodoro_cycle_count % cycles_before_long == 0:
            break_mins = int(self.storage.get_setting("pomodoro.long_break_minutes", 15))
            self.mode_badge.config(text=f"LONG BREAK ({break_mins}m)")
        else:
            break_mins = int(self.storage.get_setting("pomodoro.break_minutes", 5))
            self.mode_badge.config(text=f"SHORT BREAK ({break_mins}m)")

        self.remaining_time = break_mins * 60.0
        self._update_pomodoro_dots()
        self._format_remaining_display()
        self._update_status_display()

    def _transition_to_work(self):
        self.is_break = False
        self.audio.play_break_done()
        work_mins = int(self.storage.get_setting("pomodoro.work_minutes", 25))
        self.remaining_time = work_mins * 60.0
        self.mode_badge.config(text=f"POMODORO FOCUS ({work_mins}m)")
        self._update_pomodoro_dots()
        self._format_remaining_display()
        self._update_status_display()

    def _on_tracker_status_change(self, is_focused):
        self.is_focused = is_focused
        if self.is_running and not self.is_break:
            if not is_focused:
                self.audio.play_distraction()
            else:
                self.audio.play_refocus()

    def update_loop(self):
        now = time.time()

        if self.is_running and self.last_tick_time is not None:
            delta = now - self.last_tick_time
            self.last_tick_time = now

            if self.mode == "stopwatch":
                if self.tracker.camera_available:
                    if self.is_focused:
                        self.elapsed_time += delta
                        self.focused_buffer += delta
                    else:
                        self.distracted_buffer += delta
                else:
                    # Manual mode always tracks
                    self.elapsed_time += delta
                    self.focused_buffer += delta

                total_seconds = int(self.elapsed_time)
                hours, remainder = divmod(total_seconds, 3600)
                mins, secs = divmod(remainder, 60)
                time_str = f"{hours:02}:{mins:02}:{secs:02}"
                self.timer_label.config(text=time_str)

            elif self.mode in ("pomodoro", "countdown"):
                if self.is_break:
                    # During break, camera attention tracking is disabled
                    self.remaining_time -= delta
                    if self.remaining_time <= 0:
                        self.remaining_time = 0
                        self._transition_to_work()
                else:
                    # Work phase
                    if not self.tracker.camera_available or self.is_focused:
                        self.remaining_time -= delta
                        self.focused_buffer += delta
                    else:
                        self.distracted_buffer += delta

                    if self.remaining_time <= 0:
                        self.remaining_time = 0
                        if self.mode == "pomodoro":
                            self._transition_to_break()
                        else:
                            # Countdown complete
                            self.audio.play_complete()
                            self.stop_session()
                            messagebox.showinfo("Focus Widget", "Countdown target complete! Outstanding work!")

                self._format_remaining_display()

            self._update_status_display()

            # Sync stats buffer periodically (every 5 seconds)
            if now - self.last_stat_sync_time > 5.0:
                self._sync_stats_to_storage()

        # Update Mini-Widget
        if self.mini_widget.is_visible():
            self._sync_mini_widget()

        # Update Calibration Feed if open
        if self.calib_win is not None and self.calib_win.winfo_exists():
            self._update_calibration_view()

        self.root.after(80, self.update_loop)

    def _update_status_display(self):
        if not self.is_running:
            return

        if self.is_break:
            self.status_text.config(text="BREAK TIME ☕", fg=self.colors["break"])
            self.status_icon.config(text="☕", fg=self.colors["break"])
            self.timer_label.config(fg=self.colors["break"])
        elif not self.tracker.camera_available:
            self.status_text.config(text="MANUAL ACTIVE", fg=self.colors["break"])
            self.status_icon.config(text="⏱️", fg=self.colors["break"])
            self.timer_label.config(fg=self.colors["break"])
        elif self.is_focused:
            self.status_text.config(text="FOCUSED", fg=self.colors["accent"])
            self.status_icon.config(text="👁️", fg=self.colors["accent"])
            self.timer_label.config(fg=self.colors["accent"])
        else:
            self.status_text.config(text="DISTRACTED", fg=self.colors["distracted"])
            self.status_icon.config(text="❌", fg=self.colors["distracted"])
            self.timer_label.config(fg=self.colors["distracted"])

    def _sync_mini_widget(self):
        current_time_str = self.timer_label.cget("text")
        mode_str = self.mode if not self.is_break else "BREAK"
        
        if not self.is_running:
            color = self.colors["pause"]
            dot_color = self.colors["pause"]
        elif self.is_break:
            color = self.colors["break"]
            dot_color = self.colors["break"]
        elif self.is_focused:
            color = self.colors["accent"]
            dot_color = self.colors["accent"]
        else:
            color = self.colors["distracted"]
            dot_color = self.colors["distracted"]

        self.mini_widget.update_display(current_time_str, mode_str, color, dot_color, self.is_running)

    def _sync_stats_to_storage(self):
        if self.focused_buffer > 0 or self.distracted_buffer > 0:
            self.storage.record_time(self.focused_buffer, self.distracted_buffer)
            self.focused_buffer = 0.0
            self.distracted_buffer = 0.0
            self.last_stat_sync_time = time.time()
            self.refresh_stats_ui()

    def refresh_stats_ui(self):
        stats = self.storage.get_today_stats()
        focus_sec = int(stats["focused_seconds"])
        distract_sec = int(stats["distracted_seconds"])

        f_h, f_m = divmod(focus_sec // 60, 60)
        d_m = distract_sec // 60

        self.stat_focus_val.config(text=f"{f_h}h {f_m:02}m")
        self.stat_distract_val.config(text=f"{d_m}m")
        self.stat_score_val.config(text=f"{stats['focus_score']}%")
        self.stat_pomo_val.config(text=str(stats["completed_pomodoros"]))

    # --- CALIBRATION PREVIEW MODAL ---
    def open_calibration(self):
        if self.calib_win is not None and self.calib_win.winfo_exists():
            self.calib_win.lift()
            return

        self.tracker.set_calibration_active(True)

        self.calib_win = tk.Toplevel(self.root)
        self.calib_win.title("Camera Calibration & 3D Pose")
        self.calib_win.geometry("560x480")
        self.calib_win.resizable(False, False)
        self.calib_win.configure(bg=self.colors["bg"])
        self.calib_win.protocol("WM_DELETE_WINDOW", self.close_calibration)

        header = tk.Frame(self.calib_win, bg=self.colors["bg"])
        header.pack(fill="x", padx=16, pady=10)

        tk.Label(header, text="3D Head Pose & Attention Calibration", font=("Segoe UI", 12, "bold"),
                 bg=self.colors["bg"], fg=self.colors["fg"]).pack(side="left")

        # Video Canvas
        self.calib_canvas = tk.Canvas(self.calib_win, width=520, height=360, bg="#0D0D0F", highlightthickness=1,
                                      highlightbackground=self.colors["border"])
        self.calib_canvas.pack(padx=16, pady=5)

        footer = tk.Frame(self.calib_win, bg=self.colors["bg"])
        footer.pack(fill="x", padx=16, pady=(8, 12))

        yaw_th = self.storage.get_setting("sensitivity.yaw_threshold", 28.0)
        pitch_th = self.storage.get_setting("sensitivity.pitch_threshold", 20.0)
        grace = self.storage.get_setting("sensitivity.grace_period", 2.0)
        tk.Label(footer, text=f"Thresholds: Yaw ±{yaw_th:.0f}° | Pitch ±{pitch_th:.0f}° | Grace: {grace:.1f}s",
                 font=("Segoe UI", 9), bg=self.colors["bg"], fg=self.colors["fg_muted"]).pack(side="left")

        close_btn = tk.Button(footer, text="Done", font=("Segoe UI", 9, "bold"),
                              bg=self.colors["button"], fg=self.colors["fg"],
                              activebackground=self.colors["button_hover"], activeforeground=self.colors["fg"],
                              bd=0, padx=16, pady=4, cursor="hand2", command=self.close_calibration)
        close_btn.pack(side="right")

    def _update_calibration_view(self):
        frame = self.tracker.get_calibration_frame()
        if frame is not None and self.calib_canvas:
            # Resize frame to canvas dimensions (520x360)
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            rgb_resized = cv2.resize(rgb, (520, 360), interpolation=cv2.INTER_AREA)
            img = Image.fromarray(rgb_resized)
            self.calib_photo = ImageTk.PhotoImage(image=img)
            self.calib_canvas.create_image(0, 0, image=self.calib_photo, anchor="nw")

    def close_calibration(self):
        self.tracker.set_calibration_active(False)
        if self.calib_win is not None:
            self.calib_win.destroy()
            self.calib_win = None
            self.calib_canvas = None
            self.calib_photo = None

    # --- SETTINGS MODAL ---
    def open_settings(self):
        win = tk.Toplevel(self.root)
        win.title("Preferences")
        win.geometry("420x510")
        win.resizable(False, False)
        win.configure(bg=self.colors["bg"])

        # Title
        tk.Label(win, text="Preferences", font=("Segoe UI", 13, "bold"),
                 bg=self.colors["bg"], fg=self.colors["accent"]).pack(anchor="w", padx=20, pady=(20, 10))

        content = tk.Frame(win, bg=self.colors["bg"])
        content.pack(fill="both", expand=True, padx=20)

        # 1. Pomodoro Work Duration
        tk.Label(content, text="Pomodoro Work Duration (minutes):", font=("Segoe UI", 9),
                 bg=self.colors["bg"], fg=self.colors["fg"]).pack(anchor="w", pady=(8, 2))
        work_var = tk.IntVar(value=int(self.storage.get_setting("pomodoro.work_minutes", 25)))
        work_spin = ttk.Spinbox(content, from_=5, to=90, textvariable=work_var, width=10)
        work_spin.pack(anchor="w")

        # 2. Pomodoro Break Duration
        tk.Label(content, text="Pomodoro Short Break (minutes):", font=("Segoe UI", 9),
                 bg=self.colors["bg"], fg=self.colors["fg"]).pack(anchor="w", pady=(8, 2))
        break_var = tk.IntVar(value=int(self.storage.get_setting("pomodoro.break_minutes", 5)))
        break_spin = ttk.Spinbox(content, from_=1, to=30, textvariable=break_var, width=10)
        break_spin.pack(anchor="w")

        # 3. Grace Period Buffer
        tk.Label(content, text="Distraction Grace Period (seconds):", font=("Segoe UI", 9),
                 bg=self.colors["bg"], fg=self.colors["fg"]).pack(anchor="w", pady=(8, 2))
        grace_var = tk.DoubleVar(value=float(self.storage.get_setting("sensitivity.grace_period", 2.0)))
        grace_spin = ttk.Spinbox(content, from_=0.5, to=6.0, increment=0.5, textvariable=grace_var, width=10)
        grace_spin.pack(anchor="w")

        # 4. Head Pose Yaw Threshold
        tk.Label(content, text="Head Turn Sensitivity (Yaw ±degrees):", font=("Segoe UI", 9),
                 bg=self.colors["bg"], fg=self.colors["fg"]).pack(anchor="w", pady=(8, 2))
        yaw_var = tk.DoubleVar(value=float(self.storage.get_setting("sensitivity.yaw_threshold", 28.0)))
        yaw_spin = ttk.Spinbox(content, from_=15.0, to=50.0, increment=2.0, textvariable=yaw_var, width=10)
        yaw_spin.pack(anchor="w")

        # 5. Sound Alerts Checkboxes
        tk.Label(content, text="Audio & Notifications:", font=("Segoe UI", 9, "bold"),
                 bg=self.colors["bg"], fg=self.colors["fg"]).pack(anchor="w", pady=(15, 4))
        
        sound_var = tk.BooleanVar(value=bool(self.storage.get_setting("audio.sound_enabled", True)))
        sound_cb = tk.Checkbutton(content, text="Enable Audio Chimes", variable=sound_var,
                                  bg=self.colors["bg"], fg=self.colors["fg"], selectcolor="#2A2A33",
                                  activebackground=self.colors["bg"], activeforeground=self.colors["fg"])
        sound_cb.pack(anchor="w")

        distract_snd_var = tk.BooleanVar(value=bool(self.storage.get_setting("audio.distraction_alert", True)))
        distract_cb = tk.Checkbutton(content, text="Gentle Distraction Nudge Sound", variable=distract_snd_var,
                                     bg=self.colors["bg"], fg=self.colors["fg"], selectcolor="#2A2A33",
                                     activebackground=self.colors["bg"], activeforeground=self.colors["fg"])
        distract_cb.pack(anchor="w")

        # Save Button
        def _save_settings():
            self.storage.set_setting("pomodoro.work_minutes", work_var.get())
            self.storage.set_setting("pomodoro.break_minutes", break_var.get())
            self.storage.set_setting("sensitivity.grace_period", grace_var.get())
            self.storage.set_setting("sensitivity.yaw_threshold", yaw_var.get())
            self.storage.set_setting("audio.sound_enabled", sound_var.get())
            self.storage.set_setting("audio.distraction_alert", distract_snd_var.get())

            self.tracker.grace_period = float(grace_var.get())
            self.tracker.yaw_threshold = float(yaw_var.get())

            if not self.is_running:
                self._init_timer_for_mode()

            win.destroy()

        btn_box = tk.Frame(win, bg=self.colors["bg"])
        btn_box.pack(side="bottom", fill="x", padx=20, pady=20)

        save_btn = tk.Button(btn_box, text="Save & Apply", font=("Segoe UI", 10, "bold"),
                             bg=self.colors["accent"], fg="#000000", activebackground="#32CD32",
                             bd=0, relief="flat", padx=16, pady=6, cursor="hand2", command=_save_settings)
        save_btn.pack(side="right")

        cancel_btn = tk.Button(btn_box, text="Cancel", font=("Segoe UI", 10),
                               bg=self.colors["button"], fg=self.colors["fg"],
                               activebackground=self.colors["button_hover"], activeforeground=self.colors["fg"],
                               bd=0, relief="flat", padx=14, pady=6, cursor="hand2", command=win.destroy)
        cancel_btn.pack(side="right", padx=(0, 10))

    # --- ABOUT MODAL ---
    def show_about(self):
        about_win = tk.Toplevel(self.root)
        about_win.title("About Focus Widget")
        about_win.geometry("400x280")
        about_win.resizable(False, False)
        about_win.configure(bg=self.colors["bg"])

        try:
            about_win.iconbitmap(resource_path("icon.ico"))
        except Exception:
            pass

        tk.Label(about_win, text=f"Focus Widget v{APP_VERSION} 🎯", font=("Segoe UI", 16, "bold"),
                 bg=self.colors["bg"], fg=self.colors["accent"]).pack(pady=(25, 4))
        
        tk.Label(about_win, text="Smart Attention-Tracking Productivity Timer", font=("Segoe UI", 10, "bold"),
                 bg=self.colors["bg"], fg=self.colors["fg"]).pack(pady=2)

        tk.Label(about_win, text="MediaPipe 3D Pose & Gaze • Trio Timer Modes • Offline Privacy",
                 font=("Segoe UI", 9), bg=self.colors["bg"], fg=self.colors["fg_muted"]).pack(pady=4)

        link_frame = tk.Frame(about_win, bg=self.colors["bg"])
        link_frame.pack(pady=15)
        tk.Label(link_frame, text="Created by MeyTiii • Star on ", font=("Segoe UI", 10),
                 bg=self.colors["bg"], fg="#CCCCCC").pack(side="left")
        link = tk.Label(link_frame, text="GitHub", font=("Segoe UI", 10, "underline"),
                        bg=self.colors["bg"], fg="#4da6ff", cursor="hand2")
        link.pack(side="left")
        link.bind("<Button-1>", lambda e: webbrowser.open("https://github.com/meytiii/focus-widget"))

        tk.Button(about_win, text="Close", font=("Segoe UI", 10, "bold"),
                  bg=self.colors["button"], fg=self.colors["fg"],
                  activebackground=self.colors["button_hover"], activeforeground=self.colors["fg"],
                  bd=0, relief="flat", padx=20, pady=6, cursor="hand2", command=about_win.destroy).pack(side="bottom", pady=20)

    def on_close(self):
        self._sync_stats_to_storage()
        self.tracker.stop()
        if self.calib_win is not None:
            try:
                self.calib_win.destroy()
            except Exception: pass
        if self.mini_widget is not None:
            try:
                self.mini_widget.window.destroy()
            except Exception: pass
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    try:
        icon_path = resource_path("icon.ico")
        root.iconbitmap(icon_path)
    except Exception:
        pass

    app = FocusApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()

import tkinter as tk
from tkinter import ttk

class MiniWidget:
    def __init__(self, parent, storage=None, on_toggle=None, on_restore=None):
        self.parent = parent
        self.storage = storage
        self.on_toggle = on_toggle
        self.on_restore = on_restore

        self.window = tk.Toplevel(parent)
        self.window.title("Focus Mini")
        self.window.overrideredirect(True)
        self.window.wm_attributes("-topmost", True)
        self.window.configure(bg="#141416")

        # Position
        default_x = 100
        default_y = 100
        if storage:
            saved_x = storage.get_setting("ui.mini_x")
            saved_y = storage.get_setting("ui.mini_y")
            if saved_x is not None and saved_y is not None:
                default_x = saved_x
                default_y = saved_y
        
        self.window.geometry(f"240x60+{default_x}+{default_y}")

        # Dragging support
        self._drag_start_x = 0
        self._drag_start_y = 0

        # UI Container
        self.container = tk.Frame(self.window, bg="#1B1B1F", highlightbackground="#2E2E36", highlightthickness=1, cursor="fleur")
        self.container.pack(fill="both", expand=True)

        self.container.bind("<Button-1>", self._start_drag)
        self.container.bind("<B1-Motion>", self._on_drag)
        self.container.bind("<ButtonRelease-1>", self._end_drag)

        # Left: Status glowing dot
        self.canvas_dot = tk.Canvas(self.container, width=24, height=24, bg="#1B1B1F", highlightthickness=0, cursor="fleur")
        self.canvas_dot.pack(side="left", padx=(10, 5))
        self.dot = self.canvas_dot.create_oval(5, 5, 19, 19, fill="#00FF41", outline="")
        self.canvas_dot.bind("<Button-1>", self._start_drag)
        self.canvas_dot.bind("<B1-Motion>", self._on_drag)
        self.canvas_dot.bind("<ButtonRelease-1>", self._end_drag)

        # Middle: Timer and Mode text
        self.text_frame = tk.Frame(self.container, bg="#1B1B1F", cursor="fleur")
        self.text_frame.pack(side="left", fill="both", expand=True)
        self.text_frame.bind("<Button-1>", self._start_drag)
        self.text_frame.bind("<B1-Motion>", self._on_drag)
        self.text_frame.bind("<ButtonRelease-1>", self._end_drag)

        self.timer_label = tk.Label(self.text_frame, text="00:00:00", font=("Consolas", 15, "bold"),
                                    bg="#1B1B1F", fg="#00FF41", cursor="fleur")
        self.timer_label.pack(anchor="w", pady=(6, 0))
        self.timer_label.bind("<Button-1>", self._start_drag)
        self.timer_label.bind("<B1-Motion>", self._on_drag)
        self.timer_label.bind("<ButtonRelease-1>", self._end_drag)

        self.mode_label = tk.Label(self.text_frame, text="STOPWATCH", font=("Segoe UI", 7, "bold"),
                                   bg="#1B1B1F", fg="#888899", cursor="fleur")
        self.mode_label.pack(anchor="w")
        self.mode_label.bind("<Button-1>", self._start_drag)
        self.mode_label.bind("<B1-Motion>", self._on_drag)
        self.mode_label.bind("<ButtonRelease-1>", self._end_drag)

        # Right: Quick Buttons
        self.btn_frame = tk.Frame(self.container, bg="#1B1B1F")
        self.btn_frame.pack(side="right", padx=(5, 8))

        # Play/Pause button
        self.toggle_btn = tk.Button(self.btn_frame, text="▶", font=("Segoe UI", 9, "bold"),
                                    bg="#2B2B33", fg="#FFFFFF", activebackground="#3A3A45",
                                    activeforeground="#FFFFFF", bd=0, width=3, relief="flat",
                                    command=self._handle_toggle)
        self.toggle_btn.pack(side="left", padx=2)

        # Expand button
        self.expand_btn = tk.Button(self.btn_frame, text="⤢", font=("Segoe UI", 10, "bold"),
                                    bg="#222228", fg="#AAAAAA", activebackground="#33333E",
                                    activeforeground="#FFFFFF", bd=0, width=2, relief="flat",
                                    command=self._handle_restore)
        self.expand_btn.pack(side="left", padx=2)

        # Hide initially until toggled by main app
        self.window.withdraw()

    def _start_drag(self, event):
        self._drag_start_x = event.x_root - self.window.winfo_x()
        self._drag_start_y = event.y_root - self.window.winfo_y()

    def _on_drag(self, event):
        new_x = event.x_root - self._drag_start_x
        new_y = event.y_root - self._drag_start_y
        self.window.geometry(f"+{new_x}+{new_y}")

    def _end_drag(self, event):
        if self.storage:
            self.storage.set_setting("ui.mini_x", self.window.winfo_x())
            self.storage.set_setting("ui.mini_y", self.window.winfo_y())

    def _handle_toggle(self):
        if self.on_toggle:
            self.on_toggle()

    def _handle_restore(self):
        self.hide()
        if self.on_restore:
            self.on_restore()

    def show(self):
        self.window.deiconify()
        self.window.lift()

    def hide(self):
        self.window.withdraw()

    def is_visible(self):
        return self.window.winfo_viewable()

    def update_display(self, time_str, mode_name, color, dot_color, is_running):
        self.timer_label.config(text=time_str, fg=color)
        self.mode_label.config(text=mode_name.upper())
        self.canvas_dot.itemconfig(self.dot, fill=dot_color)
        self.toggle_btn.config(text="❚❚" if is_running else "▶")

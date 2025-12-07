import cv2
import mediapipe as mp
import threading
import time
import tkinter as tk
from tkinter import ttk
import sys
import os
import webbrowser

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

class FocusApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Focus Widget 🎯")
        self.root.geometry("400x280")
        self.root.resizable(False, False)
        
        # --- APP ICON ---
        # Set the window icon (top left and taskbar)
        try:
            icon_path = resource_path("icon.ico")
            self.root.iconbitmap(icon_path)
        except Exception:
            print("Icon not found, skipping.")

        # --- STYLING ---
        style = ttk.Style()
        style.theme_use('clam') # 'clam' usually looks cleaner on Windows than default
        
        # Define custom styles
        style.configure("TFrame", background="#f0f0f0")
        style.configure("TLabel", background="#f0f0f0", font=("Segoe UI", 11))
        style.configure("Header.TLabel", font=("Segoe UI", 16, "bold"), foreground="#333")
        style.configure("Timer.TLabel", font=("Consolas", 32, "bold"), foreground="#222")
        style.configure("TButton", font=("Segoe UI", 10, "bold"), padding=6)
        
        self.root.configure(bg="#f0f0f0")

        # --- APP STATE ---
        self.is_running = False
        self.is_focused = False
        self.start_time = 0
        self.elapsed_time = 0
        self.stop_event = threading.Event()

        # --- GUI LAYOUT ---
        main_frame = ttk.Frame(root, padding=20)
        main_frame.pack(fill="both", expand=True)

        # 1. Header with Icon Placeholder
        self.status_container = ttk.Frame(main_frame)
        self.status_container.pack(pady=(0, 15))
        
        self.status_icon = ttk.Label(self.status_container, text="⚪", font=("Segoe UI", 18))
        self.status_icon.pack(side="left", padx=5)
        
        self.status_text = ttk.Label(self.status_container, text="Ready to Focus", style="Header.TLabel")
        self.status_text.pack(side="left")

        # 2. Timer Display
        self.timer_label = ttk.Label(main_frame, text="00:00:00", style="Timer.TLabel")
        self.timer_label.pack(pady=10)

        # 3. Control Buttons Frame
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(pady=20)

        self.toggle_btn = ttk.Button(btn_frame, text="Start Session ▶", command=self.toggle_session, width=15)
        self.toggle_btn.pack(side="left", padx=5)

        self.about_btn = ttk.Button(btn_frame, text="About ℹ", command=self.show_about, width=10)
        self.about_btn.pack(side="left", padx=5)

        # --- COMPUTER VISION SETUP ---
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        self.cap = cv2.VideoCapture(0)

        # --- THREADING ---
        self.cv_thread = threading.Thread(target=self.detect_focus_loop, daemon=True)
        self.cv_thread.start()
        
        self.update_gui_timer()

    def show_about(self):
        """Creates a popup window with a clickable link."""
        about_win = tk.Toplevel(self.root)
        about_win.title("About")
        about_win.geometry("350x180")
        about_win.resizable(False, False)
        about_win.configure(bg="#f0f0f0")
        
        # Set icon for the popup too
        try:
            about_win.iconbitmap(resource_path("icon.ico"))
        except:
            pass

        ttk.Label(about_win, text="Focus Widget 1.0", style="Header.TLabel").pack(pady=(20, 5))
        ttk.Label(about_win, text="Made by MeyTiii", font=("Segoe UI", 10)).pack(pady=2)

        # Link Container
        link_frame = ttk.Frame(about_win)
        link_frame.pack(pady=15)
        
        ttk.Label(link_frame, text="If you enjoyed the app give it a star on ").pack(side="left")
        
        # The Hyperlink
        link = ttk.Label(link_frame, text="GitHub", font=("Segoe UI", 10, "underline"), foreground="blue", cursor="hand2")
        link.pack(side="left")
        link.bind("<Button-1>", lambda e: webbrowser.open("https://github.com/meytiii/focus-widget"))

        ttk.Button(about_win, text="Close", command=about_win.destroy).pack(pady=10)

    def toggle_session(self):
        if self.is_running:
            self.is_running = False
            self.toggle_btn.config(text="Resume ▶")
            self.status_text.config(text="Paused")
            self.status_icon.config(text="⏸️", foreground="orange")
        else:
            self.is_running = True
            self.start_time = time.time() - self.elapsed_time
            self.toggle_btn.config(text="Pause ⏸")

    def detect_focus_loop(self):
        while not self.stop_event.is_set():
            if not self.cap.isOpened():
                time.sleep(1)
                continue
            ret, frame = self.cap.read()
            if not ret:
                continue
            frame.flags.writeable = False
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.face_mesh.process(rgb_frame)

            if results.multi_face_landmarks:
                self.is_focused = True
            else:
                self.is_focused = False
            time.sleep(0.03)

    def update_gui_timer(self):
        if self.is_running:
            if self.is_focused:
                self.elapsed_time = time.time() - self.start_time
                self.status_text.config(text="Focused", foreground="green")
                self.status_icon.config(text="🟢", foreground="green")
            else:
                self.start_time = time.time() - self.elapsed_time
                self.status_text.config(text="Distracted!", foreground="red")
                self.status_icon.config(text="🔴", foreground="red")

            total_seconds = int(self.elapsed_time)
            hours, remainder = divmod(total_seconds, 3600)
            mins, secs = divmod(remainder, 60)
            self.timer_label.config(text=f"{hours:02}:{mins:02}:{secs:02}")
        
        self.root.after(100, self.update_gui_timer)

    def on_close(self):
        self.stop_event.set()
        if self.cap.isOpened():
            self.cap.release()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = FocusApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()

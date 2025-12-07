import cv2
import mediapipe as mp
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox
import sys
import os
import webbrowser

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class FocusApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Focus Widget 🎯")
        self.root.geometry("420x320")
        self.root.resizable(False, False)
        
        # --- APP STATE ---
        self.is_running = False
        self.is_focused = False
        self.camera_available = False
        self.start_time = 0
        self.elapsed_time = 0
        self.stop_event = threading.Event()

        # --- THEME COLORS ---
        self.colors = {
            "bg": "#1E1E1E",          # Dark Grey
            "fg": "#FFFFFF",          # White
            "accent": "#00FF41",      # Neon Green (Matrix style)
            "distracted": "#FF2A6D",  # Neon Red/Pink
            "button": "#333333",      # Button Grey
            "button_text": "#FFFFFF"
        }
        
        self.root.configure(bg=self.colors["bg"])
        self.setup_styles()

        # --- GUI LAYOUT ---
        # Main Container
        self.main_frame = ttk.Frame(root, style="Main.TFrame", padding=20)
        self.main_frame.pack(fill="both", expand=True)

        # 1. Header (Status)
        self.status_frame = ttk.Frame(self.main_frame, style="Main.TFrame")
        self.status_frame.pack(pady=(10, 20))
        
        self.status_icon = ttk.Label(self.status_frame, text="⚪", style="StatusIcon.TLabel")
        self.status_icon.pack(side="left", padx=10)
        
        self.status_text = ttk.Label(self.status_frame, text="System Ready", style="StatusText.TLabel")
        self.status_text.pack(side="left")

        # 2. Timer Display
        self.timer_label = ttk.Label(self.main_frame, text="00:00:00", style="Timer.TLabel")
        self.timer_label.pack(pady=10)

        # 3. Footer (Buttons)
        self.btn_frame = ttk.Frame(self.main_frame, style="Main.TFrame")
        self.btn_frame.pack(side="bottom", pady=10, fill="x")

        self.toggle_btn = ttk.Button(self.btn_frame, text="START FOCUS ▶", command=self.toggle_session, style="Action.TButton")
        self.toggle_btn.pack(side="left", expand=True, fill="x", padx=(0, 5))

        self.about_btn = ttk.Button(self.btn_frame, text="?", command=self.show_about, style="Subtle.TButton", width=4)
        self.about_btn.pack(side="right", padx=(5, 0))

        # --- HARDWARE SETUP ---
        self.init_camera()

        # --- APP LOOP ---
        self.update_gui_timer()

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam') # 'clam' allows us to change button colors easily
        
        # Frames and Backgrounds
        style.configure("Main.TFrame", background=self.colors["bg"])
        
        # Text Styles
        style.configure("StatusIcon.TLabel", background=self.colors["bg"], foreground="#888888", font=("Segoe UI Emoji", 24))
        style.configure("StatusText.TLabel", background=self.colors["bg"], foreground=self.colors["fg"], font=("Segoe UI", 14, "bold"))
        style.configure("Timer.TLabel", background=self.colors["bg"], foreground=self.colors["accent"], font=("Consolas", 42, "bold"))
        
        # Button Styles
        style.configure("Action.TButton", 
                        background=self.colors["accent"], 
                        foreground="#000000", 
                        font=("Segoe UI", 11, "bold"),
                        borderwidth=0,
                        focuscolor="none")
        style.map("Action.TButton", background=[("active", "#32CD32")]) # Darker green on hover

        style.configure("Subtle.TButton", 
                        background=self.colors["button"], 
                        foreground=self.colors["button_text"], 
                        font=("Segoe UI", 11, "bold"),
                        borderwidth=0)

        # Popup Styles (for About window)
        style.configure("Popup.TFrame", background=self.colors["bg"])
        style.configure("PopupTitle.TLabel", background=self.colors["bg"], foreground=self.colors["accent"], font=("Segoe UI", 16, "bold"))
        style.configure("PopupText.TLabel", background=self.colors["bg"], foreground="#CCCCCC", font=("Segoe UI", 10))
        style.configure("Link.TLabel", background=self.colors["bg"], foreground="#4da6ff", font=("Segoe UI", 10, "underline"))

    def init_camera(self):
        """Tries to initialize the camera. If it fails, falls back to manual mode."""
        try:
            # Try index 0, then 1 (sometimes external cams are 1)
            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                raise Exception("Camera index 0 not found")
            
            self.camera_available = True
            
            # Setup MediaPipe only if camera works
            self.mp_face_mesh = mp.solutions.face_mesh
            self.face_mesh = self.mp_face_mesh.FaceMesh(
                max_num_faces=1, refine_landmarks=True,
                min_detection_confidence=0.5, min_tracking_confidence=0.5
            )

            # Start Thread
            self.cv_thread = threading.Thread(target=self.detect_focus_loop, daemon=True)
            self.cv_thread.start()

        except Exception as e:
            print(f"Camera Error: {e}")
            self.camera_available = False
            self.status_text.config(text="No Camera Found")
            self.status_icon.config(text="📷🚫", foreground="orange")
            # If no camera, we default 'is_focused' to True so the timer works manually
            self.is_focused = True 

    def toggle_session(self):
        if self.is_running:
            # STOP
            self.is_running = False
            self.toggle_btn.config(text="RESUME ▶", background=self.colors["accent"])
            self.status_text.config(text="Paused", foreground=self.colors["fg"])
            self.status_icon.config(text="⏸️", foreground="orange")
        else:
            # START
            self.is_running = True
            self.start_time = time.time() - self.elapsed_time
            self.toggle_btn.config(text="PAUSE ❚❚", background="#FFB000") # Amber for pause

    def detect_focus_loop(self):
        while not self.stop_event.is_set():
            if not self.camera_available:
                return # Stop thread if no camera

            ret, frame = self.cap.read()
            if not ret:
                time.sleep(1)
                continue

            frame.flags.writeable = False
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.face_mesh.process(rgb_frame)

            if results.multi_face_landmarks:
                self.is_focused = True
            else:
                self.is_focused = False
            
            time.sleep(0.05)

    def update_gui_timer(self):
        if self.is_running:
            # If Camera is available, rely on is_focused. 
            # If NO Camera, we assume 'True' so it acts like a normal timer.
            if self.is_focused:
                self.elapsed_time = time.time() - self.start_time
                
                if self.camera_available:
                    self.status_text.config(text="FOCUSED", foreground=self.colors["accent"])
                    self.status_icon.config(text="👁️", foreground=self.colors["accent"])
                    self.timer_label.configure(foreground=self.colors["accent"])
                else:
                    self.status_text.config(text="MANUAL MODE", foreground=self.colors["accent"])
            else:
                # Distracted logic
                self.start_time = time.time() - self.elapsed_time
                self.status_text.config(text="DISTRACTED", foreground=self.colors["distracted"])
                self.status_icon.config(text="❌", foreground=self.colors["distracted"])
                self.timer_label.configure(foreground=self.colors["distracted"])

            # Format Time
            total_seconds = int(self.elapsed_time)
            hours, remainder = divmod(total_seconds, 3600)
            mins, secs = divmod(remainder, 60)
            self.timer_label.config(text=f"{hours:02}:{mins:02}:{secs:02}")
        
        self.root.after(100, self.update_gui_timer)

    def show_about(self):
        about_win = tk.Toplevel(self.root)
        about_win.title("About")
        about_win.geometry("380x250")
        about_win.resizable(False, False)
        about_win.configure(bg=self.colors["bg"])
        
        try:
            about_win.iconbitmap(resource_path("icon.ico"))
        except: pass

        # Content
        ttk.Label(about_win, text="Focus Widget v1.0", style="PopupTitle.TLabel").pack(pady=(30, 5))
        ttk.Label(about_win, text="Made by MeyTiii", style="PopupText.TLabel").pack(pady=2)

        link_frame = ttk.Frame(about_win, style="Popup.TFrame")
        link_frame.pack(pady=20)
        
        ttk.Label(link_frame, text="Enjoying the app? Star it on ", style="PopupText.TLabel").pack(side="left")
        
        link = ttk.Label(link_frame, text="GitHub", style="Link.TLabel", cursor="hand2")
        link.pack(side="left")
        link.bind("<Button-1>", lambda e: webbrowser.open("https://github.com/meytiii/focus-widget"))

        ttk.Button(about_win, text="CLOSE", command=about_win.destroy, style="Subtle.TButton").pack(side="bottom", pady=20)

    def on_close(self):
        self.stop_event.set()
        if self.camera_available and self.cap.isOpened():
            self.cap.release()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    
    # Try to set icon immediately
    try:
        icon_path = resource_path("icon.ico")
        root.iconbitmap(icon_path)
    except: pass
    
    app = FocusApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()

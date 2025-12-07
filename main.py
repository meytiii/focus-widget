import cv2
import mediapipe as mp
import threading
import time
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk

class FocusApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Focus Widget 🎯")
        self.root.geometry("350x200")
        self.root.resizable(False, False)
        
        # --- APP STATE ---
        self.is_running = False      # Is the session active?
        self.is_focused = False      # Is the user looking at the screen?
        self.start_time = 0          # Timestamp when session started
        self.elapsed_time = 0        # Total focused time accumulated
        self.stop_event = threading.Event() # To safely stop the camera thread

        # --- GUI LAYOUT ---
        # 1. Main Style
        style = ttk.Style()
        style.configure("TLabel", font=("Helvetica", 12))
        style.configure("TButton", font=("Helvetica", 10))

        # 2. Status Indicator
        self.status_frame = ttk.Frame(root)
        self.status_frame.pack(pady=10)
        
        self.status_icon = ttk.Label(self.status_frame, text="⚪", font=("Helvetica", 16))
        self.status_icon.pack(side="left", padx=5)
        
        self.status_text = ttk.Label(self.status_frame, text="Ready", font=("Helvetica", 12))
        self.status_text.pack(side="left")

        # 3. Timer Display
        self.timer_label = ttk.Label(root, text="00:00:00", font=("Consolas", 30, "bold"))
        self.timer_label.pack(pady=5)

        # 4. Control Button
        self.toggle_btn = ttk.Button(root, text="Start Focus Session", command=self.toggle_session)
        self.toggle_btn.pack(pady=15, ipadx=10, ipady=5)

        # --- COMPUTER VISION SETUP ---
        # Initialize MediaPipe Face Mesh (Lightweight face detector)
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        
        # Open Camera (0 is usually the default webcam)
        self.cap = cv2.VideoCapture(0)

        # --- THREADING ---
        # Run camera logic in a separate background thread so the GUI doesn't freeze
        self.cv_thread = threading.Thread(target=self.detect_focus_loop, daemon=True)
        self.cv_thread.start()
        
        # Start the GUI update loop
        self.update_gui_timer()

    def toggle_session(self):
        """Starts or Pauses the focus timer."""
        if self.is_running:
            # STOPPING
            self.is_running = False
            self.toggle_btn.config(text="Resume Session")
            self.status_text.config(text="Paused")
            self.status_icon.config(text="⏸️", foreground="orange")
        else:
            # STARTING
            self.is_running = True
            # Adjust start_time so the timer continues from where it left off
            self.start_time = time.time() - self.elapsed_time
            self.toggle_btn.config(text="Pause Session")

    def detect_focus_loop(self):
        """
        Background Thread: Reads camera frames and detects faces.
        This runs forever until the app closes.
        """
        while not self.stop_event.is_set():
            if not self.cap.isOpened():
                time.sleep(1)
                continue

            ret, frame = self.cap.read()
            if not ret:
                continue

            # Performance: Mark the image as not writeable to pass by reference
            frame.flags.writeable = False
            # Convert BGR (OpenCV) to RGB (MediaPipe)
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # RUN AI INFERENCE
            results = self.face_mesh.process(rgb_frame)

            # Logic: If any face landmarks are found, we assume user is present/focused
            if results.multi_face_landmarks:
                self.is_focused = True
            else:
                self.is_focused = False
            
            # Sleep slightly to reduce CPU usage (30 FPS is plenty)
            time.sleep(0.03)

    def update_gui_timer(self):
        """Updates the timer on the main thread."""
        if self.is_running:
            if self.is_focused:
                # User is here -> Update time
                self.elapsed_time = time.time() - self.start_time
                
                # Visual Feedback
                self.status_text.config(text="Focused", foreground="green")
                self.status_icon.config(text="🟢", foreground="green")
            else:
                # User is gone -> Don't update time (effectively pauses)
                # We shift start_time forward so the 'gap' isn't counted
                self.start_time = time.time() - self.elapsed_time
                
                # Visual Feedback
                self.status_text.config(text="Distracted!", foreground="red")
                self.status_icon.config(text="🔴", foreground="red")

            # Format time as HH:MM:SS
            total_seconds = int(self.elapsed_time)
            hours, remainder = divmod(total_seconds, 3600)
            mins, secs = divmod(remainder, 60)
            self.timer_label.config(text=f"{hours:02}:{mins:02}:{secs:02}")
        
        # Schedule this function to run again in 100ms
        self.root.after(100, self.update_gui_timer)

    def on_close(self):
        """Cleanup when closing the window."""
        self.stop_event.set()
        if self.cap.isOpened():
            self.cap.release()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = FocusApp(root)
    # Ensure threads close properly when window is closed
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()

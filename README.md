# Focus Widget

A desktop timer that pauses automatically when you look away from your screen.

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![OpenCV](https://img.shields.io/badge/Computer_Vision-OpenCV-green)
![MediaPipe](https://img.shields.io/badge/AI-MediaPipe-orange)
![License](https://img.shields.io/badge/License-MIT-purple)

Focus Widget tracks your attention using your webcam. It estimates head rotation (yaw and pitch) and iris position using MediaPipe Face Mesh and OpenCV. When you look away, turn your head, or leave your desk, the timer pauses. When you return your gaze to the screen, it resumes.

All video processing runs locally on your CPU. Video frames are never recorded, saved, or transmitted.

---

## Features

- **Attention tracking:** Uses 3D head pose estimation and iris position to determine whether you are looking at your screen.
- **Grace period:** A configurable 2-second buffer prevents blinks and brief keyboard checks from interrupting your session.
- **Three timer modes:** Standard count-up stopwatch, Pomodoro intervals with customizable work and break lengths, and a target countdown timer.
- **Break handling:** Attention tracking turns off automatically during Pomodoro breaks so you can step away without triggering distraction alerts.
- **Mini-widget:** Collapses the main window into a small, draggable, always-on-top pill displaying current time and status.
- **Camera calibration:** An optional preview window shows head pose vectors and facial landmarks to help you verify camera angles and thresholds.
- **Audio alerts:** Generates tone chimes for session completion, phase changes, and distraction reminders using the Python standard library.
- **Daily statistics:** Logs daily focused time, distraction time, focus percentage, and completed Pomodoro rounds to a local JSON file.

---

## Tech stack

- **Language:** Python 3.8 to 3.13
- **Interface:** Tkinter and ttk with Windows high-DPI scaling
- **Vision:** OpenCV and MediaPipe (supports both Tasks and legacy Solutions APIs)
- **Audio:** Python wave module and Windows winsound
- **Storage:** Local JSON (`focus_data.json`)

### Project structure

```
focus-widget/
├── main.py             # UI, timer state machine, and application entry point
├── cv_tracker.py       # Face mesh, solvePnP head pose, and gaze tracking
├── mini_widget.py      # Floating, draggable compact overlay
├── audio_alerts.py     # Audio chime synthesis and playback
├── storage.py          # Configuration and daily statistics storage
├── requirements.txt    # Python dependencies
└── icon.ico            # App icon
```

---

## Getting started

### Requirements

Python 3.10 through 3.13 is recommended.

```bash
git clone https://github.com/meytiii/focus-widget.git
cd focus-widget

python -m venv venv
.\venv\Scripts\activate

pip install -r requirements.txt
python main.py
```

---

## Usage

1. **Pick a mode:** Select Stopwatch, Pomodoro, or Countdown from the mode bar.
2. **Start the session:** Click Start. When the camera detects your face facing the monitor, the status shows Focused.
3. **Pausing:** Looking away or turning your head beyond the configured thresholds for more than 2 seconds marks you as Distracted and halts the clock.
4. **Mini mode:** Click the window icon in the top-right header to switch to the floating desktop pill. Click the expand button on the pill to restore the full window.
5. **Calibrate:** Click the camera icon to open the calibration tool and check your detection angles in real time.
6. **Settings:** Click the gear icon to modify Pomodoro intervals, angle tolerances, the grace period, or sound settings.

---

## License

MIT. See [LICENSE](LICENSE) for details.

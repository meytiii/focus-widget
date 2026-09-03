# Focus Widget 🎯

> A smart attention-tracking productivity timer that pauses automatically when you look away.

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![OpenCV](https://img.shields.io/badge/Computer_Vision-OpenCV-green)
![MediaPipe](https://img.shields.io/badge/AI-MediaPipe-orange)
![License](https://img.shields.io/badge/License-MIT-purple)

**Focus Widget** is an offline, privacy-first desktop application designed to keep you in the flow. It leverages your webcam, **MediaPipe Face Mesh**, and **solvePnP 3D pose estimation** to detect your real-time attention. If you turn your head, look away, or leave your desk, the timer pauses smoothly after a grace period. When you refocus, it resumes instantly.

---

## ✨ Features

| Feature | Description |
| :--- | :--- |
| 🎯 **3D Head Pose & Gaze Tracking** | Calculates 3D head rotation (Yaw & Pitch) and iris gaze direction to verify true screen attention. |
| 🛡️ **Smart Grace Period** | 2.0-second debounce buffer ensures natural blinks and quick glances at your keyboard never cause jarring pauses. |
| ⏱️ **Trio Timer Modes** | **Stopwatch** (continuous deep work), **Pomodoro** (25m work / 5m break cycles), and **Custom Countdown** targets. |
| ☕ **Auto-Pause During Breaks** | In Pomodoro mode, tracking automatically turns off during breaks so you can stretch and relax freely. |
| 🗗 **Floating Mini-Widget** | Minimize the dashboard into an always-on-top, draggable compact pill with live timer, pulse dot, and controls. |
| 📷 **On-Demand Calibration** | Toggleable live 3D pose axis and face mesh visualizer to calibrate your angle and verify detection. |
| 🔔 **Synthesized Audio Chimes** | Pleasant bell chimes for session completion and gentle distraction nudges with master mute (zero extra dependencies). |
| 📊 **Daily Focus Metrics** | Automatically logs daily focused hours, distraction time, focus score percentage, and completed Pomodoros in a local JSON file. |
| 🔒 **100% Offline & Private** | All video processing runs strictly on your local CPU. Frames are never stored or sent anywhere. |

---

## 🛠️ Architecture & Tech Stack

* **Language:** Python 3.8+ (Compatible with Python 3.8 – 3.13+)
* **GUI Framework:** Standard Library Tkinter & TTK with High-DPI scaling
* **Computer Vision:** OpenCV (`cv2`) & MediaPipe (Dual support for Tasks API and Solutions API)
* **Audio Engine:** Programmatic acoustic synthesis via built-in `wave` and Windows `winsound`
* **Storage:** Local offline `focus_data.json`

### Project Structure

```
focus-widget/
├── main.py             # Main dashboard, UI lifecycle & state machine
├── cv_tracker.py       # 3D Head pose (solvePnP), iris gaze, debounce & calibration
├── mini_widget.py      # Frameless draggable always-on-top floating pill widget
├── audio_alerts.py     # Synthesized audio chimes & async playback
├── storage.py          # Local JSON settings & daily session statistics
├── requirements.txt    # opencv-python, mediapipe, Pillow
└── icon.ico            # Application icon
```

---

## 🚀 Getting Started

### Prerequisites

You need Python installed (Python 3.8 – 3.13 recommended).

```bash
# Clone the repository
git clone https://github.com/meytiii/focus-widget.git
cd focus-widget

# Install dependencies
pip install -r requirements.txt

# Launch Focus Widget
python main.py
```

---

## 🎮 How to Use

1. **Select a Mode:** Choose **Stopwatch**, **Pomodoro**, or **Countdown** from the top mode bar.
2. **Start Working:** Click **START ▶**. Look at your screen—the widget glows green and marks you **FOCUSED**.
3. **Turn Away:** If you turn your head or leave your desk for longer than 2 seconds, the widget flags **DISTRACTED** and pauses.
4. **Mini Mode:** Click `🗗` in the top right to shrink the widget into a floating desktop pill while you work.
5. **Calibrate:** Click `📷` to open the live 3D pose view and check your angles in real time.
6. **Customize:** Click `⚙` to adjust Pomodoro durations, sensitivity thresholds, grace periods, or audio toggles.

---

## 📄 License

MIT License. See [LICENSE](LICENSE) for details.

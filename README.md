# Focus Widget 🎯

> A smart productivity timer that pauses automatically when you look away.

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![OpenCV](https://img.shields.io/badge/Computer_Vision-OpenCV-green)
![Status](https://img.shields.io/badge/Status-Prototype-orange)

**Focus Widget** is a desktop application designed to keep you in the flow. It uses your webcam and **MediaPipe's Face Mesh** technology to detect your attention in real-time. If you get distracted or leave your desk, the timer stops. When you return, it resumes instantly.

---

## ✨ Features

| Feature | Description |
| :--- | :--- |
| **Smart Tracking** | Uses Computer Vision to detect if a face is present and attentive. |
| **Auto-Pause** | The timer halts the moment you look away or leave the frame. |
| **Privacy First** | All video processing happens **locally** on your CPU. No images are ever saved or sent to the cloud. |
| **Non-Intrusive** | Minimalist GUI that sits quietly in the corner of your screen. |

---

## 🛠️ Tech Stack

*   **Language:** Python 3
*   **GUI Framework:** Tkinter (Custom styled with `ttk`)
*   **Computer Vision:** OpenCV & MediaPipe (Google)
*   **Concurrency:** Python `threading` (to prevent UI freezing during video processing)

---

## 🚀 Getting Started

### Prerequisites

You need Python installed. It is recommended to use a virtual environment.

```bash
# Clone the repo
git clone https://github.com/meytiii/focus-widget.git
cd focus-widget

# Install dependencies
pip install -r requirements.txt

import os
import sys
import time
import math
import threading

# Suppress MediaPipe / TensorFlow Lite C++ verbose logs
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["GLOG_minloglevel"] = "3"

import cv2
import numpy as np

# Try importing mediapipe
try:
    import mediapipe as mp
    HAS_MEDIAPIPE = True
except ImportError:
    HAS_MEDIAPIPE = False

MODEL_POINTS_3D = np.array([
    (0.0, 0.0, 0.0),             # Nose tip (index 1)
    (0.0, -330.0, -65.0),        # Chin (index 152)
    (-225.0, 170.0, -135.0),     # Left eye outer corner (index 33)
    (225.0, 170.0, -135.0),      # Right eye outer corner (index 263)
    (-150.0, -150.0, -125.0),    # Left mouth corner (index 61)
    (150.0, -150.0, -125.0)      # Right mouth corner (index 291)
], dtype=np.float64)

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class AttentionTracker:
    def __init__(self, camera_index=0, storage=None, on_status_change=None):
        self.camera_index = camera_index
        self.storage = storage
        self.on_status_change = on_status_change  # Callback (is_focused, reason)
        
        self.cap = None
        self.camera_available = False
        self.running = False
        self.thread = None
        self.stop_event = threading.Event()
        
        # State
        self.is_focused = False
        self.raw_attentive = False
        self.face_present = False
        self.current_yaw = 0.0
        self.current_pitch = 0.0
        self.current_roll = 0.0
        self.gaze_ratio_left = 0.5
        self.gaze_ratio_right = 0.5
        
        # Debounce / Grace period
        self.distracted_start_time = None
        self.grace_period = 2.0
        self.yaw_threshold = 28.0
        self.pitch_threshold = 20.0
        self._update_thresholds_from_storage()
        
        # Calibration view
        self.calibration_active = False
        self.latest_calibration_frame = None
        self.frame_lock = threading.Lock()
        
        # MediaPipe detector instances
        self.use_tasks_api = False
        self.face_mesh = None
        self.tasks_detector = None
        self._init_mediapipe()

    def _update_thresholds_from_storage(self):
        if self.storage:
            self.grace_period = float(self.storage.get_setting("sensitivity.grace_period", 2.0))
            self.yaw_threshold = float(self.storage.get_setting("sensitivity.yaw_threshold", 28.0))
            self.pitch_threshold = float(self.storage.get_setting("sensitivity.pitch_threshold", 20.0))
            self.camera_index = int(self.storage.get_setting("camera_index", 0))

    def _init_mediapipe(self):
        if not HAS_MEDIAPIPE:
            print("MediaPipe not available.")
            return

        # Check legacy solutions API first
        if hasattr(mp, "solutions") and hasattr(mp.solutions, "face_mesh"):
            try:
                self.face_mesh = mp.solutions.face_mesh.FaceMesh(
                    max_num_faces=1,
                    refine_landmarks=True,
                    min_detection_confidence=0.5,
                    min_tracking_confidence=0.5
                )
                self.use_tasks_api = False
                return
            except Exception as e:
                print(f"Legacy FaceMesh init error: {e}")

        # Fall back to modern tasks API
        try:
            from mediapipe.tasks.python import vision
            from mediapipe.tasks import python as mp_python
            
            task_path = resource_path("face_landmarker.task")
            if not os.path.exists(task_path):
                # Download if missing
                print(f"Downloading face_landmarker.task to {task_path}...")
                import urllib.request
                url = "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/latest/face_landmarker.task"
                urllib.request.urlretrieve(url, task_path)
            
            base_options = mp_python.BaseOptions(model_asset_path=task_path)
            options = vision.FaceLandmarkerOptions(
                base_options=base_options,
                output_facial_transformation_matrixes=True,
                num_faces=1
            )
            self.tasks_detector = vision.FaceLandmarker.create_from_options(options)
            self.use_tasks_api = True
        except Exception as e:
            print(f"MediaPipe Tasks API init error: {e}")

    def start(self):
        if self.running:
            return
        self.stop_event.clear()
        self.running = True
        self.thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)
        self._release_camera()

    def _open_camera(self):
        try:
            if self.cap is not None:
                self.cap.release()
            self.cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW if sys.platform == "win32" else cv2.CAP_ANY)
            if not self.cap.isOpened():
                # Try default backend without CAP_DSHOW
                self.cap = cv2.VideoCapture(self.camera_index)
            if self.cap.isOpened():
                self.camera_available = True
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                return True
            else:
                self.camera_available = False
                return False
        except Exception as e:
            print(f"Camera open error: {e}")
            self.camera_available = False
            return False

    def _release_camera(self):
        if self.cap is not None:
            try:
                self.cap.release()
            except Exception: pass
            self.cap = None
        self.camera_available = False

    def set_calibration_active(self, active: bool):
        self.calibration_active = active
        if not active:
            with self.frame_lock:
                self.latest_calibration_frame = None

    def get_calibration_frame(self):
        with self.frame_lock:
            if self.latest_calibration_frame is not None:
                return self.latest_calibration_frame.copy()
            return None

    def _worker_loop(self):
        while not self.stop_event.is_set():
            if not self.camera_available:
                if not self._open_camera():
                    # Manual fallback mode if camera cannot be opened
                    self.is_focused = True
                    time.sleep(1.0)
                    continue

            ret, frame = self.cap.read()
            if not ret or frame is None:
                time.sleep(0.1)
                continue

            # Flip horizontally for natural mirror feel in calibration
            frame = cv2.flip(frame, 1)
            h, w, _ = frame.shape
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            landmarks = self._extract_landmarks(rgb_frame)

            now = time.time()
            if landmarks is not None and len(landmarks) >= 468:
                self.face_present = True
                yaw, pitch, roll, rvec, tvec, cam_matrix, dist_coeffs, image_points = self._estimate_head_pose(landmarks, w, h)
                self.current_yaw = yaw
                self.current_pitch = pitch
                self.current_roll = roll

                gaze_ok = self._estimate_gaze(landmarks)

                # Check attention condition
                head_ok = (abs(yaw) <= self.yaw_threshold) and (abs(pitch) <= self.pitch_threshold)
                self.raw_attentive = head_ok and gaze_ok

                if self.raw_attentive:
                    self.distracted_start_time = None
                    new_focused = True
                else:
                    if self.distracted_start_time is None:
                        self.distracted_start_time = now
                    elapsed_distracted = now - self.distracted_start_time
                    new_focused = (elapsed_distracted < self.grace_period)

                if self.calibration_active:
                    annotated = self._render_calibration_frame(
                        frame, landmarks, w, h, rvec, tvec, cam_matrix, dist_coeffs, image_points
                    )
                    with self.frame_lock:
                        self.latest_calibration_frame = annotated

            else:
                # No face detected
                self.face_present = False
                self.raw_attentive = False
                if self.distracted_start_time is None:
                    self.distracted_start_time = now
                elapsed_distracted = now - self.distracted_start_time
                new_focused = (elapsed_distracted < self.grace_period)

                if self.calibration_active:
                    annotated = self._render_no_face_frame(frame)
                    with self.frame_lock:
                        self.latest_calibration_frame = annotated

            prev_state = self.is_focused
            self.is_focused = new_focused
            if self.on_status_change and prev_state != self.is_focused:
                self.on_status_change(self.is_focused)

            # Throttle to ~20-25 FPS to conserve CPU
            time.sleep(0.04)

        self._release_camera()

    def _extract_landmarks(self, rgb_frame):
        try:
            if self.use_tasks_api and self.tasks_detector:
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
                result = self.tasks_detector.detect(mp_image)
                if result.face_landmarks and len(result.face_landmarks) > 0:
                    return result.face_landmarks[0]
            elif self.face_mesh:
                rgb_frame.flags.writeable = False
                results = self.face_mesh.process(rgb_frame)
                if results.multi_face_landmarks and len(results.multi_face_landmarks) > 0:
                    return results.multi_face_landmarks[0].landmark
        except Exception as e:
            pass
        return None

    def _estimate_head_pose(self, landmarks, w, h):
        image_points = np.array([
            (landmarks[1].x * w, landmarks[1].y * h),       # Nose tip
            (landmarks[152].x * w, landmarks[152].y * h),   # Chin
            (landmarks[33].x * w, landmarks[33].y * h),     # Left eye outer corner
            (landmarks[263].x * w, landmarks[263].y * h),   # Right eye outer corner
            (landmarks[61].x * w, landmarks[61].y * h),     # Left mouth corner
            (landmarks[291].x * w, landmarks[291].y * h)    # Right mouth corner
        ], dtype=np.float64)

        focal_length = w
        center = (w / 2.0, h / 2.0)
        camera_matrix = np.array([
            [focal_length, 0, center[0]],
            [0, focal_length, center[1]],
            [0, 0, 1]
        ], dtype=np.float64)
        dist_coeffs = np.zeros((4, 1), dtype=np.float64)

        success, rvec, tvec = cv2.solvePnP(
            MODEL_POINTS_3D, image_points, camera_matrix, dist_coeffs, flags=cv2.SOLVEPNP_ITERATIVE
        )

        R, _ = cv2.Rodrigues(rvec)
        angles, _, _, _, _, _ = cv2.RQDecomp3x3(R)
        pitch = angles[0]
        yaw = angles[1]
        roll = angles[2]

        return yaw, pitch, roll, rvec, tvec, camera_matrix, dist_coeffs, image_points

    def _estimate_gaze(self, landmarks):
        """Check if iris gaze is centered vs deflected."""
        if len(landmarks) < 478:
            return True  # Refined iris landmarks not available, assume gaze ok

        try:
            # Left Eye: outer 33, inner 133, iris 468
            left_w = abs(landmarks[133].x - landmarks[33].x)
            if left_w > 1e-4:
                left_ratio = abs(landmarks[468].x - landmarks[33].x) / left_w
                self.gaze_ratio_left = left_ratio

            # Right Eye: inner 362, outer 263, iris 473
            right_w = abs(landmarks[263].x - landmarks[362].x)
            if right_w > 1e-4:
                right_ratio = abs(landmarks[473].x - landmarks[362].x) / right_w
                self.gaze_ratio_right = right_ratio

            # Allow reasonable glance bounds
            if (self.gaze_ratio_left < 0.18 or self.gaze_ratio_left > 0.82 or
                self.gaze_ratio_right < 0.18 or self.gaze_ratio_right > 0.82):
                return False
        except Exception:
            pass

        return True

    def _render_calibration_frame(self, frame, landmarks, w, h, rvec, tvec, cam_matrix, dist_coeffs, image_points):
        annotated = frame.copy()

        # Draw 3D Nose Direction Pointer
        nose_3d = np.array([(0.0, 0.0, 500.0)], dtype=np.float64)
        nose_end_2d, _ = cv2.projectPoints(nose_3d, rvec, tvec, cam_matrix, dist_coeffs)

        p1 = (int(image_points[0][0]), int(image_points[0][1]))
        p2 = (int(nose_end_2d[0][0][0]), int(nose_end_2d[0][0][1]))

        # Line color: Neon green if attentive, red if distracted
        color = (65, 255, 0) if self.raw_attentive else (109, 42, 255)
        cv2.line(annotated, p1, p2, color, 3, cv2.LINE_AA)
        cv2.circle(annotated, p1, 5, (255, 255, 255), -1)

        # Draw key landmark points
        for pt in image_points:
            cv2.circle(annotated, (int(pt[0]), int(pt[1])), 4, (0, 204, 255), -1)

        # Draw eye contours / irises if present
        if len(landmarks) >= 478:
            l_iris = (int(landmarks[468].x * w), int(landmarks[468].y * h))
            r_iris = (int(landmarks[473].x * w), int(landmarks[473].y * h))
            cv2.circle(annotated, l_iris, 3, (0, 255, 65), -1)
            cv2.circle(annotated, r_iris, 3, (0, 255, 65), -1)

        # Semi-transparent HUD overlay at the bottom
        overlay = annotated.copy()
        cv2.rectangle(overlay, (0, h - 85), (w, h), (20, 20, 24), -1)
        cv2.addWeighted(overlay, 0.75, annotated, 0.25, 0, annotated)

        # Angle texts
        yaw_text = f"Yaw: {self.current_yaw:+.1f} deg (Max: +-{self.yaw_threshold:.0f})"
        pitch_text = f"Pitch: {self.current_pitch:+.1f} deg (Max: +-{self.pitch_threshold:.0f})"
        cv2.putText(annotated, yaw_text, (15, h - 55), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (220, 220, 220), 1, cv2.LINE_AA)
        cv2.putText(annotated, pitch_text, (15, h - 25), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (220, 220, 220), 1, cv2.LINE_AA)

        # Status badge
        status_text = "FOCUSED" if self.is_focused else "DISTRACTED"
        badge_color = (65, 255, 0) if self.is_focused else (109, 42, 255)
        cv2.putText(annotated, status_text, (w - 170, h - 35), cv2.FONT_HERSHEY_SIMPLEX, 0.75, badge_color, 2, cv2.LINE_AA)

        return annotated

    def _render_no_face_frame(self, frame):
        annotated = frame.copy()
        h, w, _ = frame.shape
        cv2.putText(annotated, "NO FACE DETECTED", (w // 2 - 130, h // 2),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.75, (109, 42, 255), 2, cv2.LINE_AA)
        return annotated

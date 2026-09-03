import os
import sys
import time
import numpy as np

# Add parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

def test_storage():
    print("[TEST] Running StorageManager test...")
    from storage import StorageManager
    test_file = "test_focus_data.json"
    if os.path.exists(test_file):
        os.remove(test_file)

    sm = StorageManager(test_file)
    assert sm.get_setting("mode") == "stopwatch"
    assert sm.get_setting("pomodoro.work_minutes") == 25
    sm.set_setting("pomodoro.work_minutes", 30)
    assert sm.get_setting("pomodoro.work_minutes") == 30

    sm.record_time(60.0, 10.0)
    sm.record_pomodoro()
    stats = sm.get_today_stats()
    assert stats["focused_seconds"] == 60.0
    assert stats["distracted_seconds"] == 10.0
    assert stats["completed_pomodoros"] == 1
    assert stats["focus_score"] > 80

    if os.path.exists(test_file):
        os.remove(test_file)
    print("  -> StorageManager PASS")

def test_audio():
    print("[TEST] Running AudioPlayer synthesis test...")
    from audio_alerts import AudioPlayer
    player = AudioPlayer()
    assert "complete" in player.cached_sounds
    assert "distraction" in player.cached_sounds
    assert "refocus" in player.cached_sounds
    assert len(player.cached_sounds["complete"]) > 1000
    assert player.cached_sounds["complete"][:4] == b"RIFF"
    print("  -> AudioPlayer PASS")

def test_cv_tracker():
    print("[TEST] Running AttentionTracker test...")
    from cv_tracker import AttentionTracker
    tracker = AttentionTracker()
    assert tracker.grace_period == 2.0
    assert tracker.yaw_threshold == 28.0
    
    # Test head pose calculation with dummy points
    w, h = 640, 480
    class DummyLandmark:
        def __init__(self, x, y, z=0.0):
            self.x = x
            self.y = y
            self.z = z

    landmarks = [DummyLandmark(0.5, 0.5) for _ in range(480)]
    landmarks[1] = DummyLandmark(0.5, 0.45)    # Nose
    landmarks[152] = DummyLandmark(0.5, 0.75)  # Chin
    landmarks[33] = DummyLandmark(0.35, 0.40)  # Left eye outer
    landmarks[263] = DummyLandmark(0.65, 0.40) # Right eye outer
    landmarks[61] = DummyLandmark(0.40, 0.60)  # Left mouth
    landmarks[291] = DummyLandmark(0.60, 0.60) # Right mouth

    yaw, pitch, roll, rvec, tvec, cam_matrix, dist_coeffs, img_pts = tracker._estimate_head_pose(landmarks, w, h)
    print(f"  Estimated Euler Angles: Yaw={yaw:.1f}, Pitch={pitch:.1f}, Roll={roll:.1f}")
    assert isinstance(yaw, float)
    assert isinstance(pitch, float)

    blank = np.zeros((h, w, 3), dtype=np.uint8)
    frame = tracker._render_calibration_frame(blank, landmarks, w, h, rvec, tvec, cam_matrix, dist_coeffs, img_pts)
    assert frame.shape == (h, w, 3)
    print("  -> AttentionTracker PASS")

if __name__ == "__main__":
    test_storage()
    test_audio()
    test_cv_tracker()
    print("\nALL AUTOMATED TESTS PASSED SUCCESSFULLY!")

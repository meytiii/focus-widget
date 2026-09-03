import os
import json
import datetime

CONFIG_FILE = "focus_data.json"

DEFAULT_DATA = {
    "settings": {
        "mode": "stopwatch",  # "stopwatch" | "pomodoro" | "countdown"
        "pomodoro": {
            "work_minutes": 25,
            "break_minutes": 5,
            "long_break_minutes": 15,
            "cycles_before_long": 4
        },
        "countdown_minutes": 30,
        "sensitivity": {
            "yaw_threshold": 28.0,     # Max head turn angle (degrees)
            "pitch_threshold": 20.0,   # Max head tilt up/down (degrees)
            "grace_period": 2.0        # Seconds of buffer before triggering distraction
        },
        "audio": {
            "sound_enabled": True,
            "distraction_alert": True,
            "completion_alert": True
        },
        "ui": {
            "always_on_top": False,
            "mini_x": None,
            "mini_y": None
        },
        "camera_index": 0
    },
    "stats": {}
}

class StorageManager:
    def __init__(self, filepath=CONFIG_FILE):
        self.filepath = filepath
        self.data = self._load()

    def _load(self):
        if not os.path.exists(self.filepath):
            return json.loads(json.dumps(DEFAULT_DATA))
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                # Deep merge defaults in case new keys were introduced
                return self._merge_defaults(loaded, DEFAULT_DATA)
        except Exception as e:
            print(f"Warning: Failed to load {self.filepath}: {e}")
            return json.loads(json.dumps(DEFAULT_DATA))

    def _merge_defaults(self, target, reference):
        if not isinstance(target, dict):
            return reference
        result = {}
        for key, ref_val in reference.items():
            if key in target:
                if isinstance(ref_val, dict) and isinstance(target[key], dict):
                    result[key] = self._merge_defaults(target[key], ref_val)
                else:
                    result[key] = target[key]
            else:
                result[key] = ref_val
        for key, val in target.items():
            if key not in result:
                result[key] = val
        return result

    def save(self):
        try:
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving {self.filepath}: {e}")

    def get_setting(self, path, default=None):
        keys = path.split(".")
        current = self.data.get("settings", {})
        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return default
        return current

    def set_setting(self, path, value):
        keys = path.split(".")
        current = self.data.setdefault("settings", {})
        for k in keys[:-1]:
            current = current.setdefault(k, {})
        current[keys[-1]] = value
        self.save()

    def _get_today_key(self):
        return datetime.date.today().isoformat()

    def get_today_stats(self):
        today_key = self._get_today_key()
        today_dict = self.data.get("stats", {}).get(today_key, {
            "focused_seconds": 0.0,
            "distracted_seconds": 0.0,
            "completed_pomodoros": 0
        })
        focused = today_dict.get("focused_seconds", 0.0)
        distracted = today_dict.get("distracted_seconds", 0.0)
        total = focused + distracted
        score = int(round((focused / total * 100))) if total > 0 else 100

        return {
            "date": today_key,
            "focused_seconds": focused,
            "distracted_seconds": distracted,
            "focus_score": score,
            "completed_pomodoros": today_dict.get("completed_pomodoros", 0)
        }

    def record_time(self, focused_delta=0.0, distracted_delta=0.0):
        if focused_delta <= 0 and distracted_delta <= 0:
            return
        today_key = self._get_today_key()
        stats = self.data.setdefault("stats", {})
        today_dict = stats.setdefault(today_key, {
            "focused_seconds": 0.0,
            "distracted_seconds": 0.0,
            "completed_pomodoros": 0
        })
        today_dict["focused_seconds"] += focused_delta
        today_dict["distracted_seconds"] += distracted_delta
        self.save()

    def record_pomodoro(self):
        today_key = self._get_today_key()
        stats = self.data.setdefault("stats", {})
        today_dict = stats.setdefault(today_key, {
            "focused_seconds": 0.0,
            "distracted_seconds": 0.0,
            "completed_pomodoros": 0
        })
        today_dict["completed_pomodoros"] = today_dict.get("completed_pomodoros", 0) + 1
        self.save()

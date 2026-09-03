import math
import struct
import io
import wave
import threading
import sys

try:
    import winsound
    HAS_WINSOUND = True
except ImportError:
    HAS_WINSOUND = False

class AudioPlayer:
    def __init__(self, storage=None):
        self.storage = storage
        self.cached_sounds = {}
        self._pregenerate_sounds()

    def _generate_wav(self, notes, sample_rate=44100):
        """
        Generate in-memory WAV bytes for a sequence of notes.
        notes: list of (frequency_hz, duration_ms, volume 0.0-1.0)
        """
        raw_samples = []
        for freq, duration_ms, vol in notes:
            num_samples = int(sample_rate * (duration_ms / 1000.0))
            if num_samples == 0:
                continue

            # Attack and Release lengths in samples (to prevent audio clicks)
            attack_samples = min(int(sample_rate * 0.015), num_samples // 4)
            decay_samples = min(int(sample_rate * 0.05), num_samples // 3)
            release_samples = min(int(sample_rate * 0.04), num_samples // 4)

            for i in range(num_samples):
                t = i / sample_rate
                # Envelope
                if i < attack_samples:
                    env = i / attack_samples
                elif i < attack_samples + decay_samples:
                    decay_ratio = (i - attack_samples) / decay_samples
                    env = 1.0 - 0.25 * decay_ratio
                elif i > num_samples - release_samples:
                    env = 0.75 * ((num_samples - i) / release_samples)
                else:
                    env = 0.75

                # Sine wave with subtle 2nd harmonic for richer warm acoustic timbre
                val = math.sin(2 * math.pi * freq * t) * 0.8 + math.sin(4 * math.pi * freq * t) * 0.2
                sample = int(32767 * vol * env * val)
                # Clamp
                sample = max(-32767, min(32767, sample))
                raw_samples.append(sample)

        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wf:
            wf.setnchannels(1)        # Mono
            wf.setsampwidth(2)        # 16-bit
            wf.setframerate(sample_rate)
            packed = struct.pack(f"<{len(raw_samples)}h", *raw_samples)
            wf.writeframes(packed)

        return buffer.getvalue()

    def _pregenerate_sounds(self):
        """Synthesize pleasant chimes once at startup."""
        try:
            # 1. Completion / Success chime: C5 -> E5 -> G5 -> C6
            self.cached_sounds["complete"] = self._generate_wav([
                (523.25, 120, 0.4),
                (659.25, 120, 0.45),
                (783.99, 140, 0.5),
                (1046.50, 380, 0.55),
            ])

            # 2. Distraction gentle nudge: E4 -> C4
            self.cached_sounds["distraction"] = self._generate_wav([
                (329.63, 140, 0.35),
                (261.63, 240, 0.30),
            ])

            # 3. Refocus confirmation: G5
            self.cached_sounds["refocus"] = self._generate_wav([
                (783.99, 160, 0.35)
            ])

            # 4. Break finish: A4 -> D5
            self.cached_sounds["break_done"] = self._generate_wav([
                (440.00, 160, 0.45),
                (587.33, 350, 0.50)
            ])
        except Exception as e:
            print(f"Failed to pregenerate sounds: {e}")

    def _play_bytes_async(self, wav_bytes):
        if not HAS_WINSOUND or not wav_bytes:
            return
        def _runner():
            try:
                winsound.PlaySound(wav_bytes, winsound.SND_MEMORY | winsound.SND_ASYNC)
            except Exception as e:
                print(f"Audio playback error: {e}")
        threading.Thread(target=_runner, daemon=True).start()

    def play_complete(self):
        if self.storage and not self.storage.get_setting("audio.sound_enabled", True):
            return
        if self.storage and not self.storage.get_setting("audio.completion_alert", True):
            return
        self._play_bytes_async(self.cached_sounds.get("complete"))

    def play_distraction(self):
        if self.storage and not self.storage.get_setting("audio.sound_enabled", True):
            return
        if self.storage and not self.storage.get_setting("audio.distraction_alert", True):
            return
        self._play_bytes_async(self.cached_sounds.get("distraction"))

    def play_refocus(self):
        if self.storage and not self.storage.get_setting("audio.sound_enabled", True):
            return
        self._play_bytes_async(self.cached_sounds.get("refocus"))

    def play_break_done(self):
        if self.storage and not self.storage.get_setting("audio.sound_enabled", True):
            return
        self._play_bytes_async(self.cached_sounds.get("break_done"))

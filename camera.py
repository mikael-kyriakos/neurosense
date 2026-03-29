
import cv2
import numpy as np
import threading
import time
import copy
from dataclasses import dataclass, field
from typing import Optional
 
 
# ─── Public data contract ─────────────────────────────────────────────────────
 
@dataclass
class EnvironmentState:
    scene:            str   = "unknown"
    scene_confidence: float = 0.0
    person_count:     int   = 0
    situation:        str   = "UNKNOWN"   # LECTURE | MEETING | STUDY GROUP | SOLO WORK | UNKNOWN
    cognitive_load:   str   = "unknown"   # low | medium | high
    session_seconds:  float = 0.0
    session_scene:    str   = "unknown"
    updated_at:       float = field(default_factory=time.time)
 
    def as_dict(self) -> dict:
        return {
            "scene":            self.scene,
            "scene_confidence": round(self.scene_confidence, 3),
            "person_count":     self.person_count,
            "situation":        self.situation,
            "cognitive_load":   self.cognitive_load,
            "session_seconds":  round(self.session_seconds, 1),
            "session_scene":    self.session_scene,
            "updated_at":       self.updated_at,
        }
 
 
# ─── Config ───────────────────────────────────────────────────────────────────
 
_YOLO_MODEL   = "yolov8n.pt"
_YOLO_CONF    = 0.45
_YOLO_IOU     = 0.45
_PERSON_CLASS = 0
 
_CLIP_INTERVAL = 1.5   # seconds between CLIP inferences
_CLIP_SIZE     = 448   # resolution fed to CLIP
 
_SCENE_LABELS = [
    "a study room with a desk and student",
    "a classroom with desks and students",
    "a meeting room with a table and chairs",
    "a lecture hall with rows of seats",
]

_SCENE_NAMES = [
    "study room", "classroom", "meeting room", "lecture hall"
]
 
_LOAD_BY_SITUATION = {
    "LECTURE":     "high",
    "MEETING":     "high",
    "STUDY GROUP": "medium",
    "SOLO WORK":   "medium",
    "UNKNOWN":     "unknown",
}
 
_LOAD_BY_SCENE = {
    "study group" :      "medium", 
    "solo work"   :      "medium",
    "meeting room":      "high",
    "lecture hall":      "high",
    "unknown":           "unknown",
}
 
 
# ─── Situation classifier ─────────────────────────────────────────────────────
 
def _classify_situation(person_count: int, scene: str) -> str:
    if person_count == 0 :
        return "UNKNOWN"
    if person_count == 1:
        return "SOLO WORK"
    if 2 <= person_count <= 3:
        return "STUDY GROUP"
    if 3 <= person_count <= 5:
        return "MEETING"
    return "LECTURE"  # 6+
 
 
# ─── Cognitive load estimator ─────────────────────────────────────────────────
 
def _estimate_load(scene: str, situation: str) -> str:
    sit_load   = _LOAD_BY_SITUATION.get(situation, "unknown")
    scene_load = _LOAD_BY_SCENE.get(scene, "unknown")
    if situation == "UNKNOWN":
        return scene_load
    order = {"unknown": 0, "low": 1, "medium": 2, "high": 3}
    return sit_load if order.get(sit_load, 0) >= order.get(scene_load, 0) else scene_load
 
 
# ─── CLIP scene classifier ────────────────────────────────────────────────────
 
class _CLIPClassifier:
    def __init__(self):
        self._model      = None
        self._processor  = None
        self._text_feats = None
        self._ready      = False
        self._busy       = False
        self._last_run   = 0.0
        self._result     = ("unknown", 0.0)
        self._lock       = threading.Lock()
        threading.Thread(target=self._load, daemon=True).start()
 
    def _load(self):
        try:
            from transformers import CLIPModel, CLIPProcessor
            import torch
            self._model     = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
            self._processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
            self._model.eval()
            with torch.no_grad():
                inp = self._processor(text=_SCENE_LABELS, return_tensors="pt", padding=True)
                tf  = self._model.get_text_features(**inp)
                self._text_feats = tf / tf.norm(dim=-1, keepdim=True)
            self._ready = True
            print("[NeuroSense CV] CLIP ready.")
        except Exception as e:
            print(f"[NeuroSense CV] CLIP load failed: {e}")
 
    def _infer(self, frame_bgr: np.ndarray):
        try:
            import torch
            from PIL import Image
            img = Image.fromarray(cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB))
            with torch.no_grad():
                inp   = self._processor(images=img, return_tensors="pt")
                imf   = self._model.get_image_features(**inp)
                imf   = imf / imf.norm(dim=-1, keepdim=True)
                probs = ((imf @ self._text_feats.T) * 100.0).softmax(dim=-1).squeeze().tolist()
            scored = {_SCENE_NAMES[i]: probs[i] for i in range(len(probs))}
            best   = max(scored, key=scored.get)
            with self._lock:
                self._result = (best, scored[best])
        except Exception:
            pass
        finally:
            self._busy = False
 
    def maybe_run(self, frame: np.ndarray):
        if not self._ready or self._busy:
            return
        if time.time() - self._last_run < _CLIP_INTERVAL:
            return
        self._busy     = True
        self._last_run = time.time()
        small = cv2.resize(frame, (_CLIP_SIZE, _CLIP_SIZE))
        threading.Thread(target=self._infer, args=(small,), daemon=True).start()
 
    def get(self):
        with self._lock:
            return self._result
 
    @property
    def ready(self):
        return self._ready
 
 
# ─── Session tracker ──────────────────────────────────────────────────────────
 
class _SessionTracker:
    def __init__(self):
        self._current_scene = "unknown"
        self._scene_start   = time.time()
 
    def update(self, scene: str) -> tuple:
        if scene != self._current_scene and scene != "unknown":
            self._current_scene = scene
            self._scene_start   = time.time()
        return time.time() - self._scene_start, self._current_scene
 
 
# ─── Public CV module ─────────────────────────────────────────────────────────
 
class CVModule:
    def __init__(self,
                 camera_index: int  = 0,
                 show_window:  bool = False,
                 frame_width:  int  = 1280,
                 frame_height: int  = 720):
 
        self._camera_index = camera_index
        self._show_window  = show_window
        self._frame_width  = frame_width
        self._frame_height = frame_height
 
        self._state      = EnvironmentState()
        self._state_lock = threading.Lock()
        self._running    = False
        self._thread: Optional[threading.Thread] = None
 
        self._clip    = _CLIPClassifier()
        self._session = _SessionTracker()
 
    def start(self):
        if self._running:
            return
        self._running = True
        self._thread  = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        print("[NeuroSense CV] Started.")
 
    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=3)
        print("[NeuroSense CV] Stopped.")
 
    def get_state(self) -> EnvironmentState:
        with self._state_lock:
            return copy.copy(self._state)
 
    def _loop(self):
        try:
            from ultralytics import YOLO
        except ImportError:
            raise ImportError("[NeuroSense CV] Run: pip install ultralytics")
 
        yolo = YOLO(_YOLO_MODEL)
 
        cap = cv2.VideoCapture(self._camera_index)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH,  self._frame_width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self._frame_height)
 
        if not cap.isOpened():
            print(f"[NeuroSense CV] Cannot open camera {self._camera_index}")
            self._running = False
            return
 
        while self._running:                          # ← fixed: no longer inside the if block
            ret, frame = cap.read()
            if not ret:
                time.sleep(0.05)
                continue
 
            frame = cv2.flip(frame, 1)
            fh, fw = frame.shape[:2]
 
            # ── YOLO person detection ─────────────────────────────────────
            results      = yolo(frame, conf=_YOLO_CONF, iou=_YOLO_IOU,
                                classes=[_PERSON_CLASS], verbose=False)[0]
            person_count = len(results.boxes)
            boxes        = results.boxes
 
            # ── CLIP scene classification ─────────────────────────────────
            self._clip.maybe_run(frame)
            scene, scene_conf = self._clip.get()
 
            # ── Session tracking ──────────────────────────────────────────
            session_secs, session_scene = self._session.update(scene)
 
            # ── Classify situation + cognitive load ───────────────────────
            situation = _classify_situation(person_count, scene)
            load      = _estimate_load(scene, situation)
 
            # ── Update shared state ───────────────────────────────────────
            with self._state_lock:
                self._state.scene            = scene
                self._state.scene_confidence = scene_conf
                self._state.person_count     = person_count
                self._state.situation        = situation
                self._state.cognitive_load   = load
                self._state.session_seconds  = session_secs
                self._state.session_scene    = session_scene
                self._state.updated_at       = time.time()
 
            # ── Optional debug window ─────────────────────────────────────
            if self._show_window:
                cv2.imshow("NeuroSense CV", frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    self._running = False
                    break
 
        cap.release()
        if self._show_window:
            cv2.destroyAllWindows()
 
 

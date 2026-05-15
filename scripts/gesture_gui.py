"""
GUI for real-time arm gesture recognition from AD5940 BIA console output.

The firmware is expected to print lines like:
    [ID:12] 50000.00 Hz 1234.56 Ohm 12.34 deg

Run:
    python scripts/gesture_gui.py
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import queue
import random
import re
import statistics
import threading
import time
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk

try:
    import serial
    import serial.tools.list_ports
except ImportError:  # The UI still works in simulation mode.
    serial = None


APP_DIR = Path(__file__).resolve().parent
DATA_DIR = APP_DIR / "gesture_data"
PROFILE_PATH = DATA_DIR / "calibration_profile.json"
SEQUENCES_PATH = DATA_DIR / "gesture_sequences.json"
CSV_DIR = DATA_DIR / "captures"

UI_BG = "#e8edf2"
UI_CARD = "#ffffff"
UI_CARD_SOFT = "#f6f8fa"
UI_BORDER = "#c9d3dc"
UI_TEXT = "#18212b"
UI_MUTED = "#5f6b78"
UI_ACCENT = "#ff9800"
UI_ACCENT_DARK = "#d97706"
UI_BLUE = "#263746"
UI_DARK = "#111820"

LINE_RE = re.compile(
    r"\[ID:(?P<id>\d+)\]\s+"
    r"(?P<freq>[-+]?\d+(?:\.\d+)?)\s+Hz\s+"
    r"(?P<mag>[-+]?\d+(?:\.\d+)?)\s+Ohm\s+"
    r"(?P<phase>[-+]?\d+(?:\.\d+)?)\s+deg"
)

GESTURES = ["Reposo", "Puno cerrado", "Giro muneca", "Flexion brazo", "Extension brazo"]
CALIBRATION_STEPS = [
    ("Reposo", "Deja el brazo quieto, sin hacer fuerza."),
    ("Puno cerrado", "Cierra el puño y repite la acción de forma natural."),
    ("Giro muneca", "Gira la muñeca y vuelve al centro varias veces."),
    ("Flexion brazo", "Flexiona el brazo y vuelve a la posición inicial."),
    ("Extension brazo", "Extiende el brazo y vuelve a la posición inicial."),
]
CALIBRATION_PREP_SECONDS = 3
CALIBRATION_CAPTURE_SECONDS = 6
UNKNOWN_LABEL = "Movimiento desconocido"
CLASSIFICATION_WINDOW_SAMPLES = 16
CLASSIFICATION_MIN_SAMPLES = 8
CLASSIFICATION_SMOOTHING_SAMPLES = 7
MIN_CLASSIFICATION_MARGIN = 0.12
REST_LABEL = "Reposo"
PEAK_GESTURE_LABELS = {"Giro muneca", "Flexion brazo", "Extension brazo"}
ACTIVE_ADVANTAGE_THRESHOLD = 0.45
ACTIVE_MAX_DISTANCE = 3.2
PEAK_MATCH_MIN = 0.28
MAX_SIMULTANEOUS_GESTURES = 2
CLASSIFICATION_INTERVAL = 3
DRAW_INTERVAL = 3
UI_LOG_MAX_LINES = 450
CALIBRATION_UI_LOG_EVERY = 5
SECURITY_PASSWORD_HASH = hashlib.sha256("admin4321@".encode("utf-8")).hexdigest()

DISPLAY_NAMES = {
    "Reposo": "Reposo",
    "Puno cerrado": "Puño cerrado",
    "Giro muneca": "Giro de muñeca",
    "Flexion brazo": "Flexión de brazo",
    "Extension brazo": "Extensión de brazo",
    UNKNOWN_LABEL: "Movimiento desconocido",
}


def display_label(label: str) -> str:
    if " + " in label:
        return " + ".join(DISPLAY_NAMES.get(part, part) for part in label.split(" + "))
    return DISPLAY_NAMES.get(label, label)


DISPLAY_GESTURES = [display_label(gesture) for gesture in GESTURES]
INTERNAL_GESTURES_BY_DISPLAY = {display_label(gesture): gesture for gesture in GESTURES}


@dataclass
class Sample:
    sample_id: int
    timestamp: float
    frequency_hz: float
    magnitude_ohm: float
    phase_deg: float


def parse_sample(line: str) -> Sample | None:
    match = LINE_RE.search(line.strip())
    if not match:
        return None
    return Sample(
        sample_id=int(match.group("id")),
        timestamp=time.time(),
        frequency_hz=float(match.group("freq")),
        magnitude_ohm=float(match.group("mag")),
        phase_deg=float(match.group("phase")),
    )


def mean(values: list[float]) -> float:
    return statistics.fmean(values) if values else 0.0


def stdev(values: list[float]) -> float:
    if len(values) < 2:
        return 1.0
    return max(statistics.stdev(values), 1e-6)


def frequency_key(frequency_hz: float) -> str:
    return f"{round(frequency_hz):.0f}"


def nearest_frequency_key(frequency_hz: float, bins: dict[str, dict]) -> str | None:
    if not bins:
        return None
    key = frequency_key(frequency_hz)
    if key in bins:
        return key
    return min(bins.keys(), key=lambda item: abs(float(item) - frequency_hz))


def build_gesture_profile(samples: list[Sample], rest_profile: dict | None = None) -> dict:
    grouped: dict[str, list[Sample]] = {}
    for sample in samples:
        grouped.setdefault(frequency_key(sample.frequency_hz), []).append(sample)

    bins = {}
    delta_mags_all = []
    delta_phases_all = []
    rest_bins = rest_profile.get("bins", {}) if rest_profile else {}

    for key, group in grouped.items():
        mags = [sample.magnitude_ohm for sample in group]
        phases = [sample.phase_deg for sample in group]
        bin_profile = {
            "frequency_mean": mean([sample.frequency_hz for sample in group]),
            "magnitude_mean": mean(mags),
            "magnitude_std": max(stdev(mags), 5.0),
            "phase_mean": mean(phases),
            "phase_std": max(stdev(phases), 1.0),
            "sample_count": len(group),
        }

        rest_key = nearest_frequency_key(float(key), rest_bins) if rest_bins else None
        if rest_key is not None:
            rest_bin = rest_bins[rest_key]
            delta_mags = [sample.magnitude_ohm - rest_bin["magnitude_mean"] for sample in group]
            delta_phases = [sample.phase_deg - rest_bin["phase_mean"] for sample in group]
            delta_mags_all.extend(delta_mags)
            delta_phases_all.extend(delta_phases)
            bin_profile.update({
                "delta_magnitude_mean": mean(delta_mags),
                "delta_magnitude_std": max(stdev(delta_mags), 2.0),
                "delta_phase_mean": mean(delta_phases),
                "delta_phase_std": max(stdev(delta_phases), 0.5),
            })
        bins[key] = bin_profile

    mags = [sample.magnitude_ohm for sample in samples]
    phases = [sample.phase_deg for sample in samples]
    freqs = [sample.frequency_hz for sample in samples]
    profile = {
        "profile_version": 3,
        "frequency_mean": mean(freqs),
        "magnitude_mean": mean(mags),
        "magnitude_std": max(stdev(mags), 5.0),
        "phase_mean": mean(phases),
        "phase_std": max(stdev(phases), 1.0),
        "sample_count": len(samples),
        "peak_magnitude_range": (max(mags) - min(mags)) if mags else 0.0,
        "peak_phase_range": (max(phases) - min(phases)) if phases else 0.0,
        "bins": bins,
        "updated_at": time.time(),
    }
    if delta_mags_all or delta_phases_all:
        profile.update({
            "uses_rest_delta": True,
            "delta_magnitude_mean": mean(delta_mags_all),
            "delta_magnitude_std": max(stdev(delta_mags_all), 2.0),
            "delta_phase_mean": mean(delta_phases_all),
            "delta_phase_std": max(stdev(delta_phases_all), 0.5),
            "delta_peak_magnitude_range": (max(delta_mags_all) - min(delta_mags_all)) if delta_mags_all else 0.0,
            "delta_peak_phase_range": (max(delta_phases_all) - min(delta_phases_all)) if delta_phases_all else 0.0,
        })
    else:
        profile["uses_rest_delta"] = False
    return profile


def ensure_data_dirs() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    CSV_DIR.mkdir(exist_ok=True)


class SerialReader(threading.Thread):
    def __init__(self, port: str, baud: int, out_queue: queue.Queue[Sample | str]):
        super().__init__(daemon=True)
        self.port = port
        self.baud = baud
        self.out_queue = out_queue
        self._stop_event = threading.Event()
        self._serial = None

    def run(self) -> None:
        if serial is None:
            self.out_queue.put("ERROR: pyserial no esta instalado.")
            return
        try:
            self._serial = serial.Serial(self.port, self.baud, timeout=1)
            self.out_queue.put(f"Conectado a {self.port} @ {self.baud}.")
            while not self._stop_event.is_set():
                raw = self._serial.readline()
                if not raw:
                    continue
                line = raw.decode(errors="replace")
                sample = parse_sample(line)
                if sample:
                    self.out_queue.put(sample)
        except Exception as exc:
            self.out_queue.put(f"ERROR: {exc}")
        finally:
            if self._serial:
                self._serial.close()

    def stop(self) -> None:
        self._stop_event.set()


class Simulator(threading.Thread):
    def __init__(self, out_queue: queue.Queue[Sample | str]):
        super().__init__(daemon=True)
        self.out_queue = out_queue
        self._stop_event = threading.Event()
        self._sample_id = 0
        self._modes = [
            ("Reposo", 1000, 0),
            ("Puno cerrado", 1170, -10),
            ("Giro muneca", 890, 14),
        ]

    def run(self) -> None:
        self.out_queue.put("Modo simulacion iniciado.")
        while not self._stop_event.is_set():
            mode_idx = int(time.time() / 6) % len(self._modes)
            _, mag_base, phase_base = self._modes[mode_idx]
            self.out_queue.put(
                Sample(
                    sample_id=self._sample_id,
                    timestamp=time.time(),
                    frequency_hz=50000.0,
                    magnitude_ohm=mag_base + random.gauss(0, 12),
                    phase_deg=phase_base + random.gauss(0, 2),
                )
            )
            self._sample_id += 1
            time.sleep(0.08)

    def stop(self) -> None:
        self._stop_event.set()


class GestureClassifier:
    def __init__(self) -> None:
        self.profile: dict[str, dict] = {}
        self.window: list[Sample] = []
        self.label_history: list[str] = []

    def set_profile(self, profile: dict[str, dict]) -> None:
        self.profile = profile
        self.window = []
        self.label_history = []

    def is_ready(self) -> bool:
        return bool(self.profile)

    def classify(self, sample: Sample, allow_combined: bool = True) -> tuple[str, float]:
        self.window.append(sample)
        self.window = self.window[-CLASSIFICATION_WINDOW_SAMPLES:]

        if not self.profile or len(self.window) < CLASSIFICATION_MIN_SAMPLES:
            return UNKNOWN_LABEL, 0.0

        distance_by_label = {}
        rest_stats = self.profile.get(REST_LABEL)
        for label, stats in self.profile.items():
            if label != REST_LABEL and stats.get("uses_rest_delta") and rest_stats:
                distance = self._delta_distance_to_profile(stats, rest_stats, self.window)
            else:
                distance = self._distance_to_profile(stats, self.window)
            if distance is not None:
                distance_by_label[label] = distance

        if not distance_by_label:
            return UNKNOWN_LABEL, 0.0

        raw_label, confidence = self._classify_from_distances(distance_by_label, allow_combined)
        self.label_history.append(raw_label)
        self.label_history = self.label_history[-CLASSIFICATION_SMOOTHING_SAMPLES:]
        stable_label = self._stable_label()
        if stable_label == UNKNOWN_LABEL:
            return stable_label, confidence
        return stable_label, confidence

    def _classify_from_distances(self, distance_by_label: dict[str, float], allow_combined: bool) -> tuple[str, float]:
        sorted_scores = sorted(distance_by_label.items(), key=lambda item: item[1])
        best_label, best_distance = sorted_scores[0]
        second_distance = sorted_scores[1][1] if len(sorted_scores) > 1 else best_distance + 1.0
        margin = second_distance - best_distance
        basic_confidence = max(0.0, min(1.0, 1.0 - best_distance / 4.0))

        rest_distance = distance_by_label.get(REST_LABEL)
        if rest_distance is None:
            if basic_confidence < 0.35 or margin < MIN_CLASSIFICATION_MARGIN:
                return UNKNOWN_LABEL, basic_confidence
            return best_label, basic_confidence

        active = []
        for label, distance in sorted_scores:
            if label == REST_LABEL:
                continue
            stats = self.profile.get(label, {})
            peak_match = self._peak_match_score(stats)
            needs_peak = label in PEAK_GESTURE_LABELS and stats.get("peak_magnitude_range", 0.0) > 0.0
            if needs_peak and peak_match < PEAK_MATCH_MIN:
                continue

            if stats.get("uses_rest_delta"):
                if distance <= ACTIVE_MAX_DISTANCE and rest_distance >= ACTIVE_ADVANTAGE_THRESHOLD:
                    confidence = max(0.0, min(1.0, (1.0 - distance / ACTIVE_MAX_DISTANCE) + min(rest_distance, 2.0) * 0.15))
                    active.append((label, confidence, distance))
            else:
                advantage_over_rest = rest_distance - distance
                if distance <= ACTIVE_MAX_DISTANCE and advantage_over_rest >= ACTIVE_ADVANTAGE_THRESHOLD:
                    confidence = max(0.0, min(1.0, (advantage_over_rest / 2.0) + min(peak_match, 1.0) * 0.15))
                    active.append((label, confidence, distance))

        if not active:
            rest_confidence = max(0.0, min(1.0, 1.0 - rest_distance / 4.0))
            if rest_confidence >= 0.25:
                return REST_LABEL, rest_confidence
            return UNKNOWN_LABEL, rest_confidence

        active.sort(key=lambda item: (-item[1], item[2]))
        selected = active[:MAX_SIMULTANEOUS_GESTURES] if allow_combined else active[:1]
        label = " + ".join(item[0] for item in selected)
        confidence = max(item[1] for item in selected)
        return label, confidence

    def _delta_distance_to_profile(self, stats: dict, rest_stats: dict, samples: list[Sample]) -> float | None:
        if not samples or "bins" not in stats or "bins" not in rest_stats:
            return None

        bins = stats.get("bins", {})
        rest_bins = rest_stats.get("bins", {})
        distances = []
        for sample in samples:
            key = nearest_frequency_key(sample.frequency_hz, bins)
            rest_key = nearest_frequency_key(sample.frequency_hz, rest_bins)
            if key is None or rest_key is None:
                continue
            bin_stats = bins[key]
            rest_bin = rest_bins[rest_key]
            if "delta_magnitude_mean" not in bin_stats or "delta_phase_mean" not in bin_stats:
                continue
            current_delta_mag = sample.magnitude_ohm - rest_bin["magnitude_mean"]
            current_delta_phase = sample.phase_deg - rest_bin["phase_mean"]
            dm = (current_delta_mag - bin_stats["delta_magnitude_mean"]) / bin_stats["delta_magnitude_std"]
            dp = (current_delta_phase - bin_stats["delta_phase_mean"]) / bin_stats["delta_phase_std"]
            distances.append(math.sqrt(dm * dm + dp * dp))

        if not distances:
            return None
        return statistics.fmean(distances)
    def _distance_to_profile(self, stats: dict | None, samples: list[Sample]) -> float | None:
        if not stats or not samples:
            return None
        if "bins" not in stats:
            return self._legacy_distance(stats, samples)

        bins = stats.get("bins", {})
        distances = []
        for sample in samples:
            key = nearest_frequency_key(sample.frequency_hz, bins)
            if key is None:
                continue
            bin_stats = bins[key]
            dm = (sample.magnitude_ohm - bin_stats["magnitude_mean"]) / bin_stats["magnitude_std"]
            dp = (sample.phase_deg - bin_stats["phase_mean"]) / bin_stats["phase_std"]
            distances.append(math.sqrt(dm * dm + dp * dp))

        if not distances:
            return None
        return statistics.fmean(distances)

    def _peak_match_score(self, stats: dict) -> float:
        if not self.window:
            return 0.0
        profile_mag_range = stats.get("peak_magnitude_range", 0.0)
        profile_phase_range = stats.get("peak_phase_range", 0.0)
        if profile_mag_range <= 0 and profile_phase_range <= 0:
            return 1.0
        mags = [sample.magnitude_ohm for sample in self.window]
        phases = [sample.phase_deg for sample in self.window]
        current_mag_range = max(mags) - min(mags)
        current_phase_range = max(phases) - min(phases)
        mag_score = current_mag_range / profile_mag_range if profile_mag_range > 0 else 0.0
        phase_score = current_phase_range / profile_phase_range if profile_phase_range > 0 else 0.0
        return max(mag_score, phase_score)

    def _legacy_distance(self, stats: dict, samples: list[Sample]) -> float | None:
        distances = []
        for sample in samples:
            dm = (sample.magnitude_ohm - stats["magnitude_mean"]) / stats["magnitude_std"]
            dp = (sample.phase_deg - stats["phase_mean"]) / stats["phase_std"]
            distances.append(math.sqrt(dm * dm + dp * dp))
        return statistics.fmean(distances) if distances else None

    def _stable_label(self) -> str:
        labels = [label for label in self.label_history if label != UNKNOWN_LABEL]
        if not labels:
            return UNKNOWN_LABEL
        label = max(set(labels), key=labels.count)
        if labels.count(label) < max(2, len(self.label_history) // 2):
            return UNKNOWN_LABEL
        return label


class GestureApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        ensure_data_dirs()

        self.title("Reconocimiento de movimientos por bioimpedancia")
        self.geometry("1180x760")
        self.minsize(980, 660)
        self.configure(bg=UI_BG)
        self._configure_style()

        self.samples: list[Sample] = []
        self.raw_capture: list[Sample] = []
        self.sample_counter = 0
        self.last_detected_label = UNKNOWN_LABEL
        self.last_confidence = 0.0
        self.calibration_samples: list[Sample] = []
        self.queue: queue.Queue[Sample | str] = queue.Queue()
        self.reader: SerialReader | Simulator | None = None
        self.classifier = GestureClassifier()
        self.current_label = tk.StringVar(value="Sin calibrar")
        self.current_confidence = tk.StringVar(value="0%")
        self.connection_status = tk.StringVar(value="Desconectado")
        self.is_calibrating = False
        self.manual_calibration_active = False
        self.is_sequence_recording = False
        self.sequence_buffer: list[str] = []
        self.current_calibration_gesture = ""
        self.calibration_sample_counter = 0
        self.security_unlocked = False
        self.password_hash = SECURITY_PASSWORD_HASH
        self.calibration_wizard_active = False
        self.calibration_step_index = 0
        self.selected_calibration_steps = []
        self.calibration_step_vars = {}
        self.calibration_instruction = tk.StringVar(value="Marca los gestos y pulsa Calibrar seleccionados.")
        self.calibration_progress = tk.StringVar(value="Sin calibración en curso")
        self.detection_mode = tk.StringVar(value="Simple")
        self.visual_tick = 0
        self._visual_animation_job: str | None = None
        self._visual_label = ""

        self._build_ui()
        self._load_profile()
        self._load_sequences()
        self._refresh_ports()
        self._animate_visual()
        self.after(50, self._poll_queue)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _configure_style(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure("TFrame", background=UI_BG)
        style.configure("Surface.TFrame", background=UI_CARD)
        style.configure("Toolbar.TFrame", background=UI_CARD)
        style.configure("TLabel", background=UI_BG, foreground=UI_TEXT, font=("Segoe UI", 10))
        style.configure("Toolbar.TLabel", background=UI_CARD, foreground=UI_TEXT, font=("Segoe UI", 10))
        style.configure("Title.TLabel", background=UI_CARD, foreground=UI_TEXT, font=("Segoe UI", 13, "bold"))
        style.configure("Muted.TLabel", background=UI_CARD, foreground=UI_MUTED, font=("Segoe UI", 9))
        style.configure("HeroKicker.TLabel", background=UI_CARD, foreground=UI_ACCENT_DARK, font=("Segoe UI", 10, "bold"))
        style.configure("HeroValue.TLabel", background=UI_CARD, foreground=UI_TEXT, font=("Segoe UI", 28, "bold"))
        style.configure("HeroMeta.TLabel", background=UI_CARD, foreground=UI_MUTED, font=("Segoe UI", 13))

        style.configure("TLabelframe", background=UI_CARD, bordercolor=UI_BORDER, relief="solid")
        style.configure("TLabelframe.Label", background=UI_CARD, foreground=UI_TEXT, font=("Segoe UI", 10, "bold"))
        style.configure("Detection.TLabelframe", background=UI_CARD, bordercolor="#b8c2cc", relief="solid")
        style.configure("Detection.TLabelframe.Label", background=UI_CARD, foreground=UI_ACCENT_DARK, font=("Segoe UI", 10, "bold"))
        style.configure("Metric.TLabelframe", background=UI_CARD_SOFT, bordercolor=UI_BORDER, relief="solid")
        style.configure("Metric.TLabelframe.Label", background=UI_CARD_SOFT, foreground=UI_MUTED, font=("Segoe UI", 9, "bold"))

        style.configure("TButton", font=("Segoe UI", 10), padding=(12, 7), borderwidth=1)
        style.configure("Accent.TButton", font=("Segoe UI", 10, "bold"), padding=(12, 7), foreground="#ffffff", background=UI_BLUE)
        style.configure("Danger.TButton", font=("Segoe UI", 10, "bold"), padding=(12, 7), foreground="#ffffff", background="#6b2d2f")
        style.configure("Secondary.TButton", font=("Segoe UI", 10), padding=(12, 7), foreground=UI_TEXT, background="#edf1f4")
        style.map("TButton", background=[("active", "#e7eef8")], foreground=[("disabled", "#94a3b8")])
        style.map("Accent.TButton", background=[("active", "#334657"), ("disabled", "#9aa6b2")], foreground=[("disabled", "#e5e7eb")])
        style.map("Secondary.TButton", background=[("active", "#dfe5ea")])
        style.map("Danger.TButton", background=[("active", "#7f3437"), ("disabled", "#a7a7a7")], foreground=[("disabled", "#e5e7eb")])

        style.configure("TRadiobutton", background=UI_CARD, foreground=UI_TEXT, font=("Segoe UI", 10))
        style.configure("TCheckbutton", background=UI_CARD, foreground=UI_TEXT, font=("Segoe UI", 10))
        style.configure("TNotebook", background=UI_BG, borderwidth=0)
        style.configure("TNotebook.Tab", font=("Segoe UI", 10), padding=(14, 8), background="#dde4ea", foreground=UI_MUTED)
        style.map("TNotebook.Tab", background=[("selected", UI_CARD)], foreground=[("selected", UI_ACCENT_DARK)])
    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        top = ttk.Frame(self, padding=(12, 10), style="Toolbar.TFrame")
        top.grid(row=0, column=0, sticky="ew")
        top.columnconfigure(6, weight=1)

        ttk.Label(top, text="Puerto", style="Toolbar.TLabel").grid(row=0, column=0, padx=(0, 6))
        self.port_combo = ttk.Combobox(top, width=18, state="readonly")
        self.port_combo.grid(row=0, column=1, padx=(0, 8))
        ttk.Button(top, text="Actualizar", command=self._refresh_ports, style="Secondary.TButton").grid(row=0, column=2, padx=(0, 8))

        ttk.Label(top, text="Baudios", style="Toolbar.TLabel").grid(row=0, column=3, padx=(0, 6))
        self.baud_var = tk.StringVar(value="115200")
        ttk.Entry(top, width=9, textvariable=self.baud_var).grid(row=0, column=4, padx=(0, 8))

        self.connect_button = ttk.Button(top, text="Conectar", command=self._toggle_connection, style="Accent.TButton")
        self.connect_button.grid(row=0, column=5, padx=(0, 8))
        ttk.Button(top, text="Simular", command=self._start_simulator, style="Secondary.TButton").grid(row=0, column=6, sticky="w")
        ttk.Label(top, textvariable=self.connection_status).grid(row=0, column=7, sticky="e")

        panes = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        panes.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))

        left = ttk.Frame(panes, padding=10)
        right = ttk.Frame(panes, padding=10)
        panes.add(left, weight=2)
        panes.add(right, weight=1)

        left.columnconfigure(0, weight=1)
        left.rowconfigure(3, weight=1)

        detection = ttk.LabelFrame(left, text="Detección en vivo", padding=16, style="Detection.TLabelframe")
        detection.grid(row=0, column=0, sticky="ew")
        detection.columnconfigure(0, weight=1)
        detection.columnconfigure(1, weight=0)

        detection_text = ttk.Frame(detection, style="Surface.TFrame")
        detection_text.grid(row=0, column=0, sticky="nsew", padx=(0, 14))
        ttk.Label(detection_text, text="Movimiento actual", style="HeroKicker.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(detection_text, textvariable=self.current_label, style="HeroValue.TLabel").grid(
            row=1, column=0, sticky="w", pady=(4, 0)
        )
        ttk.Label(detection_text, textvariable=self.current_confidence, style="HeroMeta.TLabel").grid(
            row=2, column=0, sticky="w", pady=(6, 0)
        )

        self.arm_canvas = tk.Canvas(detection, width=340, height=220, bg=UI_CARD, highlightthickness=0, bd=0)
        self.arm_canvas.grid(row=0, column=1, sticky="e")
        self.arm_canvas.bind("<Configure>", lambda _event: self._draw_arm_visual(self.last_detected_label))

        values = ttk.Frame(left)
        values.grid(row=1, column=0, sticky="ew", pady=10)
        values.columnconfigure((0, 1, 2), weight=1)
        self.freq_var = tk.StringVar(value="- Hz")
        self.mag_var = tk.StringVar(value="- Ohm")
        self.phase_var = tk.StringVar(value="- deg")
        self._metric(values, "Frecuencia", self.freq_var, 0)
        self._metric(values, "Magnitud", self.mag_var, 1)
        self._metric(values, "Fase", self.phase_var, 2)

        self.canvas = tk.Canvas(left, height=205, bg=UI_DARK, highlightthickness=0, bd=0)
        self.canvas.grid(row=2, column=0, sticky="ew")

        log_frame = ttk.LabelFrame(left, text="Consola", padding=8)
        log_frame.grid(row=3, column=0, sticky="nsew", pady=(10, 0))
        log_frame.rowconfigure(0, weight=1)
        log_frame.columnconfigure(0, weight=1)
        self.log_text = tk.Text(log_frame, height=8, wrap="word")
        self.log_text.grid(row=0, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.log_text.configure(yscrollcommand=scroll.set, bg="#0f1720", fg="#d8e2ee", insertbackground="#ffffff", relief="flat", padx=10, pady=8, font=("Consolas", 9))

        self._build_right_panel(right)
        self._show_detection(UNKNOWN_LABEL, 0.0)

    def _show_detection(self, label: str, confidence: float) -> None:
        self.current_label.set(display_label(label))
        self.current_confidence.set(f"Confianza {confidence * 100:.0f}%")
        if label != self._visual_label:
            self._visual_label = label
            self._draw_arm_visual(label)

    def _animate_visual(self) -> None:
        self.visual_tick = (self.visual_tick + 1) % 100000
        if hasattr(self, "arm_canvas"):
            self._draw_arm_visual(self.last_detected_label)
        self._visual_animation_job = self.after(160, self._animate_visual)

    def _draw_arm_visual(self, label: str) -> None:
        if not hasattr(self, "arm_canvas"):
            return
        canvas = self.arm_canvas
        canvas.delete("all")
        width = max(canvas.winfo_width(), 300)
        height = max(canvas.winfo_height(), 190)
        tick = getattr(self, "visual_tick", 0)
        pulse = 0.5 + 0.5 * math.sin(tick * 0.45)

        canvas.create_rectangle(0, 0, width, height, fill=UI_CARD, outline="")
        for idx, color in enumerate(("#f8fbff", "#f3f7fc", "#eef4fb")):
            inset = 14 + idx * 18
            canvas.create_oval(inset, 16 + idx * 7, width - inset, height - 18 + idx * 4, outline=color, width=1)
        canvas.create_text(18, 17, text=display_label(label), anchor="w", fill=UI_TEXT, font=("Segoe UI", 10, "bold"))
        canvas.create_text(width - 18, 17, text="LIVE", anchor="e", fill=UI_ACCENT_DARK, font=("Segoe UI", 8, "bold"))

        is_fist = "Puno cerrado" in label
        is_turn = "Giro muneca" in label
        is_flex = "Flexion brazo" in label
        is_extend = "Extension brazo" in label
        is_rest = label in (REST_LABEL, UNKNOWN_LABEL, "Sin calibrar")

        scale = min(width / 420, height / 250)
        cx = width * 0.50
        cy = height * 0.47
        if is_extend:
            points = [(-132, 72), (-78, 50), (-2, 24), (78, 20), (142, 32)]
        elif is_flex:
            points = [(-132, 74), (-90, 34), (-78, -50), (-18, -92), (52, -74)]
        elif is_turn:
            wobble = math.sin(tick * 0.55) * 5
            points = [(-128, 72), (-86, 38), (-22, -40), (52, -50 + wobble), (112, -28 - wobble)]
        elif is_rest:
            points = [(-132, 72), (-92, 22), (-32, -58), (42, -58), (98, -34)]
        else:
            points = [(-128, 72), (-86, 36), (-26, -44), (48, -46), (106, -24)]

        def pt(index: int) -> tuple[float, float]:
            x, y = points[index]
            return cx + x * scale, cy + y * scale

        base = pt(0)
        shoulder = pt(1)
        elbow = pt(2)
        wrist = pt(3)
        palm = pt(4)

        orange = UI_ACCENT
        orange_dark = UI_ACCENT_DARK
        joint = "#ffb11f"
        graphite = "#3f444a"
        steel = "#717a82"
        cable = "#e11d48" if pulse > 0.45 else "#be123c"

        # Base and pedestal, inspired by industrial robot arms.
        base_y = base[1] + 24 * scale
        canvas.create_rectangle(base[0] - 82 * scale, base_y, base[0] + 44 * scale, base_y + 16 * scale, fill="#2f3438", outline="")
        canvas.create_rectangle(base[0] - 50 * scale, base_y - 18 * scale, base[0] + 8 * scale, base_y, fill="#4b5258", outline="")
        canvas.create_rectangle(base[0] - 34 * scale, base_y - 42 * scale, base[0] + 8 * scale, base_y - 18 * scale, fill="#f58b16", outline=orange_dark, width=1)
        for offset in (-18, -8, 2):
            y = base_y + offset * scale
            canvas.create_line(base[0] - 26 * scale, y, base[0] - 2 * scale, y, fill="#ffb44d", width=max(1, int(2 * scale)))

        # Soft shadow.
        canvas.create_line(base, shoulder, fill="#c4cbd3", width=max(18, int(30 * scale)), capstyle=tk.ROUND)
        canvas.create_line(shoulder, elbow, fill="#c4cbd3", width=max(16, int(24 * scale)), capstyle=tk.ROUND)
        canvas.create_line(elbow, wrist, fill="#c4cbd3", width=max(14, int(20 * scale)), capstyle=tk.ROUND)

        # Red cable from the reference image.
        cable_points = [base[0] - 22 * scale, base[1] - 12 * scale, shoulder[0] - 24 * scale, shoulder[1] - 22 * scale, elbow[0] - 8 * scale, elbow[1] - 50 * scale, wrist[0] - 4 * scale, wrist[1] - 18 * scale]
        canvas.create_line(cable_points, fill=cable, width=max(2, int((2.5 + pulse) * scale)), smooth=True, capstyle=tk.ROUND)

        # Arm links.
        canvas.create_line(base, shoulder, fill=orange, width=max(16, int(26 * scale)), capstyle=tk.ROUND)
        canvas.create_line(shoulder, elbow, fill="#ff8a12", width=max(14, int(22 * scale)), capstyle=tk.ROUND)
        canvas.create_line(elbow, wrist, fill=steel, width=max(12, int(18 * scale)), capstyle=tk.ROUND)
        canvas.create_line(wrist, palm, fill=graphite, width=max(10, int(16 * scale)), capstyle=tk.ROUND)

        # Decorative label plate on the main link.
        mid_x = (base[0] + shoulder[0]) / 2
        mid_y = (base[1] + shoulder[1]) / 2
        canvas.create_rectangle(mid_x - 16 * scale, mid_y - 20 * scale, mid_x + 18 * scale, mid_y + 22 * scale, outline="#7b8790", fill="#f9a21c", width=1)
        canvas.create_polygon(mid_x - 6 * scale, mid_y - 10 * scale, mid_x + 8 * scale, mid_y - 7 * scale, mid_x - 1 * scale, mid_y + 8 * scale, outline="#68737d", fill="")
        for offset in (-2, 5, 12):
            canvas.create_line(mid_x - 6 * scale, mid_y + offset * scale, mid_x + 12 * scale, mid_y + (offset + 7) * scale, fill="#68737d", width=1)

        def draw_joint(x: float, y: float, radius: float) -> None:
            r = radius * scale
            glow = 3 * pulse * scale
            canvas.create_oval(x - r - glow, y - r - glow, x + r + glow, y + r + glow, fill="#fff3d9", outline="")
            canvas.create_oval(x - r, y - r, x + r, y + r, fill=joint, outline=orange_dark, width=2)
            inner = r * 0.55
            canvas.create_oval(x - inner, y - inner, x + inner, y + inner, fill="#3e444b", outline="#59616a", width=1)
            bolt_r = max(1.5, r * 0.10)
            for idx in range(8):
                angle = idx * math.pi / 4 + tick * 0.015
                bx = x + math.cos(angle) * r * 0.68
                by = y + math.sin(angle) * r * 0.68
                canvas.create_oval(bx - bolt_r, by - bolt_r, bx + bolt_r, by + bolt_r, fill="#777f87", outline="")

        draw_joint(base[0], base[1], 25)
        draw_joint(shoulder[0], shoulder[1], 28)
        draw_joint(elbow[0], elbow[1], 22)
        draw_joint(wrist[0], wrist[1], 14)

        dx = palm[0] - wrist[0]
        dy = palm[1] - wrist[1]
        length = max(math.hypot(dx, dy), 1.0)
        ux, uy = dx / length, dy / length
        nx, ny = -uy, ux
        hinge = palm
        openness = 7 if is_fist else 22
        jaw_len = 28 * scale
        side = 10 * scale
        for sign in (-1, 1):
            start = (hinge[0] + nx * sign * side, hinge[1] + ny * sign * side)
            end = (hinge[0] + ux * jaw_len + nx * sign * openness * scale, hinge[1] + uy * jaw_len + ny * sign * openness * scale)
            canvas.create_line(start, end, fill="#575f66", width=max(4, int(6 * scale)), capstyle=tk.ROUND)
        if is_fist:
            canvas.create_arc(hinge[0] - 18 * scale, hinge[1] - 18 * scale, hinge[0] + 18 * scale, hinge[1] + 18 * scale, start=25, extent=310, outline="#56616a", width=max(3, int(4 * scale)), style=tk.ARC)

        if is_turn:
            arc_r = 34 * scale
            canvas.create_arc(wrist[0] - arc_r, wrist[1] - arc_r, wrist[0] + arc_r, wrist[1] + arc_r, start=30 + tick * 4, extent=260, outline=UI_ACCENT_DARK, width=max(2, int(3 * scale)), style=tk.ARC)
            canvas.create_polygon(wrist[0] + 26 * scale, wrist[1] - 22 * scale, wrist[0] + 40 * scale, wrist[1] - 18 * scale, wrist[0] + 29 * scale, wrist[1] - 7 * scale, fill=UI_ACCENT_DARK, outline="")

        if label == UNKNOWN_LABEL:
            canvas.create_text(width - 22, height - 24, text="?", anchor="e", fill="#d1495b", font=("Segoe UI", 22, "bold"))
    def _metric(self, parent: ttk.Frame, title: str, var: tk.StringVar, column: int) -> None:
        frame = ttk.LabelFrame(parent, text=title, padding=12, style="Metric.TLabelframe")
        frame.grid(row=0, column=column, sticky="ew", padx=4)
        ttk.Label(frame, textvariable=var, font=("Segoe UI", 16, "bold"), background=UI_CARD_SOFT, foreground=UI_TEXT).pack(anchor="w")

    def _build_right_panel(self, right: ttk.Frame) -> None:
        right.columnconfigure(0, weight=1)
        right.rowconfigure(0, weight=1)

        notebook = ttk.Notebook(right)
        notebook.grid(row=0, column=0, sticky="nsew")

        controls = ttk.Frame(notebook, padding=10)
        sequences_tab = ttk.Frame(notebook, padding=10)
        help_tab = ttk.Frame(notebook, padding=10)
        notebook.add(controls, text="Control")
        notebook.add(sequences_tab, text="Secuencias")
        notebook.add(help_tab, text="Ayuda")

        controls.columnconfigure(0, weight=1)
        controls.rowconfigure(1, weight=0)
        controls.rowconfigure(2, weight=1)
        sequences_tab.columnconfigure(0, weight=1)
        sequences_tab.rowconfigure(1, weight=1)

        mode_box = ttk.LabelFrame(controls, text="Modo de detección", padding=10)
        mode_box.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        mode_box.columnconfigure(0, weight=1)
        ttk.Radiobutton(mode_box, text="Simple", variable=self.detection_mode, value="Simple").grid(row=0, column=0, sticky="w")
        ttk.Radiobutton(mode_box, text="Conjunta", variable=self.detection_mode, value="Conjunta").grid(row=0, column=1, sticky="w", padx=(12, 0))

        calibration = ttk.LabelFrame(controls, text="Calibración guiada", padding=10)
        calibration.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        calibration.columnconfigure(0, weight=1)

        ttk.Label(calibration, textvariable=self.calibration_instruction, wraplength=300).grid(
            row=0, column=0, sticky="ew", pady=(0, 8)
        )
        ttk.Label(calibration, textvariable=self.calibration_progress, font=("Segoe UI", 11, "bold")).grid(
            row=1, column=0, sticky="ew", pady=(0, 8)
        )
        self.calibration_step_vars = {}
        for idx, (gesture, _) in enumerate(CALIBRATION_STEPS):
            enabled = gesture != "Flexion brazo"
            var = tk.BooleanVar(value=enabled)
            self.calibration_step_vars[gesture] = var
            ttk.Checkbutton(calibration, text=display_label(gesture), variable=var).grid(
                row=2 + idx, column=0, sticky="w"
            )

        manual_row = 2 + len(CALIBRATION_STEPS)
        ttk.Label(calibration, text="Calibración manual").grid(row=manual_row, column=0, sticky="w", pady=(8, 2))
        self.manual_gesture_var = tk.StringVar(value=display_label("Puno cerrado"))
        ttk.Combobox(calibration, values=DISPLAY_GESTURES, textvariable=self.manual_gesture_var, state="readonly").grid(
            row=manual_row + 1, column=0, sticky="ew"
        )
        manual_time = ttk.Frame(calibration)
        manual_time.grid(row=manual_row + 2, column=0, sticky="ew", pady=(6, 0))
        manual_time.columnconfigure(1, weight=1)
        ttk.Label(manual_time, text="Segundos").grid(row=0, column=0, sticky="w", padx=(0, 6))
        self.manual_seconds_var = tk.StringVar(value="6")
        ttk.Entry(manual_time, textvariable=self.manual_seconds_var, width=8).grid(row=0, column=1, sticky="w")
        self.manual_calibration_button = ttk.Button(calibration, text="Iniciar calibración manual", command=self._toggle_manual_calibration, style="Secondary.TButton")
        self.manual_calibration_button.grid(
            row=manual_row + 3, column=0, sticky="ew", pady=(8, 0)
        )

        button_row = manual_row + 4
        calibration_actions = ttk.Frame(calibration, style="Surface.TFrame")
        calibration_actions.grid(row=button_row, column=0, sticky="ew", pady=(8, 0))
        calibration_actions.columnconfigure((0, 1), weight=1)
        ttk.Button(calibration_actions, text="Calibrar seleccionados", command=self._start_full_calibration, style="Accent.TButton").grid(
            row=0, column=0, sticky="ew", padx=(0, 4)
        )
        ttk.Button(calibration_actions, text="Guardar CSV bruto", command=self._save_raw_csv, style="Secondary.TButton").grid(
            row=0, column=1, sticky="ew", padx=(4, 0)
        )

        profile_box = ttk.LabelFrame(controls, text="Perfil calibrado", padding=10)
        profile_box.grid(row=2, column=0, sticky="nsew")
        profile_box.columnconfigure(0, weight=1)
        profile_box.rowconfigure(0, weight=1)
        self.profile_list = tk.Listbox(profile_box, height=4)
        self.profile_list.grid(row=0, column=0, sticky="nsew")
        self.profile_list.configure(bg="#ffffff", fg=UI_TEXT, relief="flat", highlightthickness=1, highlightbackground=UI_BORDER, selectbackground=UI_DARK, selectforeground="#ffffff")
        profile_actions = ttk.Frame(profile_box, style="Surface.TFrame")
        profile_actions.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        profile_actions.columnconfigure(0, weight=1)
        ttk.Button(profile_actions, text="Borrar calibración seleccionada", command=self._delete_selected_calibration, style="Danger.TButton").grid(row=0, column=0, sticky="ew")
        ttk.Button(profile_actions, text="Borrar perfil completo", command=self._clear_profile, style="Danger.TButton").grid(row=1, column=0, sticky="ew", pady=(6, 0))

        security = ttk.LabelFrame(sequences_tab, text="Secuencias seguras", padding=10)
        security.grid(row=0, column=0, sticky="ew")
        security.columnconfigure(0, weight=1)
        ttk.Button(security, text="Desbloquear secuencias", command=self._unlock_security, style="Accent.TButton").grid(
            row=0, column=0, sticky="ew"
        )
        ttk.Button(security, text="Grabar secuencia", command=self._toggle_sequence_recording, style="Secondary.TButton").grid(
            row=1, column=0, sticky="ew", pady=(8, 0)
        )
        ttk.Button(security, text="Guardar secuencia grabada", command=self._save_sequence, style="Secondary.TButton").grid(
            row=2, column=0, sticky="ew", pady=(8, 0)
        )

        sequences = ttk.LabelFrame(sequences_tab, text="Lista de secuencias", padding=10)
        sequences.grid(row=1, column=0, sticky="nsew", pady=(10, 0))
        sequences.columnconfigure(0, weight=1)
        sequences.rowconfigure(0, weight=1)
        self.sequence_list = tk.Listbox(sequences)
        self.sequence_list.grid(row=0, column=0, sticky="nsew")
        self.sequence_list.configure(bg="#ffffff", fg="#263445", relief="flat", highlightthickness=1, highlightbackground="#c8d4e3", selectbackground=UI_DARK, selectforeground="#ffffff")
        ttk.Button(sequences, text="Imprimir secuencia", command=self._print_selected_sequence).grid(
            row=1, column=0, sticky="ew", pady=(8, 0)
        )

        self._build_help_tab(help_tab)

    def _build_help_tab(self, help_tab: ttk.Frame) -> None:
        help_tab.columnconfigure(0, weight=1)
        help_tab.rowconfigure(0, weight=1)

        help_text = tk.Text(help_tab, wrap="word", height=20)
        help_text.grid(row=0, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(help_tab, command=help_text.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        help_text.configure(yscrollcommand=scroll.set, bg="#ffffff", fg="#263445", relief="flat", padx=12, pady=10, font=("Segoe UI", 10))

        content = """
FUNCIONAMIENTO DE LA APP

1. Conexión
Selecciona el puerto serie de la placa y deja 115200 baudios. Conectar empieza a leer las líneas que imprime el firmware. Simular genera datos falsos para probar la interfaz sin placa.

2. Detección en vivo
La zona principal muestra el gesto reconocido, la confianza, la frecuencia, la magnitud y la fase. A la derecha aparece una representación del brazo robótico que cambia según el movimiento detectado. En modo Simple se muestra solo el gesto dominante. En modo Conjunta se permiten combinaciones como Extensión de brazo + Puño cerrado. La gráfica superior representa magnitud y fase recientes.

3. Calibración
Marca los gestos que quieras calibrar y pulsa Calibrar seleccionados. En manual, elige un movimiento, escribe los segundos de captura y pulsa Iniciar calibración manual; se detiene y guarda solo al terminar ese tiempo. Por defecto se calibra reposo, puño cerrado, giro de muñeca y extensión; flexión queda desmarcado por ahora. En cada paso hay 3 segundos para prepararse y 6 segundos de captura. En los gestos de giro, flexión y extensión también se guardan picos para reducir detecciones arrastradas.

4. Perfil calibrado
Reposo es la referencia principal. Cada movimiento se guarda como cambio respecto a Reposo por frecuencia; si no hay un cambio claro frente a Reposo, se muestra Reposo. Giro, flexión y extensión tienen control adicional de picos para reducir detecciones arrastradas. Si dos gestos parecen activos a la vez, la app puede mostrar una combinación como Extensión de brazo + Puño cerrado. Puedes borrar una calibración concreta desde Perfil calibrado.

5. CSV bruto
Guarda las últimas muestras recibidas en un CSV para analizarlas luego en Excel, Python o MATLAB.

6. Secuencias seguras
Primero crea o introduce la contraseña. Después puedes grabar una secuencia de gestos detectados, guardarla con un nombre y seleccionarla en la lista para imprimirla.

7. Recomendaciones
Usa electrodos bien colocados, evita mover cables durante la calibración y repite cada gesto siempre de una forma parecida. Si la confianza baja mucho o confunde movimientos, borra el perfil y calibra otra vez.
"""
        help_text.insert(tk.END, content.strip())
        help_text.configure(state="disabled")

    def _refresh_ports(self) -> None:
        if serial is None:
            self.port_combo["values"] = []
            self._log("pyserial no esta instalado. Puedes usar el modo simulacion.")
            return
        ports = [port.device for port in serial.tools.list_ports.comports()]
        self.port_combo["values"] = ports
        if ports and not self.port_combo.get():
            self.port_combo.set(ports[0])

    def _toggle_connection(self) -> None:
        if self.reader:
            self._stop_reader()
            return
        port = self.port_combo.get()
        if not port:
            messagebox.showwarning("Puerto requerido", "Selecciona un puerto serie.")
            return
        try:
            baud = int(self.baud_var.get())
        except ValueError:
            messagebox.showwarning("Baudios inválidos", "Introduce un número de baudios válido.")
            return
        self.reader = SerialReader(port, baud, self.queue)
        self.reader.start()
        self.connect_button.configure(text="Desconectar")
        self.connection_status.set("Conectando...")

    def _start_simulator(self) -> None:
        if self.reader:
            self._stop_reader()
        self.reader = Simulator(self.queue)
        self.reader.start()
        self.connect_button.configure(text="Detener")
        self.connection_status.set("Simulacion")

    def _stop_reader(self) -> None:
        if self.reader:
            self.reader.stop()
            self.reader = None
        if self.calibration_wizard_active or self.is_calibrating:
            self.calibration_wizard_active = False
            self.manual_calibration_active = False
            self.is_calibrating = False
            if hasattr(self, "manual_calibration_button"):
                self.manual_calibration_button.configure(text="Iniciar calibración manual", state="normal")
            self.calibration_progress.set("Calibracion cancelada")
            self.calibration_instruction.set("Marca los gestos y pulsa Calibrar seleccionados.")
        self.connect_button.configure(text="Conectar")
        self.connection_status.set("Desconectado")

    def _poll_queue(self) -> None:
        try:
            while True:
                item = self.queue.get_nowait()
                if isinstance(item, str):
                    self._log(item)
                    if item.startswith("Conectado"):
                        self.connection_status.set(item)
                    continue
                self._handle_sample(item)
        except queue.Empty:
            pass
        self.after(50, self._poll_queue)

    def _handle_sample(self, sample: Sample) -> None:
        self.sample_counter += 1
        self.samples.append(sample)
        self.raw_capture.append(sample)
        self.samples = self.samples[-120:]
        self.raw_capture = self.raw_capture[-5000:]

        self.freq_var.set(f"{sample.frequency_hz:.2f} Hz")
        self.mag_var.set(f"{sample.magnitude_ohm:.2f} Ohm")
        self.phase_var.set(f"{sample.phase_deg:.2f} deg")

        if self.is_calibrating:
            self.calibration_samples.append(sample)
            self.calibration_sample_counter += 1
            self._log_calibration_sample(sample)
            if self.sample_counter % DRAW_INTERVAL == 0:
                self._draw_chart()
            return

        if self.sample_counter % CLASSIFICATION_INTERVAL == 0:
            label, confidence = self.classifier.classify(sample, self.detection_mode.get() == "Conjunta")
            self.last_detected_label = label
            self.last_confidence = confidence
            self._show_detection(label, confidence)
        else:
            label = self.last_detected_label

        if self.sample_counter % DRAW_INTERVAL == 0:
            self._draw_chart()

        if self.is_sequence_recording and label != UNKNOWN_LABEL:
            if not self.sequence_buffer or self.sequence_buffer[-1] != label:
                self.sequence_buffer.append(label)
                self._log(f"Secuencia: {' -> '.join(self.sequence_buffer)}")

    def _draw_chart(self) -> None:
        self.canvas.delete("all")
        width = max(self.canvas.winfo_width(), 1)
        height = max(self.canvas.winfo_height(), 1)
        self.canvas.create_rectangle(0, 0, width, height, fill=UI_DARK, outline="")
        for idx in range(1, 5):
            y = idx * height / 5
            self.canvas.create_line(0, y, width, y, fill="#172033", width=1)
        for idx in range(1, 7):
            x = idx * width / 7
            self.canvas.create_line(x, 0, x, height, fill="#111a2b", width=1)
        self.canvas.create_text(14, 14, text="Magnitud", fill="#8ff0c2", anchor="w", font=("Segoe UI", 9, "bold"))
        self.canvas.create_text(14, int(height * 0.58), text="Fase", fill="#ffd166", anchor="w", font=("Segoe UI", 9, "bold"))
        if len(self.samples) < 2:
            self.canvas.create_text(width / 2, height / 2, text="Esperando muestras", fill="#64748b", font=("Segoe UI", 11))
            return
        mags = [s.magnitude_ohm for s in self.samples]
        phases = [s.phase_deg for s in self.samples]
        self._draw_series(mags, width, height, "#40f2a3", 0.10, 0.50)
        self._draw_series(phases, width, height, "#ffb000", 0.58, 0.92)
        self.canvas.create_rectangle(width - 104, 12, width - 14, 36, fill="#111827", outline="#26364f")
        self.canvas.create_text(width - 59, 24, text=f"{len(self.samples)} muestras", fill="#cbd5e1", font=("Segoe UI", 8))
    def _draw_series(self, values: list[float], width: int, height: int, color: str, top: float, bottom: float) -> None:
        vmin = min(values)
        vmax = max(values)
        if math.isclose(vmin, vmax):
            vmax = vmin + 1.0
        y_top = height * top
        y_bottom = height * bottom
        points = []
        for idx, value in enumerate(values):
            x = idx * width / max(len(values) - 1, 1)
            norm = (value - vmin) / (vmax - vmin)
            y = y_bottom - norm * (y_bottom - y_top)
            points.extend([x, y])
        self.canvas.create_line(points, fill=color, width=2, smooth=True)

    def _toggle_manual_calibration(self) -> None:
        if self.manual_calibration_active:
            return

        if self.calibration_wizard_active or self.is_calibrating:
            return
        if not self.reader:
            messagebox.showwarning("Sin datos", "Conecta la placa o activa Simular antes de calibrar.")
            return

        try:
            seconds = max(1, int(float(self.manual_seconds_var.get())))
        except ValueError:
            messagebox.showwarning("Tiempo inválido", "Introduce segundos válidos para la calibración manual.")
            return

        gesture = INTERNAL_GESTURES_BY_DISPLAY.get(self.manual_gesture_var.get(), self.manual_gesture_var.get())
        if gesture not in GESTURES:
            messagebox.showwarning("Gesto inválido", "Selecciona un gesto válido para calibrar.")
            return
        if gesture != REST_LABEL and REST_LABEL not in self.classifier.profile:
            messagebox.showwarning("Reposo requerido", "Calibra Reposo antes de calibrar movimientos.")
            return

        self.manual_calibration_active = True
        self.calibration_wizard_active = False
        self.is_calibrating = True
        self.calibration_samples = []
        self.current_calibration_gesture = gesture
        self.calibration_sample_counter = 0
        self.classifier.window = []
        self.classifier.label_history = []
        self.calibration_instruction.set(f"Calibración manual activa: {display_label(gesture)}")
        self.calibration_progress.set(f"Capturando manual durante {seconds} s")
        self.manual_calibration_button.configure(text="Capturando manual...", state="disabled")
        self._log("")
        self._log(f"=== MUESTRAS DE CALIBRACIÓN MANUAL: {gesture} ===")
        self._log("N     ID       Frecuencia(Hz)     Magnitud(Ohm)     Fase(deg)")
        self._log(f"Calibración manual iniciada para '{gesture}' durante {seconds} s.")
        self.after(seconds * 1000, self._stop_manual_calibration)

    def _stop_manual_calibration(self) -> None:
        if not self.manual_calibration_active and not self.is_calibrating:
            return
        gesture = self.current_calibration_gesture
        if not gesture:
            return
        self.manual_calibration_active = False
        self.manual_calibration_button.configure(text="Iniciar calibración manual", state="normal")
        self.calibration_progress.set("Guardando calibración manual...")
        self._finish_calibration(gesture)

    def _start_full_calibration(self) -> None:
        if self.calibration_wizard_active or self.is_calibrating:
            return
        if not self.reader:
            messagebox.showwarning("Sin datos", "Conecta la placa o activa Simular antes de calibrar.")
            return

        self.selected_calibration_steps = [
            step for step in CALIBRATION_STEPS
            if self.calibration_step_vars.get(step[0], tk.BooleanVar(value=True)).get()
        ]
        if not self.selected_calibration_steps:
            messagebox.showwarning("Sin gestos", "Selecciona al menos un gesto para calibrar.")
            return
        if REST_LABEL not in self.classifier.profile and self.selected_calibration_steps[0][0] != REST_LABEL:
            messagebox.showwarning("Reposo requerido", "Selecciona Reposo o calibra Reposo antes de calibrar movimientos.")
            return

        self.calibration_wizard_active = True
        self.calibration_step_index = 0
        self.calibration_instruction.set("Calibración iniciada. Sigue las instrucciones de cada paso.")
        self.calibration_progress.set("Preparando...")
        self.classifier.window = []
        self.classifier.label_history = []
        self._log("Calibración completa iniciada.")
        self._prepare_next_calibration_step()

    def _prepare_next_calibration_step(self) -> None:
        if not self.calibration_wizard_active:
            return

        if self.calibration_step_index >= len(self.selected_calibration_steps):
            self.calibration_wizard_active = False
            self.is_calibrating = False
            self.calibration_instruction.set("Calibración terminada. Ya puedes usar la detección en vivo.")
            self.calibration_progress.set("Completada")
            self._log("Calibración completa terminada.")
            messagebox.showinfo("Calibración terminada", "Todos los gestos se han calibrado correctamente.")
            return

        gesture, instruction = self.selected_calibration_steps[self.calibration_step_index]
        step = self.calibration_step_index + 1
        total = len(self.selected_calibration_steps)
        self.calibration_instruction.set(f"Paso {step}/{total}: {instruction}")
        self._log(f"Prepárate para calibrar '{display_label(gesture)}'.")
        self._prep_countdown(gesture, CALIBRATION_PREP_SECONDS)

    def _prep_countdown(self, gesture: str, remaining: int) -> None:
        if not self.calibration_wizard_active:
            return
        if remaining > 0:
            self.calibration_progress.set(f"{display_label(gesture)}: empieza en {remaining} s")
            self.after(1000, lambda: self._prep_countdown(gesture, remaining - 1))
            return
        self._begin_calibration_capture(gesture)

    def _begin_calibration_capture(self, gesture: str) -> None:
        if not self.calibration_wizard_active:
            return
        self.is_calibrating = True
        self.calibration_samples = []
        self.current_calibration_gesture = gesture
        self.calibration_sample_counter = 0
        self.calibration_progress.set(f"{display_label(gesture)}: capturando {CALIBRATION_CAPTURE_SECONDS} s")
        self._log("")
        self._log(f"=== MUESTRAS DE CALIBRACIÓN: {gesture} ===")
        self._log("N     ID       Frecuencia(Hz)     Magnitud(Ohm)     Fase(deg)")
        self._log(f"Calibrando '{display_label(gesture)}' durante {CALIBRATION_CAPTURE_SECONDS} s...")
        self._capture_countdown(gesture, CALIBRATION_CAPTURE_SECONDS)

    def _log_calibration_sample(self, sample: Sample) -> None:
        line = (
            f"{self.calibration_sample_counter:04d}  "
            f"ID={sample.sample_id:<6d}  "
            f"F={sample.frequency_hz:>10.2f} Hz  "
            f"M={sample.magnitude_ohm:>10.2f} Ohm  "
            f"P={sample.phase_deg:>8.2f} deg"
        )
        full_line = f"[{self.current_calibration_gesture}] {line}"
        if self.calibration_sample_counter % CALIBRATION_UI_LOG_EVERY == 0:
            self._log(full_line)
        print(full_line)

    def _capture_countdown(self, gesture: str, remaining: int) -> None:
        if not self.calibration_wizard_active:
            return
        if remaining > 0:
            self.calibration_progress.set(f"{display_label(gesture)}: repite la acción, quedan {remaining} s")
            self.after(1000, lambda: self._capture_countdown(gesture, remaining - 1))
            return
        self._finish_calibration(gesture)

    def _finish_calibration(self, gesture: str) -> None:
        was_manual = not self.calibration_wizard_active
        self.is_calibrating = False
        if len(self.calibration_samples) < 5:
            self.calibration_wizard_active = False
            self.manual_calibration_active = False
            if hasattr(self, "manual_calibration_button"):
                self.manual_calibration_button.configure(text="Iniciar calibración manual", state="normal")
            self.calibration_progress.set("Calibración detenida")
            messagebox.showwarning("Pocas muestras", "No se han recibido suficientes muestras para calibrar.")
            return

        profile = self.classifier.profile.copy()
        if gesture != REST_LABEL and REST_LABEL not in profile:
            self.manual_calibration_active = False
            if hasattr(self, "manual_calibration_button"):
                self.manual_calibration_button.configure(text="Iniciar calibración manual", state="normal")
            self.calibration_progress.set("Primero calibra Reposo")
            messagebox.showwarning("Reposo requerido", "Calibra Reposo antes de calibrar movimientos.")
            return
        rest_profile = profile.get(REST_LABEL) if gesture != REST_LABEL else None
        profile[gesture] = build_gesture_profile(self.calibration_samples, rest_profile)
        self.classifier.set_profile(profile)
        self._save_profile()
        self._refresh_profile_list()
        self.current_calibration_gesture = ""
        if was_manual:
            self.calibration_instruction.set("Calibración manual guardada")
            self.calibration_progress.set("Manual completada")
        self._log(f"Calibración guardada para '{gesture}' con {len(self.calibration_samples)} muestras.")
        self._log(f"=== FIN DE CALIBRACIÓN: {gesture} ===")
        if was_manual:
            return
        self.calibration_step_index += 1
        self.after(1000, self._prepare_next_calibration_step)

    def _load_profile(self) -> None:
        if PROFILE_PATH.exists():
            with PROFILE_PATH.open("r", encoding="utf-8") as file:
                self.classifier.set_profile(json.load(file))
        self._refresh_profile_list()

    def _save_profile(self) -> None:
        with PROFILE_PATH.open("w", encoding="utf-8") as file:
            json.dump(self.classifier.profile, file, indent=2, ensure_ascii=False)

    def _refresh_profile_list(self) -> None:
        self.profile_list.delete(0, tk.END)
        for label, stats in self.classifier.profile.items():
            self.profile_list.insert(
                tk.END,
                f"{display_label(label)}: {stats['magnitude_mean']:.1f} Ohm, {stats['phase_mean']:.1f} deg",
            )
        if self.classifier.is_ready():
            self.current_label.set("Esperando movimiento")

    def _delete_selected_calibration(self) -> None:
        index = self.profile_list.curselection()
        if not index:
            messagebox.showinfo("Sin selección", "Selecciona una calibración del perfil.")
            return

        label = list(self.classifier.profile.keys())[index[0]]
        if not messagebox.askyesno("Borrar calibración", f"Borrar solo la calibración de '{label}'?"):
            return

        profile = self.classifier.profile.copy()
        profile.pop(label, None)
        self.classifier.set_profile(profile)
        if profile:
            self._save_profile()
        elif PROFILE_PATH.exists():
            PROFILE_PATH.unlink()
        self._refresh_profile_list()
        if not profile:
            self.current_label.set("Sin calibrar")
        self._log(f"Calibración borrada: {label}")

    def _clear_profile(self) -> None:
        if not messagebox.askyesno("Borrar perfil", "¿Seguro que quieres borrar la calibración actual?"):
            return
        self.classifier.set_profile({})
        if PROFILE_PATH.exists():
            PROFILE_PATH.unlink()
        self._refresh_profile_list()
        self.current_label.set("Sin calibrar")

    def _save_raw_csv(self) -> None:
        if not self.raw_capture:
            messagebox.showinfo("Sin datos", "Todavía no hay muestras para guardar.")
            return
        default_name = time.strftime("captura_%Y%m%d_%H%M%S.csv")
        path = filedialog.asksaveasfilename(
            initialdir=CSV_DIR,
            initialfile=default_name,
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
        )
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(["sample_id", "timestamp", "frequency_hz", "magnitude_ohm", "phase_deg"])
            for sample in self.raw_capture:
                writer.writerow(
                    [sample.sample_id, sample.timestamp, sample.frequency_hz, sample.magnitude_ohm, sample.phase_deg]
                )
        self._log(f"CSV guardado: {path}")

    def _load_password_hash(self) -> str | None:
        if not SEQUENCES_PATH.exists():
            return None
        try:
            with SEQUENCES_PATH.open("r", encoding="utf-8") as file:
                return json.load(file).get("password_hash")
        except Exception:
            return None

    def _hash_password(self, password: str) -> str:
        return hashlib.sha256(password.encode("utf-8")).hexdigest()

    def _unlock_security(self) -> None:
        password = simpledialog.askstring("Contraseña", "Introduce la contraseña de administrador:", show="*")
        if password and self._hash_password(password) == SECURITY_PASSWORD_HASH:
            self.security_unlocked = True
            self.password_hash = SECURITY_PASSWORD_HASH
            self._log("Sistema de secuencias desbloqueado.")
        else:
            self.security_unlocked = False
            messagebox.showerror("Contraseña incorrecta", "No se pudo desbloquear.")

    def _toggle_sequence_recording(self) -> None:
        if not self.security_unlocked:
            messagebox.showwarning("Bloqueado", "Desbloquea el sistema con contraseña primero.")
            return
        self.is_sequence_recording = not self.is_sequence_recording
        if self.is_sequence_recording:
            self.sequence_buffer = []
            self._log("Grabando secuencia de movimientos...")
        else:
            self._log("Grabación de secuencia detenida.")

    def _load_sequences(self) -> None:
        self.sequences: dict[str, list[str]] = {}
        if SEQUENCES_PATH.exists():
            try:
                with SEQUENCES_PATH.open("r", encoding="utf-8") as file:
                    data = json.load(file)
                self.sequences = data.get("sequences", {})
            except Exception:
                self.sequences = {}
        self._refresh_sequence_list()

    def _save_sequences(self) -> None:
        with SEQUENCES_PATH.open("w", encoding="utf-8") as file:
            json.dump(
                {"password_hash": self.password_hash, "sequences": self.sequences},
                file,
                indent=2,
                ensure_ascii=False,
            )
        self._refresh_sequence_list()

    def _save_sequence(self) -> None:
        if not self.security_unlocked:
            messagebox.showwarning("Bloqueado", "Desbloquea el sistema con contraseña primero.")
            return
        if not self.sequence_buffer:
            messagebox.showinfo("Sin secuencia", "Graba al menos un movimiento.")
            return
        name = simpledialog.askstring("Nombre", "Nombre de la secuencia:")
        if not name:
            return
        self.sequences[name] = self.sequence_buffer[:]
        self._save_sequences()
        readable_sequence = " -> ".join(display_label(label) for label in self.sequence_buffer)
        self._log(f"Secuencia guardada '{name}': {readable_sequence}")

    def _refresh_sequence_list(self) -> None:
        self.sequence_list.delete(0, tk.END)
        for name, sequence in self.sequences.items():
            readable_sequence = " -> ".join(display_label(label) for label in sequence)
            self.sequence_list.insert(tk.END, f"{name}: {readable_sequence}")

    def _print_selected_sequence(self) -> None:
        index = self.sequence_list.curselection()
        if not index:
            return
        name = list(self.sequences.keys())[index[0]]
        sequence = " -> ".join(display_label(label) for label in self.sequences[name])
        print(f"{name}: {sequence}")
        self._log(f"Impreso en consola: {name}: {sequence}")

    def _log(self, message: str) -> None:
        self.log_text.insert(tk.END, f"{time.strftime('%H:%M:%S')}  {message}\n")
        line_count = int(self.log_text.index("end-1c").split(".")[0])
        if line_count > UI_LOG_MAX_LINES:
            self.log_text.delete("1.0", f"{line_count - UI_LOG_MAX_LINES}.0")
        self.log_text.see(tk.END)

    def _on_close(self) -> None:
        self._stop_reader()
        if getattr(self, "_visual_animation_job", None):
            try:
                self.after_cancel(self._visual_animation_job)
            except tk.TclError:
                pass
        self.destroy()


if __name__ == "__main__":
    app = GestureApp()
    app.mainloop()

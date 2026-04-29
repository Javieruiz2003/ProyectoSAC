from __future__ import annotations

from pathlib import Path
import tkinter as tk

from .controller import AppController
from .services.arm import ArmService
from .services.sensor import SensorService
from .storage import JsonStorage
from .ui.main_window import MainWindow


def build_controller(base_dir: Path) -> AppController:
    return AppController(
        storage=JsonStorage(base_dir),
        sensor=SensorService(),
        arm=ArmService(),
    )


def run() -> None:
    base_dir = Path(__file__).resolve().parent.parent
    controller = build_controller(base_dir)

    root = tk.Tk()
    def _on_close() -> None:
        controller.shutdown()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", _on_close)
    MainWindow(root, controller)
    root.mainloop()

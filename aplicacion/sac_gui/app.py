from __future__ import annotations

from pathlib import Path
import tkinter as tk

from .controller import AppController
from .services.arm import ArmService
from .services.sensor import SensorService
from .storage import JsonStorage
from .ui.main_window import MainWindow


def _set_windows_app_id() -> None:
    import ctypes
    from ctypes import wintypes
    import sys

    if sys.platform != "win32":
        return

    try:
        shell32 = ctypes.WinDLL("shell32", use_last_error=True)
        shell32.SetCurrentProcessExplicitAppUserModelID.argtypes = [wintypes.LPCWSTR]
        shell32.SetCurrentProcessExplicitAppUserModelID.restype = ctypes.c_long
        shell32.SetCurrentProcessExplicitAppUserModelID("ProyectoSAC.Operator")
    except (AttributeError, OSError, TypeError):
        return


def _apply_computer_photo_icon(root: tk.Tk) -> None:
    icon = tk.PhotoImage(width=64, height=64)

    def fill(color: str, x1: int, y1: int, x2: int, y2: int) -> None:
        icon.put(color, to=(x1, y1, x2, y2))

    fill("#0a3340", 8, 9, 56, 43)
    fill("#0f4c5c", 10, 11, 54, 41)
    fill("#d8edf0", 14, 15, 50, 35)
    fill("#ffffff", 18, 18, 46, 27)
    fill("#8fbec4", 15, 35, 49, 39)
    fill("#0a3340", 28, 43, 36, 51)
    fill("#0f4c5c", 23, 51, 41, 55)
    fill("#c56a2d", 19, 55, 45, 59)

    root.iconphoto(True, icon)
    root._sac_photo_icon = icon


def _apply_windows_computer_icon(root: tk.Tk) -> None:
    import ctypes
    from ctypes import wintypes
    import os
    import sys

    if sys.platform != "win32":
        return

    try:
        shell32 = ctypes.WinDLL("shell32", use_last_error=True)
        user32 = ctypes.WinDLL("user32", use_last_error=True)
    except OSError:
        return

    max_path = 260
    wm_seticon = 0x0080
    icon_small = 0
    icon_big = 1
    shgsi_icon = 0x000000100
    shgsi_small_icon = 0x000000001
    siid_desktop_pc = 109

    class SHStockIconInfo(ctypes.Structure):
        _fields_ = [
            ("cbSize", wintypes.DWORD),
            ("hIcon", wintypes.HICON),
            ("iSysImageIndex", ctypes.c_int),
            ("iIcon", ctypes.c_int),
            ("szPath", wintypes.WCHAR * max_path),
        ]

    def _load_stock_icon(flags: int):
        try:
            shell32.SHGetStockIconInfo.argtypes = [
                ctypes.c_int,
                wintypes.UINT,
                ctypes.POINTER(SHStockIconInfo),
            ]
            shell32.SHGetStockIconInfo.restype = ctypes.c_long
        except AttributeError:
            return None

        icon_info = SHStockIconInfo()
        icon_info.cbSize = ctypes.sizeof(icon_info)
        result = shell32.SHGetStockIconInfo(
            siid_desktop_pc,
            shgsi_icon | flags,
            ctypes.byref(icon_info),
        )
        if result != 0:
            return None
        return icon_info.hIcon

    def _load_shell32_icon():
        icon_library = (
            Path(os.environ.get("SystemRoot", r"C:\Windows"))
            / "System32"
            / "shell32.dll"
        )
        try:
            shell32.ExtractIconW.argtypes = [
                wintypes.HINSTANCE,
                wintypes.LPCWSTR,
                wintypes.UINT,
            ]
            shell32.ExtractIconW.restype = wintypes.HICON
        except AttributeError:
            return None

        icon_handle = shell32.ExtractIconW(None, str(icon_library), 15)
        if not icon_handle or icon_handle == 1:
            return None
        return icon_handle

    large_icon = _load_stock_icon(0) or _load_shell32_icon()
    small_icon = _load_stock_icon(shgsi_small_icon) or large_icon
    if not large_icon and not small_icon:
        return

    try:
        root.update_idletasks()
        hwnd = wintypes.HWND(root.winfo_id())
        user32.SendMessageW.argtypes = [
            wintypes.HWND,
            wintypes.UINT,
            wintypes.WPARAM,
            wintypes.LPARAM,
        ]
        user32.SendMessageW.restype = wintypes.LPARAM
        user32.SendMessageW(hwnd, wm_seticon, icon_big, large_icon or small_icon)
        user32.SendMessageW(hwnd, wm_seticon, icon_small, small_icon or large_icon)
        root._sac_windows_icon_handles = [large_icon, small_icon]
    except tk.TclError:
        return


def build_controller(base_dir: Path) -> AppController:
    return AppController(
        storage=JsonStorage(base_dir),
        sensor=SensorService(),
        arm=ArmService(),
    )


def run() -> None:
    base_dir = Path(__file__).resolve().parent.parent
    controller = build_controller(base_dir)

    _set_windows_app_id()
    root = tk.Tk()
    _apply_computer_photo_icon(root)

    def _on_close() -> None:
        controller.shutdown()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", _on_close)
    MainWindow(root, controller)
    _apply_windows_computer_icon(root)
    root.mainloop()

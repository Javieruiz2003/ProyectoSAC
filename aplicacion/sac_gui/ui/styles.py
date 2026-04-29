from __future__ import annotations

from tkinter import ttk

PALETTE = {
    "bg": "#f4efe8",
    "surface": "#fffdf9",
    "surface_alt": "#e7ded2",
    "primary": "#0f4c5c",
    "primary_dark": "#0a3340",
    "accent": "#c56a2d",
    "accent_dark": "#9d5223",
    "text": "#1f2933",
    "muted": "#52606d",
    "success": "#245f45",
}


def apply_styles(root) -> ttk.Style:
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except Exception:
        pass

    root.configure(bg=PALETTE["bg"])

    style.configure(".", font=("Segoe UI", 9), foreground=PALETTE["text"])
    style.configure("App.TFrame", background=PALETTE["bg"])
    style.configure("Card.TFrame", background=PALETTE["surface"], relief="flat")
    style.configure("Banner.TFrame", background=PALETTE["primary"])

    style.configure(
        "BannerTitle.TLabel",
        background=PALETTE["primary"],
        foreground="#ffffff",
        font=("Segoe UI Semibold", 18),
    )
    style.configure(
        "BannerSubtitle.TLabel",
        background=PALETTE["primary"],
        foreground="#d8edf0",
        font=("Segoe UI", 9),
    )
    style.configure(
        "SectionTitle.TLabel",
        background=PALETTE["surface"],
        foreground=PALETTE["primary_dark"],
        font=("Segoe UI Semibold", 12),
    )
    style.configure(
        "Body.TLabel",
        background=PALETTE["surface"],
        foreground=PALETTE["text"],
    )
    style.configure(
        "Muted.TLabel",
        background=PALETTE["surface"],
        foreground=PALETTE["muted"],
    )
    style.configure(
        "Status.TLabel",
        background=PALETTE["surface"],
        foreground=PALETTE["success"],
        font=("Segoe UI Semibold", 10),
    )
    style.configure(
        "Value.TLabel",
        background=PALETTE["surface"],
        foreground=PALETTE["text"],
        font=("Segoe UI Semibold", 10),
    )

    style.configure(
        "Primary.TButton",
        background=PALETTE["accent"],
        foreground="#ffffff",
        borderwidth=0,
        focusthickness=0,
        padding=(12, 8),
        font=("Segoe UI Semibold", 10),
    )
    style.map(
        "Primary.TButton",
        background=[("active", PALETTE["accent_dark"]), ("disabled", "#d8c3b1")],
        foreground=[("disabled", "#faf7f2")],
    )

    style.configure(
        "Secondary.TButton",
        background=PALETTE["surface_alt"],
        foreground=PALETTE["primary_dark"],
        borderwidth=0,
        focusthickness=0,
        padding=(10, 7),
        font=("Segoe UI Semibold", 10),
    )
    style.map(
        "Secondary.TButton",
        background=[("active", "#d9cfbf"), ("disabled", "#efebe5")],
        foreground=[("disabled", "#8c8c8c")],
    )

    style.configure(
        "TEntry",
        fieldbackground="#ffffff",
        background="#ffffff",
        padding=6,
        bordercolor=PALETTE["surface_alt"],
    )
    style.configure(
        "Form.TEntry",
        fieldbackground="#ffffff",
        background="#ffffff",
        padding=(8, 6),
        bordercolor=PALETTE["surface_alt"],
        relief="flat",
    )
    style.configure(
        "Form.TCombobox",
        fieldbackground="#ffffff",
        background="#ffffff",
        padding=(6, 4),
        bordercolor=PALETTE["surface_alt"],
        relief="flat",
    )
    style.configure(
        "TNotebook",
        background=PALETTE["bg"],
        borderwidth=0,
        tabmargins=(0, 0, 0, 0),
    )
    style.configure(
        "TNotebook.Tab",
        padding=(14, 7),
        background=PALETTE["surface_alt"],
        foreground=PALETTE["primary_dark"],
        font=("Segoe UI Semibold", 10),
        borderwidth=1,
    )
    style.map(
        "TNotebook.Tab",
        background=[
            ("selected", PALETTE["surface"]),
            ("active", "#f0e7dc"),
            ("disabled", "#d7d2cc"),
        ],
        foreground=[("disabled", "#777777")],
        expand=[("selected", (2, 3, 2, 0)), ("!selected", (0, 0, 0, 0))],
    )
    style.configure(
        "Tabless.TNotebook",
        background=PALETTE["bg"],
        borderwidth=0,
        relief="flat",
        tabmargins=(0, 0, 0, 0),
    )
    style.layout("Tabless.TNotebook.Tab", [])

    style.configure(
        "Treeview",
        background="#ffffff",
        fieldbackground="#ffffff",
        foreground=PALETTE["text"],
        rowheight=26,
        bordercolor=PALETTE["surface_alt"],
    )
    style.configure(
        "Treeview.Heading",
        background=PALETTE["surface_alt"],
        foreground=PALETTE["primary_dark"],
        font=("Segoe UI Semibold", 10),
    )
    style.map(
        "Treeview",
        background=[("selected", "#d6ebe7")],
        foreground=[("selected", PALETTE["text"])],
    )
    style.configure(
        "TCheckbutton",
        background=PALETTE["surface"],
        foreground=PALETTE["primary_dark"],
        font=("Segoe UI Semibold", 10),
    )

    return style

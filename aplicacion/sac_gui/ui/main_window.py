from __future__ import annotations

import math
import tkinter as tk
from tkinter import messagebox, ttk

from ..controller import AppController
from ..models import BiometricData, HandPose
from ..services.sensor import UartSensorConfig
from .styles import PALETTE, apply_styles

TRACKING_SLIDERS = (
    ("height_pct", "Altura de la mano", 0.0, 100.0, "percent"),
    ("reach_pct", "Avance", 0.0, 100.0, "percent"),
    ("lateral_pct", "Desplazamiento lateral", -100.0, 100.0, "signed_percent"),
    ("wrist_deg", "Giro de muñeca", -90.0, 90.0, "degrees"),
    ("grip_pct", "Apertura de la mano", 0.0, 100.0, "percent"),
)
TRACKING_CANVAS_WIDTH = 430
TRACKING_CANVAS_HEIGHT = 168
VIEW_PANEL_MAX_HEIGHT = 690
VIEW_PANEL_MIN_HEIGHT = 480
VIEW_PANEL_BOTTOM_MARGIN = 14
VIEW_TAB_PADDING = (16, 18, 16, 14)
ACTIVITY_PANEL_WIDTH = 320


class MainWindow(ttk.Frame):
    def __init__(self, root: tk.Tk, controller: AppController) -> None:
        self.root = root
        self.controller = controller

        apply_styles(root)
        root.title("Proyecto SAC | Aplicación de operador")
        root.geometry("1520x880")
        root.minsize(1300, 760)

        super().__init__(root, style="App.TFrame", padding=14)
        self.pack(fill="both", expand=True)
        self._height_limited_panels: list[tk.Frame] = []

        self._build_variables()
        self._build_layout()
        self.root.bind("<Configure>", self._resize_height_limited_panels, add="+")
        self.root.after_idle(self._resize_height_limited_panels)
        self.refresh_view()
        self._refresh_detected_ports(log_detection=False)
        self.log("Aplicación iniciada.")
        self.log(self.controller.get_sensor_snapshot().status_text)

    def _build_variables(self) -> None:
        sensor_config = self.controller.get_sensor_config()
        self._syncing_tracking_ui = False
        self.session_access_var = tk.StringVar()
        self.session_mode_var = tk.StringVar()
        self.session_user_var = tk.StringVar()
        self.session_profile_var = tk.StringVar()
        self.sensor_status_var = tk.StringVar()
        self.sensor_source_var = tk.StringVar()
        self.sensor_hw_var = tk.StringVar()
        self.sensor_ports_var = tk.StringVar(
            value="Pulsa 'Detectar puertos' para buscar interfaces serie disponibles."
        )
        self.normal_hint_var = tk.StringVar()
        self.calibration_profile_var = tk.StringVar()
        self.control_profile_var = tk.StringVar()
        self.command_profile_var = tk.StringVar()
        self.control_status_var = tk.StringVar(value="Sin acciones enviadas.")
        self.realtime_status_var = tk.StringVar(
            value="Seguimiento listo. Activa el modo en tiempo real para empezar."
        )
        self.hand_pose_summary_var = tk.StringVar()
        self.arm_pose_summary_var = tk.StringVar()

        self.normal_username_var = tk.StringVar()
        self.normal_password_var = tk.StringVar(value="brazo123")
        self.arm_code_var = tk.StringVar(value="2468")
        self.admin_usb_var = tk.StringVar(value="MASTER-USB-001")

        self.register_username_var = tk.StringVar()
        self.register_password_var = tk.StringVar()
        self.register_confirm_var = tk.StringVar()
        self.command_name_var = tk.StringVar()
        self.command_duration_var = tk.StringVar(value="1000")
        self.sensor_mode_var = tk.StringVar(
            value="UART" if sensor_config.source_mode == "uart" else "Simulación"
        )
        self.sensor_port_var = tk.StringVar(value=sensor_config.port)
        self.sensor_baudrate_var = tk.StringVar(value=str(sensor_config.baudrate))
        self.sensor_data_type_var = tk.StringVar(value=sensor_config.data_type)
        self.sensor_byte_order_var = tk.StringVar(value=sensor_config.byte_order)
        self.sensor_average_var = tk.StringVar(value=str(sensor_config.averaging_window))
        self.sensor_timeout_var = tk.StringVar(value=str(sensor_config.timeout_ms))
        self.sensor_magnitude_scale_var = tk.StringVar(
            value=f"{sensor_config.magnitude_scale:g}"
        )
        self.sensor_phase_scale_var = tk.StringVar(
            value=f"{sensor_config.phase_scale:g}"
        )

        self.registration_measurement_vars = self._make_measurement_vars()
        self.calibration_measurement_vars = self._make_measurement_vars()
        self.realtime_enabled_var = tk.BooleanVar(value=False)
        self.realtime_pose_vars = {
            key: tk.DoubleVar(value=50.0 if key != "lateral_pct" and key != "wrist_deg" else 0.0)
            for key, _, _, _, _ in TRACKING_SLIDERS
        }
        self.realtime_value_vars = {
            key: tk.StringVar(value="")
            for key, _, _, _, _ in TRACKING_SLIDERS
        }

    def _make_measurement_vars(self) -> dict[str, tk.StringVar]:
        return {
            "resistance_ohm": tk.StringVar(value="0.0"),
            "reactance_ohm": tk.StringVar(value="0.0"),
            "phase_deg": tk.StringVar(value="0.0"),
            "quality_index": tk.StringVar(value="0.0"),
        }

    def _build_layout(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        self._build_header()

        content = ttk.Frame(self, style="App.TFrame")
        content.grid(row=1, column=0, sticky="nsew", pady=(12, 0))
        content.columnconfigure(0, weight=0)
        content.columnconfigure(1, weight=1)
        content.columnconfigure(2, weight=0)
        content.rowconfigure(0, weight=1)

        self._build_sidebar(content)
        self._build_notebook(content)
        self._build_log_panel(content)

    def _build_header(self) -> None:
        header = ttk.Frame(self, style="Banner.TFrame", padding=(20, 14))
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)

        ttk.Label(
            header,
            text="Proyecto SAC",
            style="BannerTitle.TLabel",
        ).grid(row=0, column=0, sticky="w")
        ttk.Label(
            header,
            text=(
                "Interfaz de escritorio para autenticación, perfiles, calibración, "
                "captura y control del brazo."
            ),
            style="BannerSubtitle.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(4, 0))

    def _build_sidebar(self, parent: ttk.Frame) -> None:
        sidebar = ttk.Frame(parent, style="App.TFrame")
        sidebar.grid(row=0, column=0, sticky="nsw", padx=(0, 14))

        session_card = ttk.Frame(sidebar, style="Card.TFrame", padding=14)
        session_card.grid(row=0, column=0, sticky="ew")
        ttk.Label(session_card, text="Estado de sesión", style="SectionTitle.TLabel").grid(
            row=0, column=0, sticky="w", columnspan=2
        )
        self._add_status_row(session_card, 1, "Acceso", self.session_access_var)
        self._add_status_row(session_card, 2, "Modo", self.session_mode_var)
        self._add_status_row(session_card, 3, "Usuario", self.session_user_var)
        self._add_status_row(session_card, 4, "Perfil", self.session_profile_var)
        ttk.Button(
            session_card,
            text="Cerrar sesión",
            style="Secondary.TButton",
            command=self._on_logout,
        ).grid(row=5, column=0, columnspan=2, sticky="ew", pady=(16, 0))

        sensor_card = ttk.Frame(sidebar, style="Card.TFrame", padding=14)
        sensor_card.grid(row=1, column=0, sticky="ew", pady=(14, 0))
        ttk.Label(sensor_card, text="Sensor AD5940", style="SectionTitle.TLabel").grid(
            row=0, column=0, sticky="w", columnspan=2
        )
        self._add_status_row(sensor_card, 1, "Fuente", self.sensor_source_var)
        self._add_status_row(sensor_card, 2, "Enlace", self.sensor_hw_var)
        ttk.Label(
            sensor_card,
            textvariable=self.sensor_status_var,
            style="Muted.TLabel",
            wraplength=220,
        ).grid(
            row=3, column=0, columnspan=2, sticky="w", pady=(12, 0)
        )

    def _add_status_row(
        self,
        parent: ttk.Frame,
        row: int,
        label: str,
        variable: tk.StringVar,
    ) -> None:
        ttk.Label(parent, text=label, style="Muted.TLabel").grid(
            row=row, column=0, sticky="w", pady=(10, 0)
        )
        ttk.Label(parent, textvariable=variable, style="Value.TLabel").grid(
            row=row, column=1, sticky="e", pady=(10, 0), padx=(16, 0)
        )

    def _build_notebook(self, parent: ttk.Frame) -> None:
        notebook_shell = self._make_bounded_panel(parent, background=PALETTE["bg"])
        notebook_shell.grid(row=0, column=1, sticky="new")
        notebook_shell.columnconfigure(0, weight=1)
        notebook_shell.rowconfigure(1, weight=1)

        self.view_bar = tk.Frame(
            notebook_shell,
            bg=PALETTE["bg"],
            bd=0,
            highlightthickness=0,
        )
        self.view_bar.grid(row=0, column=0, sticky="ew", pady=(0, 6))

        self.notebook = ttk.Notebook(notebook_shell, style="Tabless.TNotebook")
        self.notebook.grid(row=1, column=0, sticky="nsew")

        self.access_tab = ttk.Frame(
            self.notebook,
            style="App.TFrame",
            padding=VIEW_TAB_PADDING,
        )
        self.sensor_tab = ttk.Frame(
            self.notebook,
            style="App.TFrame",
            padding=VIEW_TAB_PADDING,
        )
        self.profiles_tab = ttk.Frame(
            self.notebook,
            style="App.TFrame",
            padding=VIEW_TAB_PADDING,
        )
        self.calibration_tab = ttk.Frame(
            self.notebook,
            style="App.TFrame",
            padding=VIEW_TAB_PADDING,
        )
        self.control_tab = ttk.Frame(
            self.notebook,
            style="App.TFrame",
            padding=VIEW_TAB_PADDING,
        )
        self.commands_tab = ttk.Frame(
            self.notebook,
            style="App.TFrame",
            padding=VIEW_TAB_PADDING,
        )

        self.view_tabs: tuple[tuple[str, ttk.Frame], ...] = (
            ("Acceso", self.access_tab),
            ("Sensor", self.sensor_tab),
            ("Perfiles", self.profiles_tab),
            ("Calibraci\u00f3n", self.calibration_tab),
            ("Control", self.control_tab),
            ("Comandos", self.commands_tab),
        )
        self.view_tab_widgets: dict[ttk.Frame, tuple[tk.Frame, tk.Label]] = {}

        for _, tab in self.view_tabs:
            tab.grid_anchor("nw")

        self.notebook.add(self.access_tab, text="Acceso")
        self.notebook.add(self.sensor_tab, text="Sensor")
        self.notebook.add(self.profiles_tab, text="Perfiles")
        self.notebook.add(self.calibration_tab, text="Calibración")
        self.notebook.add(self.control_tab, text="Control")
        self.notebook.add(self.commands_tab, text="Comandos")

        self._build_view_selector()
        self.notebook.bind("<<NotebookTabChanged>>", self._on_notebook_tab_changed)

        self._build_access_tab()
        self._build_sensor_tab()
        self._build_profiles_tab()
        self._build_calibration_tab()
        self._build_control_tab()
        self._build_commands_tab()
        self._sync_view_selector()

    def _build_view_selector(self) -> None:
        for index, (title, tab_frame) in enumerate(self.view_tabs):
            slot = tk.Frame(
                self.view_bar,
                bg=PALETTE["bg"],
                bd=0,
                highlightthickness=0,
            )
            slot.grid(
                row=0,
                column=index,
                sticky="sw",
                padx=(0 if index == 0 else 8, 0),
            )

            label = tk.Label(
                slot,
                text=title,
                bg=PALETTE["surface_alt"],
                fg=PALETTE["primary_dark"],
                bd=1,
                relief="solid",
                padx=18,
                pady=8,
                font=("Segoe UI Semibold", 10),
                cursor="hand2",
            )
            label.pack()
            label.bind(
                "<Button-1>",
                lambda _event, target=tab_frame: self._select_view_tab(target),
            )
            self.view_tab_widgets[tab_frame] = (slot, label)

        self.view_bar.grid_columnconfigure(len(self.view_tabs), weight=1)
        tk.Frame(
            self.view_bar,
            bg=PALETTE["bg"],
            bd=0,
            highlightthickness=0,
        ).grid(row=0, column=len(self.view_tabs), sticky="ew")

    def _select_view_tab(self, tab_frame: ttk.Frame) -> None:
        if self.notebook.tab(tab_frame, "state") == "disabled":
            return
        self.notebook.select(tab_frame)
        self._sync_view_selector()

    def _on_notebook_tab_changed(self, _event: tk.Event) -> None:
        self._sync_view_selector()

    def _sync_view_selector(self) -> None:
        selected_tab = self.notebook.select()

        for tab_frame, (slot, label) in self.view_tab_widgets.items():
            tab_state = self.notebook.tab(tab_frame, "state")
            is_selected = str(tab_frame) == selected_tab

            if is_selected:
                slot.grid_configure(pady=(0, 0))
                label.configure(
                    bg=PALETTE["surface"],
                    fg=PALETTE["primary_dark"],
                    padx=20,
                    pady=10,
                    cursor="hand2",
                )
                continue

            if tab_state == "disabled":
                slot.grid_configure(pady=(10, 0))
                label.configure(
                    bg="#ddd6ce",
                    fg="#8b8379",
                    padx=18,
                    pady=7,
                    cursor="arrow",
                )
                continue

            slot.grid_configure(pady=(8, 0))
            label.configure(
                bg=PALETTE["surface_alt"],
                fg=PALETTE["primary_dark"],
                padx=18,
                pady=7,
                cursor="hand2",
            )

    def _build_access_tab(self) -> None:
        self.access_tab.columnconfigure(0, weight=1)
        self.access_tab.columnconfigure(1, weight=0)

        access_card = ttk.Frame(self.access_tab, style="Card.TFrame", padding=16)
        access_card.grid(row=0, column=0, sticky="new")
        access_card.columnconfigure(0, weight=1)

        normal_card = ttk.Frame(access_card, style="Card.TFrame")
        normal_card.grid(row=0, column=0, sticky="new")
        ttk.Label(normal_card, text="Modo normal", style="SectionTitle.TLabel").grid(
            row=0, column=0, sticky="w", columnspan=2
        )
        ttk.Label(
            normal_card,
            textvariable=self.normal_hint_var,
            style="Muted.TLabel",
            wraplength=360,
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(6, 14))
        self._add_entry(normal_card, 2, "Usuario", self.normal_username_var)
        self._add_entry(normal_card, 4, "Contraseña", self.normal_password_var, show="*")
        self._add_entry(normal_card, 6, "Código del brazo", self.arm_code_var)
        ttk.Button(
            normal_card,
            text="Entrar",
            style="Primary.TButton",
            command=self._on_normal_login,
        ).grid(row=8, column=0, columnspan=2, sticky="ew", pady=(18, 0))
        self._add_access_switch_link(
            normal_card,
            9,
            "Modo administrador",
            lambda: self._show_access_mode("admin"),
        )

        admin_card = ttk.Frame(access_card, style="Card.TFrame")
        admin_card.grid(row=0, column=0, sticky="new")
        ttk.Label(admin_card, text="Modo administrador", style="SectionTitle.TLabel").grid(
            row=0, column=0, sticky="w", columnspan=2
        )
        ttk.Label(
            admin_card,
            text=(
                "Usa el identificador del pendrive maestro para entrar sin "
                "validación del brazo."
            ),
            style="Muted.TLabel",
            wraplength=360,
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(6, 14))
        self._add_entry(admin_card, 2, "USB maestro", self.admin_usb_var)
        ttk.Button(
            admin_card,
            text="Activar modo admin",
            style="Primary.TButton",
            command=self._on_admin_login,
        ).grid(row=4, column=0, columnspan=2, sticky="ew", pady=(18, 0))
        self._add_access_switch_link(
            admin_card,
            5,
            "Modo normal",
            lambda: self._show_access_mode("normal"),
        )

        self.access_views = {
            "normal": normal_card,
            "admin": admin_card,
        }
        self._show_access_mode("normal")

    def _add_access_switch_link(
        self,
        parent: ttk.Frame,
        row: int,
        text: str,
        command,
    ) -> None:
        link = tk.Label(
            parent,
            text=text,
            bg=PALETTE["surface"],
            fg=PALETTE["primary_dark"],
            activeforeground=PALETTE["accent"],
            cursor="hand2",
            font=("Segoe UI", 8, "underline"),
        )
        link.grid(row=row, column=0, columnspan=2, sticky="w", pady=(10, 0))
        link.bind("<Button-1>", lambda _event: command())

    def _show_access_mode(self, mode: str) -> None:
        for access_mode, frame in self.access_views.items():
            if access_mode == mode:
                frame.grid()
                frame.tkraise()
            else:
                frame.grid_remove()

    def _build_sensor_tab(self) -> None:
        self.sensor_tab.columnconfigure(0, weight=1)
        self.sensor_tab.columnconfigure(1, weight=1)
        config_card = ttk.Frame(self.sensor_tab, style="Card.TFrame", padding=16)
        config_card.grid(row=0, column=0, sticky="new", padx=(0, 8))
        config_card.columnconfigure(0, weight=0, minsize=160)
        config_card.columnconfigure(1, weight=1)

        ttk.Label(
            config_card,
            text="Fuente y trama UART",
            style="SectionTitle.TLabel",
        ).grid(row=0, column=0, columnspan=2, sticky="w")
        ttk.Label(
            config_card,
            text=(
                "La app espera una estructura con tres campos consecutivos: "
                "frecuencia, modulo de impedancia y fase. Puedes escoger el "
                "tipo de dato y aplicar escala al modulo y a la fase."
            ),
            style="Muted.TLabel",
            wraplength=390,
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(6, 14))

        self._add_sensor_form_label(config_card, 2, "Fuente de captura")
        self.sensor_mode_combo = ttk.Combobox(
            config_card,
            textvariable=self.sensor_mode_var,
            values=("Simulación", "UART"),
            state="readonly",
            style="Form.TCombobox",
        )
        self.sensor_mode_combo.grid(row=2, column=1, sticky="ew", pady=(8, 0))

        self._add_sensor_form_label(config_card, 3, "Puerto UART")
        self.sensor_port_combo = ttk.Combobox(
            config_card,
            textvariable=self.sensor_port_var,
            values=(),
            style="Form.TCombobox",
        )
        self.sensor_port_combo.grid(row=3, column=1, sticky="ew", pady=(8, 0))

        self._add_sensor_form_label(config_card, 4, "Baudios")
        ttk.Entry(
            config_card,
            textvariable=self.sensor_baudrate_var,
            style="Form.TEntry",
        ).grid(row=4, column=1, sticky="ew", pady=(8, 0))

        self._add_sensor_form_label(config_card, 5, "Tipo de dato")
        ttk.Combobox(
            config_card,
            textvariable=self.sensor_data_type_var,
            values=("float32", "uint32"),
            state="readonly",
            style="Form.TCombobox",
        ).grid(row=5, column=1, sticky="ew", pady=(8, 0))

        self._add_sensor_form_label(config_card, 6, "Orden de bytes")
        ttk.Combobox(
            config_card,
            textvariable=self.sensor_byte_order_var,
            values=("little", "big"),
            state="readonly",
            style="Form.TCombobox",
        ).grid(row=6, column=1, sticky="ew", pady=(8, 0))

        self._add_sensor_form_label(config_card, 7, "Media últimas muestras")
        ttk.Entry(
            config_card,
            textvariable=self.sensor_average_var,
            style="Form.TEntry",
        ).grid(row=7, column=1, sticky="ew", pady=(8, 0))

        self._add_sensor_form_label(config_card, 8, "Timeout de lectura (ms)")
        ttk.Entry(
            config_card,
            textvariable=self.sensor_timeout_var,
            style="Form.TEntry",
        ).grid(row=8, column=1, sticky="ew", pady=(8, 0))

        self._add_sensor_form_label(config_card, 9, "Escala modulo Z")
        ttk.Entry(
            config_card,
            textvariable=self.sensor_magnitude_scale_var,
            style="Form.TEntry",
        ).grid(row=9, column=1, sticky="ew", pady=(8, 0))

        self._add_sensor_form_label(config_card, 10, "Escala fase")
        ttk.Entry(
            config_card,
            textvariable=self.sensor_phase_scale_var,
            style="Form.TEntry",
        ).grid(row=10, column=1, sticky="ew", pady=(8, 0))

        actions = ttk.Frame(config_card, style="Card.TFrame")
        actions.grid(row=11, column=0, columnspan=2, sticky="ew", pady=(14, 0))
        actions.columnconfigure(0, weight=1)
        actions.columnconfigure(1, weight=1)
        ttk.Button(
            actions,
            text="Detectar puertos",
            style="Secondary.TButton",
            command=self._on_detect_sensor_ports,
        ).grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ttk.Button(
            actions,
            text="Aplicar configuración",
            style="Primary.TButton",
            command=self._on_apply_sensor_config,
        ).grid(row=0, column=1, sticky="ew", padx=(6, 0))

        state_card = ttk.Frame(self.sensor_tab, style="Card.TFrame", padding=16)
        state_card.grid(row=0, column=1, sticky="new", padx=(8, 0))
        state_card.columnconfigure(0, weight=1)

        ttk.Label(
            state_card,
            text="Estado del sensor",
            style="SectionTitle.TLabel",
        ).grid(row=0, column=0, sticky="w")
        ttk.Label(
            state_card,
            text=(
                "Cada lectura desde los botones de captura consume lo que haya en el "
                "puerto serie, separa paquetes completos y hace la media de las últimas "
                "N muestras válidas."
            ),
            style="Muted.TLabel",
            wraplength=390,
        ).grid(row=1, column=0, sticky="w", pady=(6, 14))

        info_card = ttk.Frame(state_card, style="Card.TFrame")
        info_card.grid(row=2, column=0, sticky="ew")
        info_card.columnconfigure(0, weight=0, minsize=140)
        info_card.columnconfigure(1, weight=1)
        self._add_status_row(info_card, 0, "Fuente", self.sensor_source_var)
        self._add_status_row(info_card, 1, "Enlace", self.sensor_hw_var)

        ttk.Label(
            state_card,
            text="Puertos detectados",
            style="Muted.TLabel",
        ).grid(row=3, column=0, sticky="w", pady=(18, 4))
        ttk.Label(
            state_card,
            textvariable=self.sensor_ports_var,
            style="Value.TLabel",
            wraplength=390,
        ).grid(row=4, column=0, sticky="w")

        ttk.Label(
            state_card,
            text="Estado actual",
            style="Muted.TLabel",
        ).grid(row=5, column=0, sticky="w", pady=(18, 4))
        ttk.Label(
            state_card,
            textvariable=self.sensor_status_var,
            style="Status.TLabel",
            wraplength=390,
        ).grid(row=6, column=0, sticky="w")

        ttk.Label(
            state_card,
            text=(
                "Trama esperada: struct { tipo frecuencia; tipo modulo_z; "
                "tipo fase; }. La fase se interpreta en grados tras aplicar "
                "su escala."
            ),
            style="Muted.TLabel",
            wraplength=390,
        ).grid(row=7, column=0, sticky="w", pady=(18, 0))

    def _build_profiles_tab(self) -> None:
        self.profiles_tab.columnconfigure(0, weight=1)
        self.profiles_tab.columnconfigure(1, weight=1)

        list_card = ttk.Frame(self.profiles_tab, style="Card.TFrame", padding=16)
        list_card.grid(row=0, column=0, sticky="new", padx=(0, 8))
        list_card.rowconfigure(2, weight=1)
        list_card.columnconfigure(0, weight=1)
        ttk.Label(list_card, text="Perfiles disponibles", style="SectionTitle.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(
            list_card,
            text="Selecciona un usuario guardado para cargarlo en la sesión activa.",
            style="Muted.TLabel",
            wraplength=360,
        ).grid(row=1, column=0, sticky="w", pady=(8, 14))

        list_frame = ttk.Frame(list_card, style="Card.TFrame")
        list_frame.grid(row=2, column=0, sticky="nsew")
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        self.profile_listbox = tk.Listbox(
            list_frame,
            activestyle="none",
            bg="#ffffff",
            fg=PALETTE["text"],
            height=8,
            highlightthickness=0,
            selectbackground="#d6ebe7",
            selectforeground=PALETTE["text"],
            relief="flat",
            font=("Segoe UI", 10),
        )
        self.profile_listbox.grid(row=0, column=0, sticky="nsew")

        actions = ttk.Frame(list_card, style="Card.TFrame")
        actions.grid(row=3, column=0, sticky="ew", pady=(14, 0))
        actions.columnconfigure(0, weight=1)
        actions.columnconfigure(1, weight=1)
        ttk.Button(
            actions,
            text="Actualizar lista",
            style="Secondary.TButton",
            command=self.refresh_view,
        ).grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ttk.Button(
            actions,
            text="Cargar perfil",
            style="Primary.TButton",
            command=self._on_load_profile,
        ).grid(row=0, column=1, sticky="ew", padx=(6, 0))

        register_card = ttk.Frame(self.profiles_tab, style="Card.TFrame", padding=16)
        register_card.grid(row=0, column=1, sticky="new", padx=(8, 0))
        ttk.Label(register_card, text="Registrar usuario", style="SectionTitle.TLabel").grid(
            row=0, column=0, sticky="w", columnspan=2
        )
        ttk.Label(
            register_card,
            text=(
                "La medición de registro puede capturarse desde el sensor simulado "
                "o introducirse manualmente."
            ),
            style="Muted.TLabel",
            wraplength=360,
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(6, 14))
        self._add_entry(register_card, 2, "Usuario", self.register_username_var)
        self._add_entry(
            register_card, 4, "Contraseña", self.register_password_var, show="*"
        )
        self._add_entry(
            register_card,
            6,
            "Repetir contraseña",
            self.register_confirm_var,
            show="*",
        )
        self._build_measurement_editor(
            register_card,
            start_row=8,
            variables=self.registration_measurement_vars,
            title="Bioimpedancia de registro",
        )
        ttk.Button(
            register_card,
            text="Capturar del sensor",
            style="Secondary.TButton",
            command=self._on_capture_registration,
        ).grid(row=13, column=0, sticky="ew", pady=(16, 0), padx=(0, 6))
        ttk.Button(
            register_card,
            text="Crear usuario",
            style="Primary.TButton",
            command=self._on_register_user,
        ).grid(row=13, column=1, sticky="ew", pady=(16, 0), padx=(6, 0))

    def _build_calibration_tab(self) -> None:
        self.calibration_tab.columnconfigure(0, weight=1)

        card = ttk.Frame(self.calibration_tab, style="Card.TFrame", padding=18)
        card.grid(row=0, column=0, sticky="new")
        ttk.Label(card, text="Calibración del perfil activo", style="SectionTitle.TLabel").grid(
            row=0, column=0, sticky="w", columnspan=2
        )
        ttk.Label(
            card,
            textvariable=self.calibration_profile_var,
            style="Value.TLabel",
        ).grid(row=1, column=0, sticky="w", columnspan=2, pady=(8, 4))
        ttk.Label(
            card,
            text="Captura una nueva medición y guárdala como referencia de calibración.",
            style="Muted.TLabel",
            wraplength=520,
        ).grid(row=2, column=0, sticky="w", columnspan=2, pady=(0, 18))
        self._build_measurement_editor(
            card,
            start_row=3,
            variables=self.calibration_measurement_vars,
            title="Medición de calibración",
        )
        ttk.Button(
            card,
            text="Capturar del sensor",
            style="Secondary.TButton",
            command=self._on_capture_calibration,
        ).grid(row=8, column=0, sticky="ew", pady=(18, 0), padx=(0, 6))
        ttk.Button(
            card,
            text="Guardar calibracion",
            style="Primary.TButton",
            command=self._on_save_calibration,
        ).grid(row=8, column=1, sticky="ew", pady=(18, 0), padx=(6, 0))

    def _build_control_tab(self) -> None:
        self.control_tab.columnconfigure(0, weight=1)
        self.control_tab.columnconfigure(1, weight=1)

        quick_card = ttk.Frame(self.control_tab, style="Card.TFrame", padding=18)
        quick_card.grid(row=0, column=0, sticky="new", padx=(0, 8))
        quick_card.columnconfigure(0, weight=1)
        quick_card.columnconfigure(1, weight=1)
        quick_card.columnconfigure(2, weight=1)

        ttk.Label(quick_card, text="Control rapido", style="SectionTitle.TLabel").grid(
            row=0, column=0, columnspan=3, sticky="w"
        )
        ttk.Label(
            quick_card,
            textvariable=self.control_profile_var,
            style="Value.TLabel",
        ).grid(row=1, column=0, columnspan=3, sticky="w", pady=(8, 4))
        ttk.Label(
            quick_card,
            text=(
                "Mantiene las acciones manuales de la simulacion para pruebas puntuales "
                "de movimiento y pinza."
            ),
            style="Muted.TLabel",
            wraplength=420,
        ).grid(row=2, column=0, columnspan=3, sticky="w", pady=(0, 20))

        buttons = [
            ("Arriba", "up", 3, 1),
            ("Izquierda", "left", 4, 0),
            ("Derecha", "right", 4, 2),
            ("Abajo", "down", 5, 1),
            ("Abrir pinza", "open_grip", 6, 0),
            ("Cerrar pinza", "close_grip", 6, 2),
        ]
        for text, action_key, row, column in buttons:
            ttk.Button(
                quick_card,
                text=text,
                style="Primary.TButton" if action_key in {"up", "down"} else "Secondary.TButton",
                command=lambda key=action_key: self._on_arm_action(key),
            ).grid(row=row, column=column, sticky="ew", padx=10, pady=8)

        ttk.Label(quick_card, text="Ultima accion", style="Muted.TLabel").grid(
            row=7, column=0, columnspan=3, sticky="w", pady=(18, 4)
        )
        ttk.Label(
            quick_card,
            textvariable=self.control_status_var,
            style="Value.TLabel",
            wraplength=420,
        ).grid(row=8, column=0, columnspan=3, sticky="w")

        realtime_card = ttk.Frame(self.control_tab, style="Card.TFrame", padding=18)
        realtime_card.grid(row=0, column=1, sticky="new", padx=(8, 0))
        realtime_card.columnconfigure(0, weight=1)
        realtime_card.columnconfigure(1, weight=0)

        ttk.Label(
            realtime_card,
            text="Movimiento en tiempo real",
            style="SectionTitle.TLabel",
        ).grid(row=0, column=0, columnspan=2, sticky="w")
        ttk.Label(
            realtime_card,
            text=(
                "Simula la mano del operador con estos controles. Si activas el "
                "seguimiento, el brazo replica cada cambio al instante."
            ),
            style="Muted.TLabel",
            wraplength=450,
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(6, 12))

        controls_row = ttk.Frame(realtime_card, style="Card.TFrame")
        controls_row.grid(row=2, column=0, columnspan=2, sticky="ew")
        controls_row.columnconfigure(0, weight=1)
        controls_row.columnconfigure(1, weight=0)
        ttk.Checkbutton(
            controls_row,
            text="Seguimiento activo",
            variable=self.realtime_enabled_var,
            command=self._on_toggle_realtime_tracking,
        ).grid(row=0, column=0, sticky="w")
        ttk.Button(
            controls_row,
            text="Centrar pose",
            style="Secondary.TButton",
            command=self._on_reset_realtime_tracking,
        ).grid(row=0, column=1, sticky="e")

        sliders_frame = ttk.Frame(realtime_card, style="Card.TFrame")
        sliders_frame.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(14, 0))
        sliders_frame.columnconfigure(1, weight=1)

        for index, (key, label, min_value, max_value, value_kind) in enumerate(
            TRACKING_SLIDERS
        ):
            self._create_tracking_slider(
                sliders_frame,
                row=index,
                key=key,
                label=label,
                min_value=min_value,
                max_value=max_value,
                value_kind=value_kind,
            )

        ttk.Label(
            realtime_card,
            text="Estado del seguimiento",
            style="Muted.TLabel",
        ).grid(row=4, column=0, columnspan=2, sticky="w", pady=(18, 4))
        ttk.Label(
            realtime_card,
            textvariable=self.realtime_status_var,
            style="Status.TLabel",
            wraplength=450,
        ).grid(row=5, column=0, columnspan=2, sticky="w")

        preview_frame = ttk.Frame(realtime_card, style="Card.TFrame")
        preview_frame.grid(row=6, column=0, columnspan=2, sticky="ew", pady=(14, 0))
        preview_frame.columnconfigure(0, weight=1)

        ttk.Label(preview_frame, text="Vista de la mano y el brazo", style="Muted.TLabel").grid(
            row=0, column=0, sticky="w", pady=(0, 8)
        )
        self.tracking_canvas = tk.Canvas(
            preview_frame,
            width=TRACKING_CANVAS_WIDTH,
            height=TRACKING_CANVAS_HEIGHT,
            bg="#ffffff",
            relief="flat",
            highlightthickness=1,
            highlightbackground=PALETTE["surface_alt"],
        )
        self.tracking_canvas.grid(row=1, column=0, sticky="nsew")
        self.tracking_canvas.bind("<Motion>", self._on_tracking_canvas_motion)
        self.tracking_canvas.bind("<Leave>", self._on_tracking_canvas_leave)

        summary_frame = ttk.Frame(realtime_card, style="Card.TFrame")
        summary_frame.grid(row=7, column=0, columnspan=2, sticky="ew", pady=(16, 0))
        summary_frame.columnconfigure(0, weight=1)
        summary_frame.columnconfigure(1, weight=1)
        ttk.Label(summary_frame, text="Mano simulada", style="Muted.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(summary_frame, text="Brazo replicado", style="Muted.TLabel").grid(
            row=0, column=1, sticky="w", padx=(16, 0)
        )
        ttk.Label(
            summary_frame,
            textvariable=self.hand_pose_summary_var,
            style="Value.TLabel",
            wraplength=230,
        ).grid(row=1, column=0, sticky="w", pady=(6, 0))
        ttk.Label(
            summary_frame,
            textvariable=self.arm_pose_summary_var,
            style="Value.TLabel",
            wraplength=230,
        ).grid(row=1, column=1, sticky="w", padx=(16, 0), pady=(6, 0))

    def _build_commands_tab(self) -> None:
        self.commands_tab.columnconfigure(0, weight=1)
        self.commands_tab.columnconfigure(1, weight=1)

        list_card = ttk.Frame(self.commands_tab, style="Card.TFrame", padding=16)
        list_card.grid(row=0, column=0, sticky="new", padx=(0, 8))
        list_card.rowconfigure(2, weight=1)
        list_card.columnconfigure(0, weight=1)
        ttk.Label(list_card, text="Secuencia en edición", style="SectionTitle.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(list_card, textvariable=self.command_profile_var, style="Value.TLabel").grid(
            row=1, column=0, sticky="w", pady=(8, 14)
        )

        self.commands_tree = ttk.Treeview(
            list_card,
            columns=("name", "duration"),
            show="headings",
            height=10,
        )
        self.commands_tree.grid(row=2, column=0, sticky="nsew")
        self.commands_tree.heading("name", text="Comando")
        self.commands_tree.heading("duration", text="Duración (ms)")
        self.commands_tree.column("name", width=220, anchor="w")
        self.commands_tree.column("duration", width=120, anchor="center")

        list_actions = ttk.Frame(list_card, style="Card.TFrame")
        list_actions.grid(row=3, column=0, sticky="ew", pady=(14, 0))
        list_actions.columnconfigure(0, weight=1)
        list_actions.columnconfigure(1, weight=1)
        list_actions.columnconfigure(2, weight=1)
        ttk.Button(
            list_actions,
            text="Quitar",
            style="Secondary.TButton",
            command=self._on_remove_command,
        ).grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ttk.Button(
            list_actions,
            text="Limpiar",
            style="Secondary.TButton",
            command=self._on_clear_commands,
        ).grid(row=0, column=1, sticky="ew", padx=6)
        ttk.Button(
            list_actions,
            text="Guardar secuencia",
            style="Primary.TButton",
            command=self._on_save_commands,
        ).grid(row=0, column=2, sticky="ew", padx=(6, 0))

        edit_card = ttk.Frame(self.commands_tab, style="Card.TFrame", padding=16)
        edit_card.grid(row=0, column=1, sticky="new", padx=(8, 0))
        ttk.Label(edit_card, text="Agregar comando", style="SectionTitle.TLabel").grid(
            row=0, column=0, columnspan=2, sticky="w"
        )
        ttk.Label(
            edit_card,
            text="Puedes construir una nueva secuencia o recuperar la última guardada del perfil activo.",
            style="Muted.TLabel",
            wraplength=360,
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(6, 14))
        self._add_entry(edit_card, 2, "Nombre", self.command_name_var)
        self._add_entry(edit_card, 4, "Duración (ms)", self.command_duration_var)
        ttk.Button(
            edit_card,
            text="Añadir comando",
            style="Primary.TButton",
            command=self._on_add_command,
        ).grid(row=6, column=0, columnspan=2, sticky="ew", pady=(18, 0))
        ttk.Button(
            edit_card,
            text="Cargar secuencia guardada",
            style="Secondary.TButton",
            command=self._on_load_saved_sequence,
        ).grid(row=7, column=0, columnspan=2, sticky="ew", pady=(12, 0))

    def _build_log_panel(self, parent: ttk.Frame) -> None:
        log_card = self._make_bounded_panel(parent, width=ACTIVITY_PANEL_WIDTH)
        log_card.grid(row=0, column=2, sticky="ne", padx=(14, 0))
        log_card.rowconfigure(1, weight=1)
        log_card.columnconfigure(0, weight=1)
        ttk.Label(log_card, text="Actividad", style="SectionTitle.TLabel").grid(
            row=0, column=0, sticky="w", padx=14, pady=(14, 0)
        )

        log_body = tk.Frame(
            log_card,
            bg="#ffffff",
            bd=0,
            highlightthickness=1,
            highlightbackground=PALETTE["surface_alt"],
            highlightcolor=PALETTE["surface_alt"],
        )
        log_body.grid(row=1, column=0, sticky="nsew", padx=14, pady=(10, 14))
        log_body.rowconfigure(0, weight=1)
        log_body.columnconfigure(0, weight=1)

        log_scrollbar = ttk.Scrollbar(log_body, orient="vertical")
        self.log_text = tk.Text(
            log_body,
            wrap="word",
            bg="#ffffff",
            fg=PALETTE["text"],
            relief="flat",
            highlightthickness=0,
            padx=8,
            pady=8,
            font=("Consolas", 9),
            yscrollcommand=log_scrollbar.set,
        )
        self.log_text.grid(row=0, column=0, sticky="nsew")
        log_scrollbar.configure(command=self.log_text.yview)
        log_scrollbar.grid(row=0, column=1, sticky="ns")
        self.log_text.configure(state="disabled")

    def _make_bounded_panel(
        self,
        parent: tk.Misc,
        *,
        width: int | None = None,
        background: str | None = None,
    ) -> tk.Frame:
        panel = tk.Frame(
            parent,
            bg=background or PALETTE["surface"],
            bd=0,
            highlightthickness=1,
            highlightbackground=PALETTE["surface_alt"],
            highlightcolor=PALETTE["surface_alt"],
            height=VIEW_PANEL_MAX_HEIGHT,
        )
        if width is not None:
            panel.configure(width=width)
        panel.grid_propagate(False)
        self._height_limited_panels.append(panel)
        return panel

    def _resize_height_limited_panels(self, event: tk.Event | None = None) -> None:
        if event is not None and event.widget is not self.root:
            return
        if not self._height_limited_panels:
            return

        root_height = self.root.winfo_height()
        root_top = self.root.winfo_rooty()
        available_heights = []
        for panel in self._height_limited_panels:
            if not panel.winfo_exists():
                continue
            panel_top = max(panel.winfo_rooty() - root_top, 0)
            available_heights.append(root_height - panel_top - VIEW_PANEL_BOTTOM_MARGIN)

        if not available_heights:
            return

        target_height = min(VIEW_PANEL_MAX_HEIGHT, min(available_heights))
        target_height = max(VIEW_PANEL_MIN_HEIGHT, target_height)
        for panel in self._height_limited_panels:
            panel.configure(height=target_height)

    def _add_entry(
        self,
        parent: ttk.Frame,
        row: int,
        label: str,
        variable: tk.StringVar,
        show: str | None = None,
    ) -> None:
        ttk.Label(parent, text=label, style="Body.TLabel").grid(
            row=row, column=0, columnspan=2, sticky="w", pady=(8, 0)
        )
        entry = ttk.Entry(parent, textvariable=variable, show=show, style="Form.TEntry")
        entry.grid(
            row=row + 1,
            column=0,
            columnspan=2,
            sticky="ew",
            pady=(4, 0),
        )
        parent.columnconfigure(0, weight=1)
        parent.columnconfigure(1, weight=1)

    def _add_sensor_form_label(
        self,
        parent: ttk.Frame,
        row: int,
        label: str,
    ) -> None:
        ttk.Label(parent, text=label, style="Body.TLabel").grid(
            row=row,
            column=0,
            sticky="w",
            pady=(6, 0),
            padx=(0, 12),
        )

    def _read_sensor_config_from_form(self) -> UartSensorConfig | None:
        try:
            baudrate = int(self.sensor_baudrate_var.get().strip())
            averaging_window = int(self.sensor_average_var.get().strip())
            timeout_ms = int(self.sensor_timeout_var.get().strip())
            magnitude_scale = float(self.sensor_magnitude_scale_var.get().strip())
            phase_scale = float(self.sensor_phase_scale_var.get().strip())
        except ValueError:
            self._show_error(
                "Configuración del sensor",
                "Revisa los campos numéricos de UART antes de aplicar la configuración.",
            )
            return None

        return UartSensorConfig(
            source_mode=(
                "uart" if self.sensor_mode_var.get().strip().lower() == "uart" else "mock"
            ),
            port=self.sensor_port_var.get().strip(),
            baudrate=baudrate,
            data_type=self.sensor_data_type_var.get().strip(),
            byte_order=self.sensor_byte_order_var.get().strip(),
            averaging_window=averaging_window,
            timeout_ms=timeout_ms,
            magnitude_scale=magnitude_scale,
            phase_scale=phase_scale,
        )

    def _refresh_detected_ports(self, log_detection: bool = True) -> None:
        ports = self.controller.list_available_serial_ports()
        if hasattr(self, "sensor_port_combo"):
            self.sensor_port_combo.configure(values=ports)

        if ports:
            if not self.sensor_port_var.get().strip():
                self.sensor_port_var.set(ports[0])
            summary = ", ".join(ports)
            self.sensor_ports_var.set(summary)
            if log_detection:
                self.log(f"Puertos serie detectados: {summary}")
            return

        self.sensor_ports_var.set(
            "No se detectaron puertos automáticamente. Puedes escribir uno manualmente."
        )
        if log_detection:
            self.log(
                "No se detectaron puertos automáticamente. Puedes configurar el puerto UART a mano."
            )

    def _create_tracking_slider(
        self,
        parent: ttk.Frame,
        row: int,
        key: str,
        label: str,
        min_value: float,
        max_value: float,
        value_kind: str,
    ) -> None:
        ttk.Label(parent, text=label, style="Body.TLabel").grid(
            row=row,
            column=0,
            sticky="w",
            pady=(7, 0),
        )
        ttk.Scale(
            parent,
            orient="horizontal",
            from_=min_value,
            to=max_value,
            variable=self.realtime_pose_vars[key],
            command=self._on_realtime_pose_changed,
        ).grid(row=row, column=1, sticky="ew", padx=(10, 10), pady=(7, 0))
        ttk.Label(
            parent,
            textvariable=self.realtime_value_vars[key],
            style="Value.TLabel",
            width=11,
        ).grid(row=row, column=2, sticky="e", pady=(7, 0))
        self.realtime_value_vars[key].set(
            self._format_tracking_value(self.realtime_pose_vars[key].get(), value_kind)
        )

    def _format_tracking_value(self, value: float, value_kind: str) -> str:
        if value_kind == "degrees":
            return f"{value:+.0f} deg"
        if value_kind == "signed_percent":
            return f"{value:+.0f}%"

        return f"{value:.0f}%"

    def _clamp_tracking_value(self, key: str, value: float) -> float:
        for slider_key, _, min_value, max_value, _ in TRACKING_SLIDERS:
            if slider_key == key:
                return max(min_value, min(max_value, value))

        return value

    def _get_realtime_pose_from_vars(self) -> HandPose:
        return HandPose(
            height_pct=self.realtime_pose_vars["height_pct"].get(),
            reach_pct=self.realtime_pose_vars["reach_pct"].get(),
            lateral_pct=self.realtime_pose_vars["lateral_pct"].get(),
            wrist_deg=self.realtime_pose_vars["wrist_deg"].get(),
            grip_pct=self.realtime_pose_vars["grip_pct"].get(),
        )

    def _build_measurement_editor(
        self,
        parent: ttk.Frame,
        start_row: int,
        variables: dict[str, tk.StringVar],
        title: str,
    ) -> None:
        parent.columnconfigure(0, weight=0, minsize=180)
        parent.columnconfigure(1, weight=1)
        ttk.Label(parent, text=title, style="SectionTitle.TLabel").grid(
            row=start_row, column=0, sticky="w", columnspan=2, pady=(10, 6)
        )
        fields = [
            ("Resistencia [ohm]", "resistance_ohm"),
            ("Reactancia [ohm]", "reactance_ohm"),
            ("Fase [grados]", "phase_deg"),
            ("Índice de calidad", "quality_index"),
        ]
        current_row = start_row + 1
        for label, key in fields:
            ttk.Label(parent, text=label, style="Body.TLabel").grid(
                row=current_row, column=0, sticky="w", pady=(6, 0)
            )
            ttk.Entry(parent, textvariable=variables[key], style="Form.TEntry").grid(
                row=current_row, column=1, sticky="ew", pady=(6, 0), padx=(10, 0)
            )
            current_row += 1

    def refresh_view(self) -> None:
        ctx = self.controller.get_context()
        sensor = self.controller.get_sensor_snapshot()

        self.session_access_var.set("Autenticado" if ctx.is_authenticated else "Bloqueado")
        if ctx.auth_mode.value == "admin":
            self.session_mode_var.set("Administrador")
        elif ctx.auth_mode.value == "normal":
            self.session_mode_var.set("Normal")
        else:
            self.session_mode_var.set("Sin sesión")
        self.session_user_var.set(ctx.current_username or "Sin usuario")
        self.session_profile_var.set(
            ctx.active_profile.username if ctx.profile_loaded else "Sin perfil cargado"
        )

        self.sensor_status_var.set(sensor.status_text)
        self.sensor_source_var.set(
            "Simulación" if sensor.source_mode == "mock" else "UART"
        )
        if sensor.source_mode == "mock":
            self.sensor_hw_var.set("Simulado")
        else:
            self.sensor_hw_var.set("Conectado" if sensor.hardware_ready else "Sin enlace")

        if self.controller.has_registered_users():
            self.normal_hint_var.set(
                "Usa usuario, contraseña y el código mostrado por el brazo."
            )
        else:
            self.normal_hint_var.set(
                "Aún no hay usuarios registrados. Puedes entrar con la contraseña general y luego crear el primero."
            )

        if not self.register_username_var.get() and ctx.current_username:
            self.register_username_var.set(ctx.current_username)

        profile_name = ctx.current_username or "Sin perfil activo"
        self.calibration_profile_var.set(f"Perfil activo: {profile_name}")
        self.control_profile_var.set(f"Perfil activo: {profile_name}")
        self.command_profile_var.set(f"Perfil activo: {profile_name}")

        self._refresh_profile_list()
        self._refresh_commands_tree()
        self._refresh_realtime_tracking()
        self._update_tab_states()

    def _refresh_profile_list(self) -> None:
        previous_selection = self._get_selected_profile_name()
        profiles = self.controller.list_profiles()

        self.profile_listbox.delete(0, tk.END)
        for profile in profiles:
            self.profile_listbox.insert(tk.END, profile.username)

        if previous_selection:
            for index, profile in enumerate(profiles):
                if profile.username == previous_selection:
                    self.profile_listbox.selection_set(index)
                    self.profile_listbox.activate(index)
                    break

    def _refresh_commands_tree(self) -> None:
        for item in self.commands_tree.get_children():
            self.commands_tree.delete(item)

        for index, command in enumerate(
            self.controller.get_context().pending_commands.commands
        ):
            self.commands_tree.insert(
                "",
                "end",
                iid=str(index),
                values=(command.name, command.duration_ms),
            )

    def _refresh_realtime_tracking(self) -> None:
        tracking_state = self.controller.get_realtime_tracking_state()

        self._syncing_tracking_ui = True
        self.realtime_enabled_var.set(tracking_state.tracking_enabled)
        self.realtime_pose_vars["height_pct"].set(tracking_state.hand_pose.height_pct)
        self.realtime_pose_vars["reach_pct"].set(tracking_state.hand_pose.reach_pct)
        self.realtime_pose_vars["lateral_pct"].set(tracking_state.hand_pose.lateral_pct)
        self.realtime_pose_vars["wrist_deg"].set(tracking_state.hand_pose.wrist_deg)
        self.realtime_pose_vars["grip_pct"].set(tracking_state.hand_pose.grip_pct)
        self._syncing_tracking_ui = False

        for key, _, _, _, value_kind in TRACKING_SLIDERS:
            self.realtime_value_vars[key].set(
                self._format_tracking_value(self.realtime_pose_vars[key].get(), value_kind)
            )

        self.realtime_status_var.set(tracking_state.status_text)
        self.hand_pose_summary_var.set(tracking_state.hand_pose.summary())
        self.arm_pose_summary_var.set(tracking_state.arm_pose.summary())
        self._render_tracking_preview(
            hand_pose=tracking_state.hand_pose,
            arm_pose=tracking_state.arm_pose,
            tracking_enabled=tracking_state.tracking_enabled,
        )

    def _render_tracking_preview(
        self,
        hand_pose: HandPose,
        arm_pose: HandPose,
        tracking_enabled: bool,
    ) -> None:
        if not hasattr(self, "tracking_canvas"):
            return

        canvas = self.tracking_canvas
        canvas.delete("all")

        width = TRACKING_CANVAS_WIDTH
        height = TRACKING_CANVAS_HEIGHT
        left_center = width * 0.25
        right_center = width * 0.75
        divider_x = width * 0.5
        base_y = height - 32

        canvas.create_rectangle(0, 0, width, height, outline="", fill="#ffffff")
        canvas.create_text(
            left_center,
            16,
            text="Mano del operador",
            fill=PALETTE["primary_dark"],
            font=("Segoe UI Semibold", 10),
        )
        canvas.create_text(
            right_center,
            16,
            text="Brazo robotico",
            fill=PALETTE["primary_dark"],
            font=("Segoe UI Semibold", 10),
        )
        canvas.create_line(
            divider_x,
            28,
            divider_x,
            height - 16,
            fill=PALETTE["surface_alt"],
            dash=(4, 4),
        )

        self._draw_pose_preview(
            canvas=canvas,
            center_x=left_center,
            base_y=base_y,
            pose=hand_pose,
            color=PALETTE["accent"],
            label="MANO",
        )
        self._draw_pose_preview(
            canvas=canvas,
            center_x=right_center,
            base_y=base_y,
            pose=arm_pose,
            color=PALETTE["primary"],
            label="BRAZO",
        )

        status_color = PALETTE["success"] if tracking_enabled else PALETTE["muted"]
        canvas.create_text(
            divider_x,
            height - 8,
            text=(
                "Seguimiento activo: el brazo copia la mano en tiempo real."
                if tracking_enabled
                else "Seguimiento en pausa: la mano cambia, pero el brazo mantiene su ultima pose."
            ),
            fill=status_color,
            font=("Segoe UI", 9),
        )

    def _draw_pose_preview(
        self,
        canvas: tk.Canvas,
        center_x: float,
        base_y: float,
        pose: HandPose,
        color: str,
        label: str,
    ) -> None:
        lateral_offset = pose.lateral_pct * 0.42
        shoulder_x = center_x
        shoulder_y = base_y
        wrist_x = center_x + lateral_offset
        wrist_y = base_y - (35 + pose.height_pct * 0.8)
        palm_radius = 10 + pose.reach_pct * 0.06

        canvas.create_line(
            shoulder_x,
            shoulder_y,
            wrist_x,
            wrist_y,
            width=5,
            fill=color,
            capstyle=tk.ROUND,
        )
        canvas.create_oval(
            wrist_x - palm_radius,
            wrist_y - palm_radius,
            wrist_x + palm_radius,
            wrist_y + palm_radius,
            fill="",
            outline=color,
            width=3,
        )

        grip_opening = 6 + pose.grip_pct * 0.18
        finger_length = 18 + pose.reach_pct * 0.12
        angle_rad = math.radians(pose.wrist_deg)
        for direction in (-1, 1):
            finger_angle = angle_rad + direction * 0.55
            start_x = wrist_x + math.cos(angle_rad + direction * math.pi / 2) * grip_opening
            start_y = wrist_y + math.sin(angle_rad + direction * math.pi / 2) * grip_opening
            end_x = start_x + math.cos(finger_angle) * finger_length
            end_y = start_y + math.sin(finger_angle) * finger_length
            canvas.create_line(
                start_x,
                start_y,
                end_x,
                end_y,
                width=3,
                fill=color,
                capstyle=tk.ROUND,
            )

        canvas.create_text(
            center_x,
            42,
            text=label,
            fill=color,
            font=("Consolas", 10, "bold"),
        )
        canvas.create_text(
            center_x,
            60,
            text=f"H {pose.height_pct:.0f}% | A {pose.reach_pct:.0f}% | P {pose.grip_pct:.0f}%",
            fill=PALETTE["muted"],
            font=("Segoe UI", 9),
        )

    def _update_tab_states(self) -> None:
        ctx = self.controller.get_context()
        self.notebook.tab(self.access_tab, state="normal")
        self.notebook.tab(self.sensor_tab, state="normal")
        self.notebook.tab(
            self.profiles_tab, state="normal" if ctx.is_authenticated else "disabled"
        )

        profile_state = "normal" if ctx.is_authenticated and ctx.profile_loaded else "disabled"
        self.notebook.tab(self.calibration_tab, state=profile_state)
        self.notebook.tab(self.control_tab, state=profile_state)
        self.notebook.tab(self.commands_tab, state=profile_state)

        current_tab = self.notebook.select()
        if self.notebook.tab(current_tab, "state") == "disabled":
            self.notebook.select(self.access_tab)
        self._sync_view_selector()

    def _read_measurement_vars(
        self, variables: dict[str, tk.StringVar]
    ) -> BiometricData | None:
        try:
            return BiometricData(
                resistance_ohm=float(variables["resistance_ohm"].get()),
                reactance_ohm=float(variables["reactance_ohm"].get()),
                phase_deg=float(variables["phase_deg"].get()),
                quality_index=float(variables["quality_index"].get()),
            )
        except ValueError:
            self._show_error("Revisión de datos", "Introduce valores numéricos válidos.")
            return None

    def _write_measurement_vars(
        self, variables: dict[str, tk.StringVar], measurement: BiometricData
    ) -> None:
        variables["resistance_ohm"].set(f"{measurement.resistance_ohm:.2f}")
        variables["reactance_ohm"].set(f"{measurement.reactance_ohm:.2f}")
        variables["phase_deg"].set(f"{measurement.phase_deg:.2f}")
        variables["quality_index"].set(f"{measurement.quality_index:.2f}")

    def _get_selected_profile_name(self) -> str:
        selection = self.profile_listbox.curselection()
        if not selection:
            return ""
        return str(self.profile_listbox.get(selection[0]))

    def _on_normal_login(self) -> None:
        success, message = self.controller.login_normal(
            self.normal_username_var.get(),
            self.normal_password_var.get(),
            self.arm_code_var.get(),
        )
        self._handle_result(success, message)

    def _on_admin_login(self) -> None:
        success, message = self.controller.login_admin(self.admin_usb_var.get())
        self._handle_result(success, message)

    def _on_detect_sensor_ports(self) -> None:
        self._refresh_detected_ports(log_detection=True)

    def _on_apply_sensor_config(self) -> None:
        config = self._read_sensor_config_from_form()
        if config is None:
            return

        success, message = self.controller.configure_sensor(config)
        if not success:
            self._handle_result(False, message, dialog_on_success=False)
            return

        self.log(message)
        self.refresh_view()

    def _on_logout(self) -> None:
        self.controller.logout()
        self.control_status_var.set("Sin acciones enviadas.")
        self.log("Sesión cerrada.")
        self.refresh_view()

    def _on_capture_registration(self) -> None:
        success, measurement, message = self.controller.capture_measurement(
            "registro inicial"
        )
        if not success or measurement is None:
            self._handle_result(False, message, dialog_on_success=False)
            return

        self._write_measurement_vars(self.registration_measurement_vars, measurement)
        self.log(message)
        self.refresh_view()

    def _on_register_user(self) -> None:
        measurement = self._read_measurement_vars(self.registration_measurement_vars)
        if measurement is None:
            return

        success, message = self.controller.register_user(
            self.register_username_var.get(),
            self.register_password_var.get(),
            self.register_confirm_var.get(),
            measurement,
        )
        if success:
            self._clear_registration_form()
        self._handle_result(success, message)

    def _clear_registration_form(self) -> None:
        self.register_password_var.set("")
        self.register_confirm_var.set("")

    def _on_load_profile(self) -> None:
        username = self._get_selected_profile_name()
        success, message = self.controller.load_profile(username)
        self._handle_result(success, message)

    def _on_capture_calibration(self) -> None:
        success, measurement, message = self.controller.capture_measurement("calibracion")
        if not success or measurement is None:
            self._handle_result(False, message, dialog_on_success=False)
            return

        self._write_measurement_vars(self.calibration_measurement_vars, measurement)
        self.log(message)
        self.refresh_view()

    def _on_save_calibration(self) -> None:
        measurement = self._read_measurement_vars(self.calibration_measurement_vars)
        if measurement is None:
            return

        success, message = self.controller.save_calibration(measurement)
        self._handle_result(success, message)

    def _on_arm_action(self, action_key: str) -> None:
        success, message = self.controller.perform_arm_action(action_key)
        if success:
            self.control_status_var.set(message)
        self._handle_result(success, message, dialog_on_success=False)

    def _on_toggle_realtime_tracking(self) -> None:
        success, message = self.controller.set_realtime_tracking(
            self.realtime_enabled_var.get()
        )
        if not success:
            self._syncing_tracking_ui = True
            self.realtime_enabled_var.set(not self.realtime_enabled_var.get())
            self._syncing_tracking_ui = False
            self._handle_result(False, message, dialog_on_success=False)
            return

        self.log(message)
        self.refresh_view()

    def _on_reset_realtime_tracking(self) -> None:
        success, message = self.controller.reset_realtime_tracking_pose()
        if not success:
            self._handle_result(False, message, dialog_on_success=False)
            return

        self.log(message)
        self.refresh_view()

    def _on_realtime_pose_changed(self, _value: str) -> None:
        if self._syncing_tracking_ui:
            return

        pose = self._get_realtime_pose_from_vars()
        for key, _, _, _, value_kind in TRACKING_SLIDERS:
            self.realtime_value_vars[key].set(
                self._format_tracking_value(self.realtime_pose_vars[key].get(), value_kind)
            )

        success, message = self.controller.update_realtime_hand_pose(
            pose.height_pct,
            pose.reach_pct,
            pose.lateral_pct,
            pose.wrist_deg,
            pose.grip_pct,
        )
        if not success:
            self.realtime_status_var.set(message)
            return

        self._refresh_realtime_tracking()

    def _on_tracking_canvas_motion(self, event: tk.Event) -> None:
        if not self.realtime_enabled_var.get():
            return

        width = max(self.tracking_canvas.winfo_width(), 1)
        height = max(self.tracking_canvas.winfo_height(), 1)
        x_ratio = max(0.0, min(1.0, event.x / width))
        y_ratio = max(0.0, min(1.0, event.y / height))

        self._syncing_tracking_ui = True
        self.realtime_pose_vars["lateral_pct"].set(
            self._clamp_tracking_value("lateral_pct", x_ratio * 200.0 - 100.0)
        )
        self.realtime_pose_vars["height_pct"].set(
            self._clamp_tracking_value("height_pct", 100.0 - y_ratio * 100.0)
        )
        self._syncing_tracking_ui = False

        for key, _, _, _, value_kind in TRACKING_SLIDERS:
            self.realtime_value_vars[key].set(
                self._format_tracking_value(self.realtime_pose_vars[key].get(), value_kind)
            )

        pose = self._get_realtime_pose_from_vars()
        success, message = self.controller.update_realtime_hand_pose(
            pose.height_pct,
            pose.reach_pct,
            pose.lateral_pct,
            pose.wrist_deg,
            pose.grip_pct,
        )
        if not success:
            self.realtime_status_var.set(message)
            return

        self._refresh_realtime_tracking()

    def _on_tracking_canvas_leave(self, _event: tk.Event) -> None:
        if self.realtime_enabled_var.get():
            self.realtime_status_var.set(
                "Seguimiento activo en pausa de raton. Vuelve a la vista para continuar."
            )

    def _on_add_command(self) -> None:
        try:
            duration_ms = int(self.command_duration_var.get())
        except ValueError:
            self._show_error("Duración inválida", "La duración debe ser un número entero.")
            return

        success, message = self.controller.add_pending_command(
            self.command_name_var.get(),
            duration_ms,
        )
        if success:
            self.command_name_var.set("")
        self._handle_result(success, message, dialog_on_success=False)

    def _on_remove_command(self) -> None:
        selection = self.commands_tree.selection()
        if not selection:
            self._show_error("Selección requerida", "Selecciona un comando para quitarlo.")
            return

        success, message = self.controller.remove_pending_command(int(selection[0]))
        self._handle_result(success, message, dialog_on_success=False)

    def _on_clear_commands(self) -> None:
        self.controller.clear_pending_commands()
        self.log("Secuencia temporal vaciada.")
        self.refresh_view()

    def _on_load_saved_sequence(self) -> None:
        success, message = self.controller.load_saved_commands_into_pending()
        self._handle_result(success, message, dialog_on_success=False)

    def _on_save_commands(self) -> None:
        success, message = self.controller.save_pending_commands()
        self._handle_result(success, message)

    def _handle_result(
        self,
        success: bool,
        message: str,
        dialog_on_success: bool = True,
    ) -> None:
        if success:
            self.log(message)
            self.refresh_view()
            if dialog_on_success:
                messagebox.showinfo("Proyecto SAC", message)
            return

        self.log(f"Error: {message}")
        self.refresh_view()
        self._show_error("Proyecto SAC", message)

    def _show_error(self, title: str, message: str) -> None:
        messagebox.showerror(title, message)

    def log(self, message: str) -> None:
        self.log_text.configure(state="normal")
        self.log_text.insert("end", f"- {message}\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

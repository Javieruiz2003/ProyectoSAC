from __future__ import annotations

from .models import (
    MAX_COMMANDS,
    ArmCommand,
    AuthMode,
    BiometricData,
    CommandSequence,
    HandPose,
    RealtimeTrackingState,
    SessionContext,
    UserProfile,
)
from .services.arm import ArmService
from .services.sensor import (
    SensorService,
    SensorServiceError,
    SensorSnapshot,
    UartSensorConfig,
)
from .storage import JsonStorage


class AppController:
    def __init__(
        self,
        storage: JsonStorage,
        sensor: SensorService,
        arm: ArmService,
    ) -> None:
        self.storage = storage
        self.sensor = sensor
        self.arm = arm
        self.context = SessionContext()
        self._sensor_snapshot = self.sensor.initialize()

    def get_context(self) -> SessionContext:
        return self.context

    def get_sensor_snapshot(self) -> SensorSnapshot:
        self._sensor_snapshot = self.sensor.get_snapshot()
        return self._sensor_snapshot

    def get_sensor_config(self) -> UartSensorConfig:
        return self.sensor.get_config()

    def list_available_serial_ports(self) -> list[str]:
        return self.sensor.list_available_ports()

    def configure_sensor(self, config: UartSensorConfig) -> tuple[bool, str]:
        try:
            snapshot = self.sensor.apply_config(config)
        except SensorServiceError as exc:
            return False, str(exc)

        self._sensor_snapshot = snapshot
        return True, snapshot.status_text

    def has_registered_users(self) -> bool:
        return self.storage.has_registered_user_credentials()

    def list_profiles(self) -> list[UserProfile]:
        return self.storage.list_profiles()

    def logout(self) -> None:
        self.arm.clear_tracking()
        self.context.reset_session()

    def shutdown(self) -> None:
        self.sensor.close()

    def get_realtime_tracking_state(self) -> RealtimeTrackingState:
        return self.arm.get_tracking_state()

    def login_normal(
        self,
        username: str,
        password: str,
        arm_code: str,
    ) -> tuple[bool, str]:
        username = username.strip()
        password = password.strip()
        arm_code = arm_code.strip()

        if not password:
            return False, "Introduce una contraseña antes de continuar."

        if self.storage.has_registered_user_credentials():
            if not username:
                return False, "Introduce el nombre de usuario."
            if not self.storage.verify_user_password(username, password):
                self.context.reset_session()
                return False, "Credenciales incorrectas."
        else:
            if not self.storage.verify_normal_mode_password(password):
                self.context.reset_session()
                return False, "La contraseña del modo normal no es válida."

        if not self.arm.validate_identity(arm_code):
            self.context.reset_session()
            return False, "El código del brazo no coincide con la simulación."

        self.context.is_authenticated = True
        self.context.is_admin_mode = False
        self.context.arm_verified = True
        self.context.auth_mode = AuthMode.NORMAL
        self.context.current_username = username

        profile = self.storage.load_user_profile(username) if username else None
        if profile is not None:
            self._set_active_profile(profile)
            return True, f"Acceso concedido para {profile.username}."

        self.context.active_profile = UserProfile(username=username)
        self.context.profile_loaded = False
        return True, "Acceso normal concedido. Ya puedes registrar o cargar un perfil."

    def login_admin(self, usb_id: str) -> tuple[bool, str]:
        usb_id = usb_id.strip()
        if not usb_id:
            return False, "Introduce el identificador del pendrive maestro."

        if not self.storage.is_master_usb_valid(usb_id):
            self.context.reset_session()
            return False, "Pendrive maestro no válido."

        self.context.is_authenticated = True
        self.context.is_admin_mode = True
        self.context.usb_verified = True
        self.context.auth_mode = AuthMode.ADMIN
        self.context.current_username = ""
        self.context.active_profile = UserProfile(username="")
        self.context.profile_loaded = False
        return True, "Modo administrador activado."

    def capture_measurement(
        self, label: str
    ) -> tuple[bool, BiometricData | None, str]:
        try:
            data = self.sensor.capture_bioimpedance(label)
        except SensorServiceError as exc:
            self._sensor_snapshot = self.sensor.get_snapshot()
            return False, None, str(exc)

        snapshot = self.get_sensor_snapshot()
        source = "simulación" if snapshot.uses_mock_capture else "UART"
        return True, data, f"Medición obtenida desde {source}: {snapshot.status_text}"

    def register_user(
        self,
        username: str,
        password: str,
        confirm_password: str,
        measurement: BiometricData,
    ) -> tuple[bool, str]:
        username = username.strip()
        if not self.context.is_authenticated:
            return False, "Debes iniciar sesión antes de registrar un usuario."
        if not username:
            return False, "Introduce un nombre de usuario."
        if not password:
            return False, "La contraseña no puede estar vacía."
        if password != confirm_password:
            return False, "Las contraseñas no coinciden."
        if self.storage.user_exists(username):
            return False, "Ese usuario ya existe."

        profile = UserProfile(
            username=username,
            registered_bioimpedance=measurement,
            has_registered_bioimpedance=True,
        )
        if not self.storage.register_user_account(profile, password):
            return False, "No se pudo guardar el usuario."

        self._set_active_profile(profile)
        self.context.user_registered_this_session = True
        return True, f'Usuario "{username}" registrado correctamente.'

    def load_profile(self, username: str) -> tuple[bool, str]:
        username = username.strip()
        if not self.context.is_authenticated:
            return False, "Debes iniciar sesión antes de cargar un perfil."
        if not username:
            return False, "Selecciona un perfil."

        profile = self.storage.load_user_profile(username)
        if profile is None:
            return False, "No se encontró el perfil seleccionado."

        self._set_active_profile(profile)
        return True, f'Perfil "{username}" cargado correctamente.'

    def save_calibration(self, measurement: BiometricData) -> tuple[bool, str]:
        if not self.context.is_authenticated:
            return False, "Necesitas una sesión activa."
        if not self.context.current_username:
            return False, "Carga o crea un perfil antes de calibrar."
        if not self.storage.user_exists(self.context.current_username):
            return False, "El perfil activo no existe en almacenamiento."
        if not self.storage.update_calibration_data(
            self.context.current_username, measurement
        ):
            return False, "No se pudo guardar la calibración."

        self.context.calibration_done_this_session = True
        self._refresh_active_profile(self.context.current_username)
        return True, "Calibración guardada correctamente."

    def perform_arm_action(self, action_key: str) -> tuple[bool, str]:
        can_operate, message = self._can_operate_arm()
        if not can_operate:
            return False, message

        return True, self.arm.perform_action(action_key)

    def set_realtime_tracking(self, enabled: bool) -> tuple[bool, str]:
        can_operate, message = self._can_operate_arm()
        if not can_operate:
            return False, message

        state = self.arm.set_tracking_enabled(enabled)
        return True, state.status_text

    def update_realtime_hand_pose(
        self,
        height_pct: float,
        reach_pct: float,
        lateral_pct: float,
        wrist_deg: float,
        grip_pct: float,
    ) -> tuple[bool, str]:
        can_operate, message = self._can_operate_arm()
        if not can_operate:
            return False, message

        state = self.arm.update_hand_pose(
            HandPose(
                height_pct=height_pct,
                reach_pct=reach_pct,
                lateral_pct=lateral_pct,
                wrist_deg=wrist_deg,
                grip_pct=grip_pct,
            )
        )
        return True, state.status_text

    def reset_realtime_tracking_pose(self) -> tuple[bool, str]:
        can_operate, message = self._can_operate_arm()
        if not can_operate:
            return False, message

        state = self.arm.reset_tracking_pose()
        return True, state.status_text

    def add_pending_command(self, name: str, duration_ms: int) -> tuple[bool, str]:
        if not self.context.is_authenticated:
            return False, "La grabación requiere una sesión activa."
        if not self.context.profile_loaded:
            return False, "No hay un perfil activo para asociar la secuencia."
        if not name.strip():
            return False, "Introduce el nombre del comando."
        if duration_ms < 100 or duration_ms > 60_000:
            return False, "La duración debe estar entre 100 y 60000 ms."
        if self.context.pending_commands.count >= MAX_COMMANDS:
            return False, f"Solo se permiten {MAX_COMMANDS} comandos por secuencia."

        self.context.pending_commands.commands.append(
            ArmCommand(name=name.strip(), duration_ms=duration_ms)
        )
        self.context.commands_recorded_this_session = True
        self.context.save_commands_pending = True
        return True, "Comando añadido a la secuencia temporal."

    def remove_pending_command(self, index: int) -> tuple[bool, str]:
        if index < 0 or index >= self.context.pending_commands.count:
            return False, "Selecciona un comando válido."

        removed = self.context.pending_commands.commands.pop(index)
        self.context.save_commands_pending = self.context.pending_commands.count > 0
        return True, f'Comando "{removed.name}" eliminado de la secuencia.'

    def clear_pending_commands(self) -> None:
        self.context.pending_commands = CommandSequence()
        self.context.save_commands_pending = False

    def load_saved_commands_into_pending(self) -> tuple[bool, str]:
        if not self.context.profile_loaded:
            return False, "No hay un perfil cargado."
        if not self.context.active_profile.has_saved_commands:
            return False, "El perfil activo no tiene una secuencia guardada."

        self.context.pending_commands = CommandSequence(
            commands=[
                ArmCommand(name=command.name, duration_ms=command.duration_ms)
                for command in self.context.active_profile.saved_commands.commands
            ]
        )
        self.context.save_commands_pending = self.context.pending_commands.count > 0
        return True, "Secuencia guardada cargada en el editor."

    def save_pending_commands(self) -> tuple[bool, str]:
        if not self.context.profile_loaded:
            return False, "Carga o crea un perfil antes de guardar comandos."
        if self.context.pending_commands.count == 0:
            return False, "No hay comandos pendientes de guardado."
        if not self.storage.save_command_sequence(
            self.context.current_username, self.context.pending_commands
        ):
            return False, "No se pudo guardar la secuencia."

        self.context.save_commands_pending = False
        self._refresh_active_profile(self.context.current_username)
        return True, "Secuencia guardada correctamente."

    def _set_active_profile(self, profile: UserProfile) -> None:
        self.context.active_profile = profile
        self.context.current_username = profile.username
        self.context.profile_loaded = True

    def _can_operate_arm(self) -> tuple[bool, str]:
        if not self.context.is_authenticated:
            return False, "Debes autenticarte antes de controlar el brazo."
        if not self.context.profile_loaded:
            return False, "Carga o crea un perfil antes de operar."

        return True, ""

    def _refresh_active_profile(self, username: str) -> None:
        profile = self.storage.load_user_profile(username)
        if profile is not None:
            self._set_active_profile(profile)

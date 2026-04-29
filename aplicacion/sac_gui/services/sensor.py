from __future__ import annotations

from collections import deque
from dataclasses import dataclass, replace
import math
import random
import struct
import time

from ..models import BiometricData

try:
    import serial
    from serial import SerialException
    from serial.tools import list_ports
except ImportError:  # pragma: no cover - optional runtime dependency
    serial = None
    list_ports = None

    class SerialException(Exception):
        pass


@dataclass(slots=True)
class UartSensorConfig:
    source_mode: str = "mock"
    port: str = "COM3"
    baudrate: int = 115200
    data_type: str = "float32"
    byte_order: str = "little"
    averaging_window: int = 5
    timeout_ms: int = 250
    magnitude_scale: float = 1.0
    phase_scale: float = 1.0

    def copy(self) -> "UartSensorConfig":
        return replace(self)


@dataclass(slots=True)
class SensorSnapshot:
    initialized: bool
    hardware_ready: bool
    uses_mock_capture: bool
    status_text: str
    source_mode: str
    port_name: str
    packet_format: str
    averaging_window: int


@dataclass(slots=True)
class UartSensorSample:
    frequency_hz: float
    magnitude: float
    phase_deg: float


class SensorServiceError(RuntimeError):
    pass


class SensorService:
    def __init__(self) -> None:
        self._rng = random.Random()
        self._initialized = False
        self._hardware_ready = False
        self._status_text = (
            "Captura simulada activa. Cambia a UART en la pestaña Sensor para "
            "leer frecuencia, modulo de impedancia y fase desde la placa."
        )
        self._config = UartSensorConfig()
        self._serial_connection = None
        self._packet_buffer = bytearray()
        self._recent_uart_samples: deque[UartSensorSample] = deque(maxlen=128)

    def initialize(self) -> SensorSnapshot:
        self._initialized = True
        if self._config.source_mode == "uart":
            self._refresh_uart_status()
        return self.get_snapshot()

    def get_snapshot(self) -> SensorSnapshot:
        return SensorSnapshot(
            initialized=self._initialized,
            hardware_ready=self._hardware_ready,
            uses_mock_capture=self._config.source_mode != "uart",
            status_text=self._status_text,
            source_mode=self._config.source_mode,
            port_name=self._config.port,
            packet_format=(
                f"{self._config.data_type}/{self._config.byte_order}"
                if self._config.source_mode == "uart"
                else "mock"
            ),
            averaging_window=self._config.averaging_window,
        )

    def get_config(self) -> UartSensorConfig:
        return self._config.copy()

    def list_available_ports(self) -> list[str]:
        if list_ports is None:
            return []

        return [port.device for port in list_ports.comports()]

    def apply_config(self, config: UartSensorConfig) -> SensorSnapshot:
        sanitized = self._sanitize_config(config)
        config_changed = sanitized != self._config
        self._config = sanitized

        if config_changed:
            self._packet_buffer.clear()
            self._recent_uart_samples.clear()

        if self._config.source_mode == "uart":
            self._refresh_uart_status(force_reconnect=True)
        else:
            self._close_serial_connection()
            self._hardware_ready = False
            self._status_text = (
                "Captura simulada activa. Los botones de lectura usarán datos "
                "sintéticos hasta que actives UART."
            )

        self._initialized = True
        return self.get_snapshot()

    def capture_bioimpedance(self, label: str) -> BiometricData:
        if not self._initialized:
            self.initialize()

        if self._config.source_mode == "uart":
            return self._capture_uart_bioimpedance()

        return self._capture_mock_bioimpedance(label)

    def close(self) -> None:
        self._close_serial_connection()

    def _capture_mock_bioimpedance(self, label: str) -> BiometricData:
        magnitude = self._rng.uniform(470.0, 690.0)
        phase_deg = self._rng.uniform(-12.0, 18.0)
        phase_rad = math.radians(phase_deg)
        resistance = magnitude * math.cos(phase_rad)
        reactance = magnitude * math.sin(phase_rad)
        quality = max(65.0, min(99.0, self._rng.uniform(79.0, 97.0)))

        if label:
            quality = max(65.0, min(99.0, quality + (len(label) % 3) * 0.4))

        self._status_text = (
            "Captura simulada activa. Se ha generado una muestra virtual de "
            "modulo de impedancia/fase para la medición solicitada."
        )
        return BiometricData(
            resistance_ohm=round(resistance, 2),
            reactance_ohm=round(reactance, 2),
            phase_deg=round(phase_deg, 2),
            quality_index=round(quality, 2),
        )

    def _capture_uart_bioimpedance(self) -> BiometricData:
        self._ensure_uart_connection()
        new_samples = self._read_available_uart_samples()
        if not new_samples:
            raise SensorServiceError(
                "No se recibieron paquetes completos por UART dentro del tiempo de espera."
            )

        window = min(self._config.averaging_window, len(self._recent_uart_samples))
        samples = list(self._recent_uart_samples)[-window:]
        avg_frequency_hz = sum(sample.frequency_hz for sample in samples) / window
        avg_magnitude = sum(sample.magnitude for sample in samples) / window
        avg_phase_deg = sum(sample.phase_deg for sample in samples) / window

        magnitude_spread = (
            max(sample.magnitude for sample in samples) -
            min(sample.magnitude for sample in samples)
        )
        phase_spread = (
            max(sample.phase_deg for sample in samples) -
            min(sample.phase_deg for sample in samples)
        )
        quality = max(50.0, min(99.0, 98.0 - magnitude_spread * 0.08 - phase_spread * 0.8))

        phase_rad = math.radians(avg_phase_deg)
        resistance = avg_magnitude * math.cos(phase_rad)
        reactance = avg_magnitude * math.sin(phase_rad)

        self._hardware_ready = True
        self._status_text = (
            f"UART {self._config.port} activa. Última lectura: media de {window} "
            f"muestras a {avg_frequency_hz:g} Hz "
            f"({self._config.data_type}, {self._config.byte_order})."
        )
        return BiometricData(
            resistance_ohm=round(resistance, 2),
            reactance_ohm=round(reactance, 2),
            phase_deg=round(avg_phase_deg, 2),
            quality_index=round(quality, 2),
        )

    def _sanitize_config(self, config: UartSensorConfig) -> UartSensorConfig:
        source_mode = config.source_mode.strip().lower()
        if source_mode not in {"mock", "uart"}:
            raise SensorServiceError("La fuente del sensor debe ser 'mock' o 'uart'.")

        data_type = config.data_type.strip().lower()
        if data_type not in {"float32", "uint32"}:
            raise SensorServiceError("El tipo de dato UART debe ser float32 o uint32.")

        byte_order = config.byte_order.strip().lower()
        if byte_order not in {"little", "big"}:
            raise SensorServiceError("El orden de bytes debe ser little o big.")

        if config.baudrate <= 0:
            raise SensorServiceError("La velocidad UART debe ser un entero positivo.")
        if config.averaging_window <= 0:
            raise SensorServiceError("La media debe usar al menos 1 muestra.")
        if config.timeout_ms <= 0:
            raise SensorServiceError("El tiempo de espera debe ser mayor que cero.")

        return UartSensorConfig(
            source_mode=source_mode,
            port=config.port.strip(),
            baudrate=config.baudrate,
            data_type=data_type,
            byte_order=byte_order,
            averaging_window=config.averaging_window,
            timeout_ms=config.timeout_ms,
            magnitude_scale=config.magnitude_scale,
            phase_scale=config.phase_scale,
        )

    def _refresh_uart_status(self, force_reconnect: bool = False) -> None:
        if serial is None:
            self._hardware_ready = False
            self._status_text = (
                "UART seleccionada, pero pyserial no está instalado. Instala pyserial "
                "o vuelve a Simulación."
            )
            return

        if not self._config.port:
            self._hardware_ready = False
            self._status_text = (
                "UART seleccionada, pero todavía no hay un puerto configurado."
            )
            return

        if force_reconnect:
            self._close_serial_connection()

        try:
            self._ensure_uart_connection()
        except SensorServiceError as exc:
            self._hardware_ready = False
            self._status_text = str(exc)
            return

        self._hardware_ready = True
        self._status_text = (
            f"UART lista en {self._config.port}. Esperando paquetes con "
            f"frecuencia, modulo de impedancia y fase en formato "
            f"{self._config.data_type}."
        )

    def _ensure_uart_connection(self) -> None:
        if serial is None:
            raise SensorServiceError(
                "No se puede abrir UART porque pyserial no está instalado."
            )

        if not self._config.port:
            raise SensorServiceError(
                "No se puede leer por UART porque no hay un puerto configurado."
            )

        timeout_seconds = self._config.timeout_ms / 1000.0

        try:
            if self._serial_connection is None:
                self._serial_connection = serial.Serial(
                    port=self._config.port,
                    baudrate=self._config.baudrate,
                    timeout=timeout_seconds,
                )
            elif not self._serial_connection.is_open:
                self._serial_connection.open()

            self._serial_connection.timeout = timeout_seconds
            self._serial_connection.baudrate = self._config.baudrate
            self._hardware_ready = True
        except (SerialException, OSError, ValueError) as exc:
            self._close_serial_connection()
            raise SensorServiceError(
                f"No se pudo abrir el puerto UART {self._config.port}: {exc}"
            ) from exc

    def _close_serial_connection(self) -> None:
        if self._serial_connection is None:
            return

        try:
            if self._serial_connection.is_open:
                self._serial_connection.close()
        except (SerialException, OSError):
            pass
        finally:
            self._serial_connection = None

    def _read_available_uart_samples(self) -> list[UartSensorSample]:
        if self._serial_connection is None:
            raise SensorServiceError("La conexión UART no está disponible.")

        packet_size = self._get_packet_size()
        deadline = time.monotonic() + (self._config.timeout_ms / 1000.0)
        new_samples: list[UartSensorSample] = []

        while time.monotonic() < deadline:
            bytes_waiting = max(self._serial_connection.in_waiting, packet_size)
            chunk = self._serial_connection.read(bytes_waiting)
            if chunk:
                self._packet_buffer.extend(chunk)
                while len(self._packet_buffer) >= packet_size:
                    packet = bytes(self._packet_buffer[:packet_size])
                    del self._packet_buffer[:packet_size]
                    sample = self._decode_uart_packet(packet)
                    new_samples.append(sample)
                    self._recent_uart_samples.append(sample)

                if len(new_samples) >= self._config.averaging_window:
                    break
                continue

            if new_samples:
                break

            time.sleep(0.01)

        return new_samples

    def _decode_uart_packet(self, packet: bytes) -> UartSensorSample:
        try:
            raw_frequency, raw_magnitude, raw_phase = struct.unpack(
                self._get_struct_format(),
                packet,
            )
        except struct.error as exc:
            raise SensorServiceError(
                "Se recibió un paquete UART con un tamaño incompatible."
            ) from exc

        frequency_hz = float(raw_frequency)
        magnitude = float(raw_magnitude) * self._config.magnitude_scale
        phase_deg = float(raw_phase) * self._config.phase_scale
        return UartSensorSample(
            frequency_hz=frequency_hz,
            magnitude=magnitude,
            phase_deg=phase_deg,
        )

    def _get_struct_format(self) -> str:
        endian = "<" if self._config.byte_order == "little" else ">"
        value_code = "f" if self._config.data_type == "float32" else "I"
        return f"{endian}{value_code}{value_code}{value_code}"

    def _get_packet_size(self) -> int:
        return struct.calcsize(self._get_struct_format())

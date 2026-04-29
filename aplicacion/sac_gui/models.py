from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import Enum
from typing import Any

MAX_COMMANDS = 10


class AuthMode(str, Enum):
    NONE = "none"
    NORMAL = "normal"
    ADMIN = "admin"


@dataclass(slots=True)
class BiometricData:
    resistance_ohm: float = 0.0
    reactance_ohm: float = 0.0
    phase_deg: float = 0.0
    quality_index: float = 0.0

    def to_dict(self) -> dict[str, float]:
        return {
            "resistance_ohm": self.resistance_ohm,
            "reactance_ohm": self.reactance_ohm,
            "phase_deg": self.phase_deg,
            "quality_index": self.quality_index,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> "BiometricData":
        payload = payload or {}
        return cls(
            resistance_ohm=float(payload.get("resistance_ohm", 0.0)),
            reactance_ohm=float(payload.get("reactance_ohm", 0.0)),
            phase_deg=float(payload.get("phase_deg", 0.0)),
            quality_index=float(payload.get("quality_index", 0.0)),
        )


@dataclass(slots=True)
class HandPose:
    height_pct: float = 50.0
    reach_pct: float = 50.0
    lateral_pct: float = 0.0
    wrist_deg: float = 0.0
    grip_pct: float = 50.0

    def copy(self) -> "HandPose":
        return replace(self)

    def summary(self) -> str:
        return (
            f"Altura {self.height_pct:.0f}% | "
            f"Avance {self.reach_pct:.0f}% | "
            f"Lateral {self.lateral_pct:+.0f}% | "
            f"Giro {self.wrist_deg:+.0f} deg | "
            f"Pinza {self.grip_pct:.0f}%"
        )


@dataclass(slots=True)
class RealtimeTrackingState:
    tracking_enabled: bool = False
    hand_pose: HandPose = field(default_factory=HandPose)
    arm_pose: HandPose = field(default_factory=HandPose)
    status_text: str = (
        "Seguimiento listo. Activa el modo en tiempo real para que el brazo copie la mano simulada."
    )

    def copy(self) -> "RealtimeTrackingState":
        return RealtimeTrackingState(
            tracking_enabled=self.tracking_enabled,
            hand_pose=self.hand_pose.copy(),
            arm_pose=self.arm_pose.copy(),
            status_text=self.status_text,
        )


@dataclass(slots=True)
class ArmCommand:
    name: str
    duration_ms: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "duration_ms": self.duration_ms,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> "ArmCommand":
        payload = payload or {}
        return cls(
            name=str(payload.get("name", "")),
            duration_ms=int(payload.get("duration_ms", 0)),
        )


@dataclass(slots=True)
class CommandSequence:
    commands: list[ArmCommand] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.commands)

    def to_dict(self) -> dict[str, Any]:
        return {
            "commands": [command.to_dict() for command in self.commands],
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> "CommandSequence":
        payload = payload or {}
        return cls(
            commands=[
                ArmCommand.from_dict(command_payload)
                for command_payload in payload.get("commands", [])
            ]
        )


@dataclass(slots=True)
class UserProfile:
    username: str
    registered_bioimpedance: BiometricData = field(default_factory=BiometricData)
    calibration_bioimpedance: BiometricData = field(default_factory=BiometricData)
    has_registered_bioimpedance: bool = False
    has_calibration_data: bool = False
    saved_commands: CommandSequence = field(default_factory=CommandSequence)
    has_saved_commands: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "username": self.username,
            "registered_bioimpedance": self.registered_bioimpedance.to_dict(),
            "calibration_bioimpedance": self.calibration_bioimpedance.to_dict(),
            "has_registered_bioimpedance": self.has_registered_bioimpedance,
            "has_calibration_data": self.has_calibration_data,
            "saved_commands": self.saved_commands.to_dict(),
            "has_saved_commands": self.has_saved_commands,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> "UserProfile":
        payload = payload or {}
        return cls(
            username=str(payload.get("username", "")),
            registered_bioimpedance=BiometricData.from_dict(
                payload.get("registered_bioimpedance")
            ),
            calibration_bioimpedance=BiometricData.from_dict(
                payload.get("calibration_bioimpedance")
            ),
            has_registered_bioimpedance=bool(
                payload.get("has_registered_bioimpedance", False)
            ),
            has_calibration_data=bool(payload.get("has_calibration_data", False)),
            saved_commands=CommandSequence.from_dict(payload.get("saved_commands")),
            has_saved_commands=bool(payload.get("has_saved_commands", False)),
        )


@dataclass(slots=True)
class SessionContext:
    is_authenticated: bool = False
    is_admin_mode: bool = False
    arm_verified: bool = False
    usb_verified: bool = False
    profile_loaded: bool = False
    user_registered_this_session: bool = False
    calibration_done_this_session: bool = False
    commands_recorded_this_session: bool = False
    save_commands_pending: bool = False
    auth_mode: AuthMode = AuthMode.NONE
    current_username: str = ""
    active_profile: UserProfile = field(default_factory=lambda: UserProfile(username=""))
    pending_commands: CommandSequence = field(default_factory=CommandSequence)

    def reset_session(self) -> None:
        self.is_authenticated = False
        self.is_admin_mode = False
        self.arm_verified = False
        self.usb_verified = False
        self.profile_loaded = False
        self.user_registered_this_session = False
        self.calibration_done_this_session = False
        self.commands_recorded_this_session = False
        self.save_commands_pending = False
        self.auth_mode = AuthMode.NONE
        self.current_username = ""
        self.active_profile = UserProfile(username="")
        self.pending_commands = CommandSequence()

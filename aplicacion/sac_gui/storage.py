from __future__ import annotations

import hashlib
import hmac
import json
from pathlib import Path
import secrets
from typing import Any

from .models import BiometricData, CommandSequence, UserProfile

DEFAULT_NORMAL_MODE_PASSWORD = "brazo123"
DEFAULT_MASTER_USB_ID = "MASTER-USB-001"
MAX_USERS = 8
PBKDF2_ITERATIONS = 120_000


class JsonStorage:
    def __init__(self, base_dir: Path) -> None:
        self._base_dir = base_dir
        self._data_dir = self._base_dir / "data"
        self._path = self._data_dir / "app_state.json"
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._data: dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        if self._path.exists():
            try:
                self._data = json.loads(self._path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                self._data = self._build_default_data()
                self._save()
                return

            self._ensure_defaults()
            self._save()
            return

        self._data = self._build_default_data()
        self._save()

    def _build_default_data(self) -> dict[str, Any]:
        return {
            "normal_mode": self._build_secret(DEFAULT_NORMAL_MODE_PASSWORD),
            "master_usb": self._build_secret(DEFAULT_MASTER_USB_ID),
            "users": {},
        }

    def _ensure_defaults(self) -> None:
        if "normal_mode" not in self._data:
            self._data["normal_mode"] = self._build_secret(DEFAULT_NORMAL_MODE_PASSWORD)

        if "master_usb" not in self._data:
            self._data["master_usb"] = self._build_secret(DEFAULT_MASTER_USB_ID)

        if "users" not in self._data or not isinstance(self._data["users"], dict):
            self._data["users"] = {}

    def _save(self) -> None:
        self._path.write_text(
            json.dumps(self._data, indent=2, ensure_ascii=True),
            encoding="utf-8",
        )

    def _build_secret(self, value: str) -> dict[str, str]:
        salt = secrets.token_hex(16)
        return {
            "salt": salt,
            "password_hash": self._hash_secret(value, salt),
        }

    def _hash_secret(self, raw_value: str, salt_hex: str) -> str:
        return hashlib.pbkdf2_hmac(
            "sha256",
            raw_value.encode("utf-8"),
            bytes.fromhex(salt_hex),
            PBKDF2_ITERATIONS,
        ).hex()

    def _verify_secret(self, raw_value: str, payload: dict[str, str]) -> bool:
        if not raw_value or not payload:
            return False

        salt = payload.get("salt")
        expected_hash = payload.get("password_hash")
        if not salt or not expected_hash:
            return False

        current_hash = self._hash_secret(raw_value, salt)
        return hmac.compare_digest(current_hash, expected_hash)

    def list_profiles(self) -> list[UserProfile]:
        users = self._data.get("users", {})
        profiles = [
            UserProfile.from_dict(user_payload.get("profile"))
            for user_payload in users.values()
        ]
        return sorted(profiles, key=lambda profile: profile.username.lower())

    def has_registered_user_credentials(self) -> bool:
        return bool(self._data.get("users"))

    def user_exists(self, username: str) -> bool:
        return username in self._data.get("users", {})

    def load_user_profile(self, username: str) -> UserProfile | None:
        user_payload = self._data.get("users", {}).get(username)
        if not user_payload:
            return None

        return UserProfile.from_dict(user_payload.get("profile"))

    def save_user_profile(self, profile: UserProfile) -> bool:
        if not profile.username:
            return False

        users = self._data.setdefault("users", {})
        if profile.username not in users:
            return False

        users[profile.username]["profile"] = profile.to_dict()
        self._save()
        return True

    def register_user_account(self, profile: UserProfile, password: str) -> bool:
        if not profile.username or not password:
            return False

        users = self._data.setdefault("users", {})
        if profile.username not in users and len(users) >= MAX_USERS:
            return False

        users[profile.username] = {
            "credentials": self._build_secret(password),
            "profile": profile.to_dict(),
        }
        self._save()
        return True

    def update_calibration_data(self, username: str, data: BiometricData) -> bool:
        profile = self.load_user_profile(username)
        if profile is None:
            return False

        profile.calibration_bioimpedance = data
        profile.has_calibration_data = True
        return self.save_user_profile(profile)

    def save_command_sequence(self, username: str, sequence: CommandSequence) -> bool:
        profile = self.load_user_profile(username)
        if profile is None:
            return False

        profile.saved_commands = sequence
        profile.has_saved_commands = sequence.count > 0
        return self.save_user_profile(profile)

    def verify_user_password(self, username: str, password: str) -> bool:
        user_payload = self._data.get("users", {}).get(username)
        if not user_payload:
            return False

        return self._verify_secret(password, user_payload.get("credentials", {}))

    def verify_normal_mode_password(self, password: str) -> bool:
        return self._verify_secret(password, self._data.get("normal_mode", {}))

    def is_master_usb_valid(self, usb_id: str) -> bool:
        return self._verify_secret(usb_id, self._data.get("master_usb", {}))

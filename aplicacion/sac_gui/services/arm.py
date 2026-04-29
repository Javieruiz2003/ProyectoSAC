from __future__ import annotations

from ..models import HandPose, RealtimeTrackingState

IDENTITY_CODE = "2468"

ACTION_LABELS = {
    "up": "Brazo moviéndose hacia arriba.",
    "down": "Brazo moviéndose hacia abajo.",
    "left": "Brazo moviéndose hacia la izquierda.",
    "right": "Brazo moviéndose hacia la derecha.",
    "open_grip": "Pinza abierta.",
    "close_grip": "Pinza cerrada.",
}


class ArmService:
    def __init__(self) -> None:
        self._tracking_state = RealtimeTrackingState()

    def validate_identity(self, code: str) -> bool:
        return code.strip() == IDENTITY_CODE

    def get_actions(self) -> list[tuple[str, str]]:
        return [
            ("up", "Arriba"),
            ("left", "Izquierda"),
            ("right", "Derecha"),
            ("down", "Abajo"),
            ("open_grip", "Abrir pinza"),
            ("close_grip", "Cerrar pinza"),
        ]

    def perform_action(self, action_key: str) -> str:
        return ACTION_LABELS.get(action_key, "Acción no reconocida.")

    def get_tracking_state(self) -> RealtimeTrackingState:
        return self._tracking_state.copy()

    def set_tracking_enabled(self, enabled: bool) -> RealtimeTrackingState:
        self._tracking_state.tracking_enabled = enabled
        if enabled:
            self._tracking_state.arm_pose = self._tracking_state.hand_pose.copy()
            self._tracking_state.status_text = (
                "Seguimiento en tiempo real activo. El brazo replica la mano simulada."
            )
        else:
            self._tracking_state.status_text = (
                "Seguimiento en pausa. Puedes mover la mano virtual y reactivar el modo cuando quieras."
            )

        return self.get_tracking_state()

    def update_hand_pose(self, pose: HandPose) -> RealtimeTrackingState:
        self._tracking_state.hand_pose = pose.copy()
        if self._tracking_state.tracking_enabled:
            self._tracking_state.arm_pose = pose.copy()
            self._tracking_state.status_text = (
                "Brazo sincronizado con la mano virtual en tiempo real."
            )
        else:
            self._tracking_state.status_text = (
                "Mano virtual actualizada. Activa el seguimiento para que el brazo copie la pose."
            )

        return self.get_tracking_state()

    def reset_tracking_pose(self) -> RealtimeTrackingState:
        neutral_pose = HandPose()
        self._tracking_state.hand_pose = neutral_pose.copy()
        self._tracking_state.arm_pose = neutral_pose.copy()
        if self._tracking_state.tracking_enabled:
            self._tracking_state.status_text = (
                "Pose centrada. El brazo sigue replicando la mano simulada."
            )
        else:
            self._tracking_state.status_text = (
                "Pose centrada. Activa el seguimiento para volver a sincronizar el brazo."
            )

        return self.get_tracking_state()

    def clear_tracking(self) -> None:
        self._tracking_state = RealtimeTrackingState()

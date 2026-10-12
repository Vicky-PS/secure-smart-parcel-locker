from __future__ import annotations

from hash_chain import HashChainLog, LogEntry
from firmware_security import verify_firmware


class FirmwareRejected(RuntimeError):
    pass


class LockerController:
    def __init__(
        self,
        compartment_id: str,
        public_key_pem: bytes,
        firmware_bytes: bytes,
        firmware_signature: bytes,
    ):
        if not verify_firmware(public_key_pem, firmware_bytes, firmware_signature):
            raise FirmwareRejected(f"{compartment_id}: firmware signature invalid")
        self.compartment_id = compartment_id
        self.log = HashChainLog(compartment_id)
        self._awaiting_authenticated_open = False
        self.log.append("FIRMWARE_VERIFIED", "controller boot accepted")

    def authenticated_unlock(self, actor_ref: str) -> LogEntry:
        self._awaiting_authenticated_open = True
        return self.log.append("UNLOCK_AUTHENTICATED", f"actor={actor_ref}")

    def door_sensor_event(self, opened: bool) -> LogEntry:
        if opened:
            if self._awaiting_authenticated_open:
                event = self.log.append("DOOR_OPEN", "authenticated opening")
            else:
                event = self.log.append("TAMPER", "door opened without authenticated unlock")
            self._awaiting_authenticated_open = False
            return event
        return self.log.append("DOOR_CLOSE", "door closed")

    def courier_claims_delivery_without_door_open(self, actor_ref: str) -> LogEntry:
        return self.log.append(
            "SUSPICIOUS_DELIVERY_CLAIM",
            f"actor={actor_ref}; delivery claimed without door-open sequence",
        )

    def verify_chain(self) -> tuple[bool, int | None]:
        return self.log.verify()

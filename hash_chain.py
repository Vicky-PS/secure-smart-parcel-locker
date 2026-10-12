from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import hashlib
import json
from typing import Any


GENESIS_HASH = "0" * 64


@dataclass
class LogEntry:
    id: str
    compartment_id: str
    index: int
    timestamp: str
    event_type: str
    detail: str
    previous_hash: str
    hash: str
    chain_valid: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class HashChainLog:
    def __init__(self, compartment_id: str):
        self.compartment_id = compartment_id
        self.entries: list[LogEntry] = []

    def append(self, event_type: str, detail: str = "") -> LogEntry:
        index = len(self.entries)
        timestamp = datetime.now(timezone.utc).isoformat()
        previous_hash = self.entries[-1].hash if self.entries else GENESIS_HASH
        entry_hash = self._hash_entry(index, timestamp, event_type, detail, previous_hash)
        entry = LogEntry(
            id=f"{self.compartment_id}-{index:04d}",
            compartment_id=self.compartment_id,
            index=index,
            timestamp=timestamp,
            event_type=event_type,
            detail=detail,
            previous_hash=previous_hash,
            hash=entry_hash,
        )
        self.entries.append(entry)
        return entry

    def tamper_entry(self, index: int, new_detail: str) -> None:
        self.entries[index].detail = new_detail

    def verify(self) -> tuple[bool, int | None]:
        expected_previous = GENESIS_HASH
        for entry in self.entries:
            if entry.previous_hash != expected_previous:
                entry.chain_valid = False
                return False, entry.index
            expected_hash = self._hash_entry(
                entry.index,
                entry.timestamp,
                entry.event_type,
                entry.detail,
                entry.previous_hash,
            )
            if entry.hash != expected_hash:
                entry.chain_valid = False
                return False, entry.index
            expected_previous = entry.hash
            entry.chain_valid = True
        return True, None

    @staticmethod
    def _hash_entry(
        index: int,
        timestamp: str,
        event_type: str,
        detail: str,
        previous_hash: str,
    ) -> str:
        payload = {
            "index": index,
            "timestamp": timestamp,
            "event_type": event_type,
            "detail": detail,
            "previous_hash": previous_hash,
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

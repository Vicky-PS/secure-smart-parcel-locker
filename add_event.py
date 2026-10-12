"""
Append a single new event onto an EXISTING compartment's hash chain.

Unlike simulate_scenarios.py (which always starts each compartment's chain
fresh at index 0), this script reads the compartment's current latest event
from Cosmos DB (falling back to the local JSONL file if Cosmos isn't
configured), seeds an in-memory HashChainLog with that entry, appends one
new event on top of it, and pushes just that new event to IoT Hub and
Cosmos DB.

Usage:
    python add_event.py C-02 DOOR_OPEN "authenticated opening"
    python add_event.py C-02 TAMPER "door opened without authenticated unlock"
    python add_event.py C-06 FIRMWARE_VERIFIED "controller boot accepted"
"""

from __future__ import annotations

import argparse

from hash_chain import HashChainLog, LogEntry
from cloud_logging import read_cosmos_events, send_to_iot_hub, write_to_cosmos, write_local_events


def get_latest_for_compartment(compartment_id: str) -> dict | None:
    events, source = read_cosmos_events()
    print(f"(reading existing history via: {source})")
    matching = [e for e in events if e["compartment_id"] == compartment_id]
    if not matching:
        return None
    matching.sort(key=lambda e: e["index"])
    return matching[-1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("compartment_id", help="e.g. C-02")
    parser.add_argument("event_type", help="e.g. DOOR_OPEN, DOOR_CLOSE, UNLOCK_AUTHENTICATED, TAMPER")
    parser.add_argument("detail", nargs="?", default="", help="Free-text detail for the event")
    args = parser.parse_args()

    log = HashChainLog(args.compartment_id)
    latest = get_latest_for_compartment(args.compartment_id)

    if latest:
        # Pad with lightweight placeholders so HashChainLog.append() computes
        # the correct next index (len(entries)) and reads the correct
        # previous_hash (entries[-1].hash) when it continues the chain.
        for i in range(latest["index"]):
            log.entries.append(LogEntry(
                id=f"__placeholder-{i}", compartment_id=args.compartment_id,
                index=i, timestamp="", event_type="", detail="",
                previous_hash="", hash="",
            ))
        seeded = LogEntry(
            id=latest["id"],
            compartment_id=latest["compartment_id"],
            index=latest["index"],
            timestamp=latest["timestamp"],
            event_type=latest["event_type"],
            detail=latest["detail"],
            previous_hash=latest["previous_hash"],
            hash=latest["hash"],
        )
        log.entries.append(seeded)
        print(f"Continuing chain for {args.compartment_id} from index {seeded.index} "
              f"(previous hash {seeded.hash[:12]}...)")
    else:
        print(f"No existing events found for {args.compartment_id}; starting a new chain.")

    new_entry = log.append(args.event_type, args.detail)
    print(f"\nNew event created:")
    print(f"  id={new_entry.id}  index={new_entry.index}")
    print(f"  event_type={new_entry.event_type}  detail={new_entry.detail!r}")
    print(f"  hash={new_entry.hash[:16]}...")

    write_local_events([new_entry])

    for publish in (send_to_iot_hub, write_to_cosmos):
        try:
            ok, message = publish([new_entry])
        except Exception as exc:
            ok, message = False, f"{publish.__name__} failed: {exc}"
        print(f"{'OK' if ok else 'INFO'}: {message}")


if __name__ == "__main__":
    main()

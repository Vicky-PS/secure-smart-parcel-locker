from __future__ import annotations

from firmware_security import generate_key_pair, sign_firmware
from locker_controller import FirmwareRejected, LockerController
from cloud_logging import reset_local_events, send_to_iot_hub, write_local_events, write_to_cosmos


def collect(controller: LockerController):
    valid, failed_index = controller.verify_chain()
    for entry in controller.log.entries:
        entry.chain_valid = valid if failed_index is None else entry.index < failed_index
    return controller.log.entries


def main() -> None:
    reset_local_events()
    private_key, public_key = generate_key_pair()
    firmware = b"secure-locker-controller-v1"
    signature = sign_firmware(private_key, firmware)
    all_entries = []

    normal = LockerController("C-01", public_key, firmware, signature)
    normal.authenticated_unlock("courier-4101")
    normal.door_sensor_event(True)
    normal.door_sensor_event(False)
    all_entries.extend(collect(normal))

    bypass = LockerController("C-02", public_key, firmware, signature)
    bypass.door_sensor_event(True)
    bypass.door_sensor_event(False)
    all_entries.extend(collect(bypass))

    ghost = LockerController("C-03", public_key, firmware, signature)
    ghost.courier_claims_delivery_without_door_open("courier-7782")
    all_entries.extend(collect(ghost))

    edited = LockerController("C-04", public_key, firmware, signature)
    edited.authenticated_unlock("courier-9150")
    edited.door_sensor_event(True)
    edited.door_sensor_event(False)
    edited.log.tamper_entry(1, "actor=admin-edited-after-the-fact")
    all_entries.extend(collect(edited))

    try:
        LockerController("C-05", public_key, b"secure-locker-controller-v1-modified", signature)
    except FirmwareRejected:
        rejected = LockerController("C-05", public_key, firmware, signature)
        rejected.log.append("FIRMWARE_REJECTED", "modified firmware signature rejected")
        all_entries.extend(collect(rejected))

    write_local_events(all_entries)

    for publish in (send_to_iot_hub, write_to_cosmos):
        try:
            ok, message = publish(all_entries)
        except Exception as exc:
            ok, message = False, f"{publish.__name__} failed: {exc}"
        print(f"{'OK' if ok else 'INFO'}: {message}")

    tamper_count = sum(1 for entry in all_entries if entry.event_type == "TAMPER")
    invalid_count = sum(1 for entry in all_entries if not entry.chain_valid)
    print(f"Generated {len(all_entries)} events.")
    print(f"Tamper events: {tamper_count}")
    print(f"Invalid chain entries: {invalid_count}")


if __name__ == "__main__":
    main()

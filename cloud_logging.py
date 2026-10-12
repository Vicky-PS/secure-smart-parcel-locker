from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Iterable

from dotenv import load_dotenv

from hash_chain import LogEntry


load_dotenv()

DATA_DIR = Path("data")
LOCAL_EVENT_FILE = DATA_DIR / "events.jsonl"


def write_local_events(entries: Iterable[LogEntry]) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    with LOCAL_EVENT_FILE.open("a", encoding="utf-8") as handle:
        for entry in entries:
            handle.write(json.dumps(entry.to_dict(), sort_keys=True) + "\n")


def reset_local_events() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    LOCAL_EVENT_FILE.write_text("", encoding="utf-8")


def read_local_events() -> list[dict]:
    if not LOCAL_EVENT_FILE.exists():
        return []
    events = []
    with LOCAL_EVENT_FILE.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                events.append(json.loads(line))
    return events


def send_to_iot_hub(entries: Iterable[LogEntry]) -> tuple[bool, str]:
    connection_string = os.getenv("IOTHUB_DEVICE_CONNECTION_STRING", "").strip()
    if not connection_string:
        return False, "IoT Hub skipped: IOTHUB_DEVICE_CONNECTION_STRING is empty."

    from azure.iot.device import IoTHubDeviceClient, Message

    client = IoTHubDeviceClient.create_from_connection_string(connection_string)
    try:
        client.connect()
        for entry in entries:
            payload = json.dumps(entry.to_dict(), sort_keys=True)
            message = Message(payload)
            message.content_encoding = "utf-8"
            message.content_type = "application/json;charset=utf-8"
            client.send_message(message)
        return True, "IoT Hub published events successfully."
    finally:
        client.disconnect()


def write_to_cosmos(entries: Iterable[LogEntry]) -> tuple[bool, str]:
    endpoint = os.getenv("COSMOS_ENDPOINT", "").strip()
    key = os.getenv("COSMOS_KEY", "").strip()
    database_name = os.getenv("COSMOS_DATABASE", "smart-locker-db").strip()
    container_name = os.getenv("COSMOS_CONTAINER", "locker-events").strip()

    if not endpoint or not key:
        return False, "Cosmos DB skipped: COSMOS_ENDPOINT or COSMOS_KEY is empty."

    from azure.cosmos import CosmosClient, PartitionKey

    client = CosmosClient(endpoint, credential=key)
    database = client.create_database_if_not_exists(id=database_name)
    container = database.create_container_if_not_exists(
        id=container_name,
        partition_key=PartitionKey(path="/compartment_id"),
    )
    for entry in entries:
        container.upsert_item(entry.to_dict())
    return True, "Cosmos DB stored events successfully."


def read_cosmos_events() -> tuple[list[dict], str]:
    endpoint = os.getenv("COSMOS_ENDPOINT", "").strip()
    key = os.getenv("COSMOS_KEY", "").strip()
    database_name = os.getenv("COSMOS_DATABASE", "smart-locker-db").strip()
    container_name = os.getenv("COSMOS_CONTAINER", "locker-events").strip()

    if not endpoint or not key:
        return read_local_events(), "Showing local events because Cosmos DB is not configured."

    try:
        from azure.cosmos import CosmosClient

        client = CosmosClient(endpoint, credential=key)
        container = client.get_database_client(database_name).get_container_client(container_name)
        query = "SELECT * FROM c ORDER BY c.timestamp DESC"
        events = list(container.query_items(query=query, enable_cross_partition_query=True))
        return events, "Showing events from Cosmos DB."
    except Exception as exc:
        return read_local_events(), f"Cosmos DB unavailable, showing local events instead: {exc}"

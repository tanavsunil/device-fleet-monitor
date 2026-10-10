from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field


app = FastAPI(title="Mini Device Fleet Monitor")

# In-memory storage, keyed by the unique device ID.
devices: dict[str, dict] = {}


class DeviceRegistration(BaseModel):
    """Validate the information supplied when registering a device."""

    id: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=200)


def get_device_status(
    device: dict,
    now: datetime | None = None,
) -> str:
    """Calculate online/offline status from the last heartbeat received."""

    last_seen = device["last_heartbeat_received_at"]

    if last_seen is None:
        return "OFFLINE"

    current_time = now or datetime.now(timezone.utc)
    elapsed = (current_time - last_seen).total_seconds()

    if elapsed <= 30:
        return "ONLINE"

    return "OFFLINE"


def format_device(device: dict) -> dict:
    """Convert an internal device record into an API response."""

    return {
        "id": device["id"],
        "name": device["name"],
        "status": get_device_status(device),
        "last_heartbeat": device["last_heartbeat_received_at"],
    }


@app.post("/devices", status_code=201)
def register_device(payload: DeviceRegistration):
    """Register a new device."""

    if payload.id in devices:
        raise HTTPException(
            status_code=409,
            detail=f"Device '{payload.id}' is already registered.",
        )

    device = {
        "id": payload.id,
        "name": payload.name,
        "registered_at": datetime.now(timezone.utc),
        "last_heartbeat_received_at": None,
        "last_device_timestamp": None,
        "last_reported_status": None,
    }

    devices[payload.id] = device

    return format_device(device)

#

class Heartbeat(BaseModel):
    """Validate heartbeat data sent by a device."""

    timestamp: datetime
    status: str = Field(min_length=1, max_length=50)


@app.post("/devices/{device_id}/heartbeat")
def receive_heartbeat(device_id: str, payload: Heartbeat):
    """Record a heartbeat from a registered device."""

    if device_id not in devices:
        raise HTTPException(
            status_code=404,
            detail=f"Device '{device_id}' is not registered.",
        )

    device = devices[device_id]

    # Use server time for the 30-second timeout.
    device["last_heartbeat_received_at"] = datetime.now(timezone.utc)

    # Preserve the timestamp and status reported by the device.
    device["last_device_timestamp"] = payload.timestamp
    device["last_reported_status"] = payload.status

    return format_device(device)

@app.get("/devices")
def list_devices():
    """List all registered devices with their current status."""

    return [
        format_device(device)
        for device in devices.values()
    ]


@app.get("/devices/{device_id}")
def get_device(device_id: str):
    """Return details for a single registered device."""

    if device_id not in devices:
        raise HTTPException(
            status_code=404,
            detail=f"Device '{device_id}' is not registered.",
        )

    return format_device(devices[device_id])


@app.get("/summary")
def get_summary():
    """Return counts of online and offline devices."""

    statuses = [
        get_device_status(device)
        for device in devices.values()
    ]

    online_count = statuses.count("ONLINE")
    offline_count = statuses.count("OFFLINE")

    return {
        "total": len(devices),
        "online": online_count,
        "offline": offline_count,
    }
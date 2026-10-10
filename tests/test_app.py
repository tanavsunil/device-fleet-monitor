
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

import app as app_module


client = TestClient(app_module.app)


@pytest.fixture(autouse=True)
def reset_devices():
    """Keep tests independent by clearing the in-memory registry."""
    app_module.devices.clear()
    yield
    app_module.devices.clear()


def test_register_device():
    response = client.post(
        "/devices",
        json={"id": "device-01", "name": "Lab Device 01"},
    )

    assert response.status_code == 201
    assert response.json()["id"] == "device-01"
    assert response.json()["status"] == "OFFLINE"
    assert response.json()["last_heartbeat"] is None


def test_duplicate_registration_returns_conflict():
    payload = {"id": "device-01", "name": "Lab Device 01"}

    first = client.post("/devices", json=payload)
    second = client.post("/devices", json=payload)

    assert first.status_code == 201
    assert second.status_code == 409


def test_heartbeat_marks_registered_device_online():
    client.post(
        "/devices",
        json={"id": "device-01", "name": "Lab Device 01"},
    )

    response = client.post(
        "/devices/device-01/heartbeat",
        json={
            "timestamp": "2026-10-10T08:30:00Z",
            "status": "OK",
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "ONLINE"
    assert response.json()["last_heartbeat"] is not None


def test_heartbeat_for_unknown_device_returns_404():
    response = client.post(
        "/devices/unknown-device/heartbeat",
        json={
            "timestamp": "2026-10-10T08:30:00Z",
            "status": "OK",
        },
    )

    assert response.status_code == 404


def test_device_without_heartbeat_is_offline():
    device = {"last_heartbeat_received_at": None}

    assert app_module.get_device_status(device) == "OFFLINE"


def test_device_timeout_boundary():
    last_seen = datetime(
        2026, 10, 10, 12, 0, 0, tzinfo=timezone.utc
    )
    device = {"last_heartbeat_received_at": last_seen}

    # Exactly 30 seconds old: still online.
    assert app_module.get_device_status(
        device, now=last_seen + timedelta(seconds=30)
    ) == "ONLINE"

    # More than 30 seconds old: offline.
    assert app_module.get_device_status(
        device, now=last_seen + timedelta(seconds=31)
    ) == "OFFLINE"


def test_summary_counts_devices_correctly():
    client.post(
        "/devices",
        json={"id": "device-01", "name": "Lab Device 01"},
    )

    response = client.get("/summary")

    assert response.status_code == 200
    assert response.json() == {
        "total": 1,
        "online": 0,
        "offline": 1,
    }

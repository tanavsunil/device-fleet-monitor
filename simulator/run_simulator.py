
"""Simulate five devices sending periodic heartbeats to the API."""

from datetime import datetime, timezone
import threading

import httpx


API_URL = "http://127.0.0.1:8000"
HEARTBEAT_INTERVAL = 5

DEVICE_IDS = [f"sim-device-{number:02d}" for number in range(1, 6)]

shutdown_event = threading.Event()
running_events = {
    device_id: threading.Event() for device_id in DEVICE_IDS
}

# All devices send heartbeats by default.
for event in running_events.values():
    event.set()


def register_devices() -> bool:
    """Register all simulated devices, accepting existing registrations."""

    for device_id in DEVICE_IDS:
        try:
            response = httpx.post(
                f"{API_URL}/devices",
                json={
                    "id": device_id,
                    "name": f"Simulated Device {device_id[-2:]}",
                },
                timeout=5.0,
            )
        except httpx.HTTPError as exc:
            print(f"Could not reach the API: {exc}")
            print("Make sure the API server is running.")
            return False

        if response.status_code == 201:
            print(f"[registered] {device_id}")
        elif response.status_code == 409:
            print(f"[exists] {device_id} is already registered")
        else:
            print(
                f"[error] Registration failed for {device_id}: "
                f"{response.status_code} {response.text}"
            )
            return False

    return True


def heartbeat_loop(device_id: str) -> None:
    """Send heartbeats while this simulator is running."""

    while not shutdown_event.is_set():
        if running_events[device_id].is_set():
            timestamp = datetime.now(timezone.utc).isoformat()

            try:
                response = httpx.post(
                    f"{API_URL}/devices/{device_id}/heartbeat",
                    json={"timestamp": timestamp, "status": "OK"},
                    timeout=5.0,
                )
                response.raise_for_status()
                print(f"[heartbeat] {device_id} -> OK")
            except httpx.HTTPError as exc:
                print(f"[error] Heartbeat failed for {device_id}: {exc}")

        # Wait interruptibly so shutdown does not have to wait five seconds.
        if shutdown_event.wait(HEARTBEAT_INTERVAL):
            break


def show_devices() -> None:
    """Print which simulated devices are sending heartbeats."""

    for device_id, event in running_events.items():
        state = "RUNNING" if event.is_set() else "STOPPED"
        print(f"{device_id}: {state}")


def main() -> None:
    if not register_devices():
        return

    threads = []

    for device_id in DEVICE_IDS:
        thread = threading.Thread(
            target=heartbeat_loop,
            args=(device_id,),
            daemon=True,
        )
        thread.start()
        threads.append(thread)

    print("\nSimulator started. Commands:")
    print("  stop <device-id>   Stop heartbeats from one device")
    print("  start <device-id>  Resume its heartbeats")
    print("  list               Show simulator device states")
    print("  quit               Stop the simulator\n")

    try:
        while True:
            parts = input("> ").strip().lower().split()

            if not parts:
                continue

            if parts[0] in {"stop", "start"} and len(parts) == 2:
                device_id = parts[1]

                if device_id not in running_events:
                    print(f"Unknown simulator device: {device_id}")
                    continue

                if parts[0] == "stop":
                    running_events[device_id].clear()
                    print(
                        f"Stopped {device_id}. It should become OFFLINE "
                        "after 30 seconds without a heartbeat."
                    )
                else:
                    running_events[device_id].set()
                    print(f"Resumed heartbeats for {device_id}.")

            elif parts[0] == "list" and len(parts) == 1:
                show_devices()

            elif parts[0] in {"quit", "exit"} and len(parts) == 1:
                break

            else:
                print("Unknown command. Type 'list', 'stop', 'start', or 'quit'.")

    except (KeyboardInterrupt, EOFError):
        print("\nShutting down simulator...")

    finally:
        shutdown_event.set()

        for thread in threads:
            thread.join(timeout=1.0)

        print("Simulator stopped.")


if __name__ == "__main__":
    main()

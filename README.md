
# Mini Device Fleet Monitor

A lightweight REST API for registering simulated devices, receiving periodic heartbeats, and monitoring the current status of a device fleet.

The application considers a device `ONLINE` if the server received its latest heartbeat within the last 30 seconds. Otherwise, the device is `OFFLINE`.

## Features

- Register devices with unique IDs.
- Receive and record heartbeats from registered devices.
- List all devices with their current status.
- Retrieve details for an individual device.
- Summarize total, online, and offline devices.
- Simulate five devices sending heartbeats every five seconds.
- Stop an individual simulated device and observe its timeout.
- Automated tests for registration, heartbeat handling, error cases, and timeout behaviour.

## Design and Architecture

The application uses Python and FastAPI.

- `app.py` contains the HTTP endpoints, in-memory device registry, input validation, and status calculation.
- `tests/test_app.py` contains automated tests using pytest and FastAPI's TestClient.
- `simulator/run_simulator.py` runs five simulated devices that send heartbeats to the API.
- `requirements.txt` lists the Python dependencies.

The device registry is an in-memory dictionary keyed by device ID. Each device record stores its ID, name, registration time, last server-side heartbeat receipt time, and the latest device-reported timestamp and status.

The API calculates `ONLINE` or `OFFLINE` when a device is returned. This avoids relying on a background job to update stored status values.

The server's heartbeat receipt time is used for timeout calculations rather than trusting the device-provided timestamp.

## Prerequisites

- Python 3.13
- Git
- A terminal capable of running Python commands
- Internet access for installing dependencies

The instructions below use PowerShell on Windows. Equivalent commands can be used on other operating systems.

## Installation

Clone the repository and enter its directory:

```powershell
git clone https://github.com/tanavsunil/device-fleet-monitor.git
cd device-fleet-monitor
```

Create a virtual environment:

```powershell
python -m venv .venv
```

Activate it in Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install the dependencies:

```powershell
python -m pip install -r requirements.txt
```

If PowerShell reports that it cannot find Python, verify that Python is installed and available on your PATH.

## Run the Application

From the project root, activate the virtual environment and run:

```powershell
python -m uvicorn app:app --reload
```

The API will be available at:

- Base URL: http://127.0.0.1:8000
- Interactive API documentation: http://127.0.0.1:8000/docs

Keep this terminal running while using the API or simulator.

## Run the Simulator

Open a second terminal in the project root. Activate the virtual environment if necessary, then run:

```powershell
python simulator/run_simulator.py
```

The simulator registers five devices and starts sending heartbeats every five seconds.


Supported interactive commands:

```text
list
stop sim-device-03
start sim-device-03
quit
```


`list` shows which simulated devices are sending heartbeats.

`stop sim-device-03` stops heartbeats from that device. After more than 30 seconds without another heartbeat, the API should report it as `OFFLINE`, while the other devices remain `ONLINE`.

`start sim-device-03` resumes heartbeats.

`quit` shuts down the simulator.

The API server must remain running for the simulator to communicate with it.

## Run the Tests

From the project root, with the virtual environment activated, run:

```powershell
python -m pytest -q
```

The tests cover:

- Successful device registration.
- Duplicate device registration.
- Heartbeat handling.
- Heartbeats from unknown devices.
- Devices without heartbeats.
- The exact 30-second timeout boundary.
- Fleet summary counts.

The timeout boundary is tested using controlled timestamps, so the automated test suite does not need to wait 30 seconds.

## API Endpoints

### Register a Device

`POST /devices`

Request:

```json
{
  "id": "device-01",
  "name": "Lab Device 01"
}
```

Returns `201 Created` on success and `409 Conflict` if the ID is already registered.

### Receive a Heartbeat

`POST /devices/{device_id}/heartbeat`

Request:

```json
{
  "timestamp": "2026-10-10T10:30:00Z",
  "status": "OK"
}
```

Returns `200 OK` when the registered device's heartbeat is accepted and `404 Not Found` if the device does not exist.

The server records its own receipt time for timeout calculations.

### List Devices

`GET /devices`

Returns an array containing the registered devices and their current statuses. An empty registry returns an empty array.

### Get Device Details

`GET /devices/{device_id}`

Returns the details and current status of the requested device, or `404 Not Found` if the device is not registered.

### Get Fleet Summary

`GET /summary`

Example response:

```json
{
  "total": 5,
  "online": 4,
  "offline": 1
}
```

The following invariant should always hold:

`total = online + offline`

## Device Status Rules

- A device with no received heartbeat is `OFFLINE`.
- A device whose latest heartbeat was received no more than 30 seconds ago is `ONLINE`.
- A device whose latest heartbeat was received more than 30 seconds ago is `OFFLINE`.

The 30-second boundary is inclusive: exactly 30 seconds is still `ONLINE`.

## Assumptions

- Device IDs uniquely identify devices and cannot be registered twice.
- Only registered devices may send heartbeats.
- The server's UTC receipt time is authoritative for timeout calculations.
- The device-provided timestamp and status are retained as reported values.
- Device connectivity (`ONLINE`/`OFFLINE`) is separate from the device-reported health status.
- The application is designed for a local demonstration with a small simulated fleet.

## Known Limitations

- Device records are stored in memory and are lost when the server restarts.
- The implementation is intended for a single application process.
- Authentication and authorization are not implemented.
- The application has no persistent database.
- The API has no production monitoring, alerting, or rate limiting.

## Improvements With One Additional Day

- Add SQLite or PostgreSQL persistence.
- Add integration tests for a longer-running simulator session and timeout transitions.
- Improve structured logging and application observability.
- Add configuration for the heartbeat timeout and simulator interval.
- Review concurrency behaviour and support multiple application workers safely.
- Add authentication and basic operational security controls.

## AI Usage

**Tool used:** ChatGPT.

**How it was used:** ChatGPT helped plan the application architecture, explain FastAPI and Git concepts, develop the API and test structure, and troubleshoot the Python dependency installation issue.

**Generated code improved:** I extended the heartbeat timeout test to check three cases: 29 seconds (ONLINE), exactly 30 seconds (ONLINE), and 31 seconds (OFFLINE). This explicitly verifies the timeout boundary specified in the requirements. This was a manual change made in order to verify that the 30 second timeframe condition was met.

**Personal verification:** I ran the automated test suite and confirmed that all seven tests passed. I also exercised the API through FastAPI's interactive documentation and tested the simulator by stopping one device and verifying that it became OFFLINE while the other four remained ONLINE.

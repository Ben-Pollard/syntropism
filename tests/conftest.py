import socket
import subprocess
import time

import pytest


def is_service_ready(host="localhost", port=4222):
    """Check if a service is responding on the given port."""
    try:
        with socket.create_connection((host, port), timeout=1):
            return True
    except (TimeoutError, ConnectionRefusedError):
        return False


@pytest.fixture(scope="session")
def nats_server():
    """
    Fixture to ensure NATS is running for the duration of the test session.
    Starts NATS using docker-compose if it's not already running.
    """
    nats_url = "nats://localhost:4222"

    # Check if NATS is already running
    if not is_service_ready(port=4222):
        print("\nStarting NATS via docker-compose...")
        subprocess.run(
            ["docker", "compose", "up", "-d", "nats"],
            check=True,
            capture_output=True,
        )

        # Wait for NATS to be ready
        max_retries = 10
        ready = False
        for i in range(max_retries):
            if is_service_ready(port=4222):
                ready = True
                break
            print(f"Waiting for NATS... (attempt {i + 1}/{max_retries})")
            time.sleep(1)

        if not ready:
            pytest.fail("NATS failed to start within the timeout period.")

    yield nats_url


@pytest.fixture(scope="session", autouse=True)
def otel_collector():
    """
    Fixture to ensure OTel Collector and Phoenix are running.
    """
    # Check if OTel Collector is already running (default port 4317)
    if not is_service_ready(port=4317):
        print("\nStarting OTel Collector and Phoenix via docker-compose...")
        subprocess.run(
            ["docker", "compose", "up", "-d", "otel-collector", "phoenix"],
            check=True,
            capture_output=True,
        )

        # Wait for Collector to be ready
        max_retries = 10
        ready = False
        for i in range(max_retries):
            if is_service_ready(port=4317):
                ready = True
                break
            print(f"Waiting for OTel Collector... (attempt {i + 1}/{max_retries})")
            time.sleep(1)

        if not ready:
            print("Warning: OTel Collector failed to start. Tests may be slow due to timeouts.")

    yield

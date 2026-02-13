import socket
import subprocess
import time

import pytest


def is_nats_ready(host="localhost", port=4222):
    """Check if NATS is responding on the given port."""
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
    if not is_nats_ready():
        print("\nStarting NATS via docker-compose...")
        subprocess.run(
            ["docker", "compose", "-f", "docker-compose.nats.yml", "up", "-d", "nats"],
            check=True,
            capture_output=True,
        )

        # Wait for NATS to be ready
        max_retries = 10
        ready = False
        for i in range(max_retries):
            if is_nats_ready():
                ready = True
                break
            print(f"Waiting for NATS... (attempt {i+1}/{max_retries})")
            time.sleep(1)

        if not ready:
            pytest.fail("NATS failed to start within the timeout period.")

    yield nats_url

    # We leave NATS running to avoid the overhead of restarting it for every test run,
    # but you could add cleanup here if desired:
    # subprocess.run(["docker-compose", "-f", "docker-compose.nats.yml", "stop", "nats"])

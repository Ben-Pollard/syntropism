import json
import os

import docker

from syntropism.domain.models import ResourceBundle

# Determine the project root (where syntropism/ is located)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class ExecutionSandbox:
    def __init__(self, image="bp-agent-runner:latest", system_service_url=None, debug=False):
        self.client = docker.from_env()
        self.image = image
        # Default to host.docker.internal for Linux/Mac to access host API
        if system_service_url is None:
            system_service_url = os.getenv("SYSTEM_SERVICE_URL", "http://host.docker.internal:8000")
        self.system_service_url = system_service_url
        self.debug = debug

    def run_agent(self, agent_id: str, workspace_path: str, resource_bundle: ResourceBundle, runtime_data: dict = None):
        """
        Runs an agent in a Docker container with specified resource limits.
        """
        # Convert memory_mb to Docker format (e.g., "512m")
        mem_limit = f"{int(resource_bundle.memory_mb)}m"

        # Convert cpu_seconds to cpu_period and cpu_quota
        # Default period is 100,000 (100ms)
        cpu_period = 100000
        cpu_quota = int(resource_bundle.cpu_seconds * cpu_period)

        if runtime_data:
            env_json_path = os.path.join(workspace_path, "env.json")
            with open(env_json_path, "w") as f:
                json.dump(runtime_data, f, indent=2)

        environment = {
            "AGENT_ID": agent_id,
            "SYSTEM_SERVICE_URL": self.system_service_url,
            "NATS_URL": os.getenv("NATS_URL", "nats://host.docker.internal:4222"),
            "PYTHONPATH": "/system:$PYTHONPATH",  # Ensure /system is in path
        }

        if runtime_data and "execution_id" in runtime_data:
            environment["EXECUTION_ID"] = str(runtime_data["execution_id"])

        # Enable debug mode if requested
        if self.debug:
            environment["DEBUG"] = "1"
            environment["DEBUGPY_ENABLE"] = "1"

        # Mount workspace and system contracts
        # project_root is mounted read-only so agents can import contracts but not modify system code
        volumes = {
            workspace_path: {"bind": "/workspace", "mode": "rw"},
            PROJECT_ROOT: {"bind": "/system", "mode": "ro"},
        }

        container = None
        try:
            container = self.client.containers.run(
                self.image,
                detach=True,
                environment=environment,
                volumes=volumes,
                mem_limit=mem_limit,
                cpu_period=cpu_period,
                cpu_quota=cpu_quota,
                working_dir="/workspace",
                extra_hosts={"host.docker.internal": "host-gateway"},
            )

            # Wait for completion with timeout
            result = container.wait(timeout=resource_bundle.cpu_seconds)
            exit_code = result.get("StatusCode", 1)
            logs = container.logs().decode("utf-8")
        except Exception as e:
            exit_code = 1
            logs = str(e)
            if container:
                try:
                    logs = container.logs().decode("utf-8") + "\n" + logs
                except Exception:
                    pass
        finally:
            if container:
                container.remove(force=True)

        return exit_code, logs

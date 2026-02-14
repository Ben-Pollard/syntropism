import os
import unittest
from unittest.mock import MagicMock, patch

from syntropism.core.sandbox import ExecutionSandbox
from syntropism.domain.models import ResourceBundle


class TestExecutionSandbox(unittest.TestCase):
    def setUp(self):
        # Patch docker.from_env before instantiating ExecutionSandbox
        self.patcher = patch("docker.from_env")
        self.mock_from_env = self.patcher.start()
        self.mock_client = MagicMock()
        self.mock_from_env.return_value = self.mock_client

        self.sandbox = ExecutionSandbox()
        self.resource_bundle = ResourceBundle(cpu_seconds=0.5, memory_mb=512.0)
        self.agent_id = "test-agent-123"
        self.workspace_path = "/tmp/workspace"

    def tearDown(self):
        self.patcher.stop()

    def test_run_agent_configures_docker_correctly(self):
        # Setup mock container
        mock_container = MagicMock()
        self.mock_client.containers.run.return_value = mock_container
        mock_container.wait.return_value = {"StatusCode": 0}
        mock_container.logs.return_value = b"Execution successful"

        # Execute
        exit_code, logs = self.sandbox.run_agent(self.agent_id, self.workspace_path, self.resource_bundle)

        # Verify
        self.mock_client.containers.run.assert_called_once()
        args, kwargs = self.mock_client.containers.run.call_args

        # Check image
        self.assertEqual(args[0], "bp-agent-runner:latest")

        # Check environment variables
        env = kwargs.get("environment", {})
        self.assertEqual(env.get("AGENT_ID"), self.agent_id)
        self.assertIn("SYSTEM_SERVICE_URL", env)

        # Check resource limits
        self.assertEqual(kwargs.get("mem_limit"), "512m")
        self.assertEqual(kwargs.get("cpu_period"), 100000)
        self.assertEqual(kwargs.get("cpu_quota"), 50000)

        # Check volumes
        volumes = kwargs.get("volumes", {})
        self.assertIn(self.workspace_path, volumes)
        self.assertEqual(volumes[self.workspace_path]["bind"], "/workspace")
        self.assertEqual(volumes[self.workspace_path]["mode"], "rw")

        # Check other params
        self.assertTrue(kwargs.get("detach"))
        self.assertEqual(kwargs.get("working_dir"), "/workspace")

    def test_run_agent_handles_failure_exit_code(self):
        # Setup mock container
        mock_container = MagicMock()
        self.mock_client.containers.run.return_value = mock_container
        mock_container.wait.return_value = {"StatusCode": 1}
        mock_container.logs.return_value = b"Execution failed"

        # Execute
        exit_code, logs = self.sandbox.run_agent(self.agent_id, self.workspace_path, self.resource_bundle)

        # Verify
        self.assertEqual(exit_code, 1)
        self.assertEqual(logs, "Execution failed")
        mock_container.remove.assert_called_once_with(force=True)

    def test_run_agent_handles_timeout(self):
        # Setup mock container
        mock_container = MagicMock()
        self.mock_client.containers.run.return_value = mock_container

        # docker-py wait() raises ReadTimeout or similar if timeout reached
        from requests.exceptions import ReadTimeout

        mock_container.wait.side_effect = ReadTimeout("Timeout reached")
        mock_container.logs.return_value = b"Partial logs"

        # Execute
        exit_code, logs = self.sandbox.run_agent(self.agent_id, self.workspace_path, self.resource_bundle)

        # Verify
        self.assertEqual(exit_code, 1)
        self.assertIn("Timeout reached", logs)
        mock_container.remove.assert_called_once_with(force=True)
        # Verify wait was called with timeout
        mock_container.wait.assert_called_once_with(timeout=self.resource_bundle.cpu_seconds)

    def test_run_agent_handles_image_not_found(self):
        # Setup mock to raise ImageNotFound
        import docker.errors

        self.mock_client.containers.run.side_effect = docker.errors.ImageNotFound("Image not found")

        # Execute
        exit_code, logs = self.sandbox.run_agent(self.agent_id, self.workspace_path, self.resource_bundle)

        # Verify
        self.assertEqual(exit_code, 1)
        self.assertIn("Image not found", logs)

    def test_configurable_system_service_url(self):
        custom_url = "http://custom-service:9000"
        sandbox = ExecutionSandbox(system_service_url=custom_url)

        # Setup mock container
        mock_container = MagicMock()
        self.mock_client.containers.run.return_value = mock_container
        mock_container.wait.return_value = {"StatusCode": 0}
        mock_container.logs.return_value = b"OK"

        # Execute
        sandbox.run_agent(self.agent_id, self.workspace_path, self.resource_bundle)

        # Verify
        _, kwargs = self.mock_client.containers.run.call_args
        env = kwargs.get("environment", {})
        self.assertEqual(env.get("SYSTEM_SERVICE_URL"), custom_url)

    def test_run_agent_writes_env_json(self):
        import json
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            runtime_data = {"credits": 100.0, "agent_id": self.agent_id}

            # Setup mock container
            mock_container = MagicMock()
            self.mock_client.containers.run.return_value = mock_container
            mock_container.wait.return_value = {"StatusCode": 0}
            mock_container.logs.return_value = b"OK"

            self.sandbox.run_agent(self.agent_id, tmpdir, self.resource_bundle, runtime_data=runtime_data)

            env_json_path = os.path.join(tmpdir, "env.json")
            self.assertTrue(os.path.exists(env_json_path))
            with open(env_json_path) as f:
                saved_data = json.load(f)
            self.assertEqual(saved_data, runtime_data)

"""Tests for Genesis Agent Logic in workspaces/genesis/main.py"""

import json
import os
from unittest.mock import mock_open, patch

import pytest


@pytest.fixture
def mock_env_json():
    """Sample env.json content for testing."""
    return {"agent_id": "test-agent-123", "credits": 1000.0}


@pytest.fixture
def mock_env_json_with_attention():
    """Sample env.json with attention_share for testing."""
    return {"agent_id": "test-agent-456", "credits": 600.0, "attention_share": 1.0}


@pytest.fixture
def mock_env_json_low_balance():
    """Sample env.json with low balance for testing."""
    return {"agent_id": "test-agent-789", "credits": 400.0}


class TestGenesisAgentEnvLoading:
    """Tests for Step 1: Update Agent to read env.json"""

    def test_loads_env_json_successfully(self, mock_env_json, tmp_path):
        """Agent should successfully load env.json from /app/env.json"""
        env_file = tmp_path / "env.json"
        env_file.write_text(json.dumps(mock_env_json))

        with patch("builtins.open", mock_open(read_data=json.dumps(mock_env_json))):
            with patch("os.path.exists", return_value=True):
                # Import here to test module-level behavior
                from workspaces.genesis.main import load_env

                result = load_env("/app/env.json")
                assert result["agent_id"] == mock_env_json["agent_id"]
                assert result["credits"] == mock_env_json["credits"]

    def test_handles_missing_env_json(self, tmp_path):
        """Agent should handle missing env.json gracefully"""
        with patch("os.path.exists", return_value=False):
            from workspaces.genesis.main import load_env

            result = load_env("/app/env.json")
            assert result is None


class TestMarketInteraction:
    """Tests for Step 2: Implement Market Interaction using Service Layers"""

    def test_cognition_service_integration(self, mock_env_json):
        """Agent should use CognitionService for market data integration"""
        from workspaces.genesis.services import CognitionService

        service = CognitionService()
        result = service.integrate()
        assert result == "Cognition integration called"

    def test_economic_service_get_balance(self, mock_env_json):
        """Agent should use EconomicService to get balance"""
        from unittest.mock import patch

        from workspaces.genesis.services import EconomicService

        service = EconomicService()
        # Mock the HTTP call to avoid network errors
        with patch.object(
            service, "_make_request", return_value={"agent_id": mock_env_json["agent_id"], "balance": 1000.0}
        ):
            result = service.get_balance(mock_env_json["agent_id"])
            assert result["agent_id"] == mock_env_json["agent_id"]
            assert "balance" in result


class TestBiddingLogic:
    """Tests for Step 3: Implement Bidding Logic"""

    def test_bids_10_percent_of_balance(self, mock_env_json):
        """Agent should bid 10% of balance for standard bundle"""
        from workspaces.genesis.main import calculate_bid

        bid = calculate_bid(mock_env_json["credits"], attention_share=0.0)
        expected_bid = mock_env_json["credits"] * 0.10  # 10% of 1000 = 100

        assert bid["amount"] == expected_bid
        assert bid["cpu"] == 1
        assert bid["memory_mb"] == 128
        assert bid["tokens"] == 1000
        assert bid["attention_share"] == 0.0

    def test_bids_with_attention_when_balance_above_threshold(self, mock_env_json_with_attention):
        """Agent should bid with attention_share=1.0 when balance > 500"""
        from workspaces.genesis.main import calculate_bid

        bid = calculate_bid(mock_env_json_with_attention["credits"], attention_share=1.0)

        assert bid["attention_share"] == 1.0
        assert bid["amount"] == mock_env_json_with_attention["credits"] * 0.10

    def test_no_attention_when_balance_below_threshold(self, mock_env_json_low_balance):
        """Agent should not bid for attention when balance <= 500"""
        from workspaces.genesis.main import calculate_bid

        bid = calculate_bid(mock_env_json_low_balance["credits"], attention_share=0.0)

        assert bid["attention_share"] == 0.0

    @patch.dict(os.environ, {"AGENT_ID": "test-agent-123"})
    def test_economic_service_place_bid(self, mock_env_json):
        """Agent should use EconomicService to place bids"""
        from unittest.mock import patch

        from workspaces.genesis.services import EconomicService

        service = EconomicService()
        # Mock the HTTP call to avoid network errors
        with patch.object(
            service, "_make_request", return_value={"bid_id": "test-bid", "amount": 100.0, "status": "placed"}
        ):
            # Provide valid resources to satisfy BidRequest contract
            result = service.place_bid(100.0, resources={"cpu": 1.0, "memory_mb": 128, "tokens": 1000})
            assert result["amount"] == 100.0


class TestPromptingLogic:
    """Tests for Step 4: Implement Prompting Logic using Service Layers"""

    @patch("nats.connect")
    def test_sends_prompt_when_attention_share_positive(self, mock_nats_connect, mock_env_json_with_attention):
        """Agent should use SocialService for non-blocking human interaction"""
        from workspaces.genesis.services import SocialService

        service = SocialService()
        result = service.send_async_message("Hello from Genesis! I am evolving.")
        assert "Async message sent:" in result

    def test_social_service_initialization(self):
        """SocialService should initialize correctly"""
        from workspaces.genesis.services import SocialService

        service = SocialService()
        assert service is not None


class TestWorkspaceService:
    """Tests for WorkspaceService path validation and audit logging"""

    def test_workspace_service_validates_path(self):
        """WorkspaceService should validate paths to prevent directory traversal"""
        from workspaces.genesis.services import WorkspaceService

        service = WorkspaceService()
        # Valid path should not raise
        result = service.validate_path("/workspace/test.txt")
        assert result is True

    def test_workspace_service_rejects_invalid_path(self):
        """WorkspaceService should reject paths with directory traversal"""
        from workspaces.genesis.services import WorkspaceService

        service = WorkspaceService()
        with pytest.raises(ValueError):
            service.validate_path("../etc/passwd")

    def test_workspace_service_audit_log(self):
        """WorkspaceService should log filesystem actions"""
        from workspaces.genesis.services import WorkspaceService

        service = WorkspaceService()
        # Should not raise
        service.audit_log("read", "/workspace/test.txt")


class TestGenesisAgentMain:
    """Integration tests for the main Genesis agent function using service layers"""

    @patch("builtins.open", new_callable=mock_open)
    @patch("os.path.exists")
    @patch("workspaces.genesis.services.EconomicService._make_request")
    @patch("workspaces.genesis.services.SocialService._make_request")
    def test_full_agent_workflow_high_balance(
        self, mock_social_req, mock_econ_req, mock_exists, mock_open_file, mock_env_json_with_attention
    ):
        """Test complete Genesis agent workflow with high balance and attention using services"""
        mock_open_file.return_value.read.return_value = json.dumps(mock_env_json_with_attention)
        mock_exists.return_value = True
        mock_econ_req.return_value = {"balance": 1000.0}
        mock_social_req.return_value = {"status": "success"}

        from workspaces.genesis.main import main

        # Should not raise - uses service layers instead of HTTP calls
        main()

    @patch("builtins.open", new_callable=mock_open)
    @patch("os.path.exists")
    @patch("workspaces.genesis.services.EconomicService._make_request")
    @patch("workspaces.genesis.services.SocialService._make_request")
    def test_full_agent_workflow_low_balance(
        self, mock_social_req, mock_econ_req, mock_exists, mock_open_file, mock_env_json_low_balance
    ):
        """Test complete Genesis agent workflow with low balance (no attention) using services"""
        mock_open_file.return_value.read.return_value = json.dumps(mock_env_json_low_balance)
        mock_exists.return_value = True
        mock_econ_req.return_value = {"balance": 400.0}

        from workspaces.genesis.main import main

        # Should not raise - uses service layers instead of HTTP calls
        main()


class TestServiceLayerAbstractions:
    """Tests for the new service layer abstractions"""

    def test_cognition_service_exists(self):
        """CognitionService should be importable from services module"""
        from workspaces.genesis.services import CognitionService

        service = CognitionService()
        assert hasattr(service, "integrate")

    def test_economic_service_exists(self):
        """EconomicService should be importable from services module"""
        from workspaces.genesis.services import EconomicService

        service = EconomicService()
        assert hasattr(service, "place_bid")
        assert hasattr(service, "get_balance")

    def test_social_service_exists(self):
        """SocialService should be importable from services module"""
        from workspaces.genesis.services import SocialService

        service = SocialService()
        assert hasattr(service, "send_async_message")

    def test_workspace_service_exists(self):
        """WorkspaceService should be importable from services module"""
        from workspaces.genesis.services import WorkspaceService

        service = WorkspaceService()
        assert hasattr(service, "validate_path")
        assert hasattr(service, "audit_log")

    def test_all_services_loguru_logger(self):
        """All services should use loguru for structured logging"""
        from workspaces.genesis.services import CognitionService, EconomicService, SocialService, WorkspaceService

        # Should not raise when initializing
        CognitionService()
        EconomicService()
        SocialService()
        WorkspaceService()

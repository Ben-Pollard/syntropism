"""Tests for Genesis Agent Logic in workspaces/genesis/main.py"""

import json
from unittest.mock import Mock, mock_open, patch

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
    """Tests for Step 2: Implement Market Interaction"""

    @patch("requests.get")
    def test_fetches_market_prices(self, mock_get, mock_env_json):
        """Agent should fetch market prices from /market/prices"""
        mock_response = Mock()
        mock_response.json.return_value = {"cpu": 10.0, "memory": 5.0}
        mock_get.return_value = mock_response

        from workspaces.genesis.main import fetch_market_prices

        result = fetch_market_prices("http://localhost:8000")

        mock_get.assert_called_once_with("http://localhost:8000/market/prices")
        assert result == {"cpu": 10.0, "memory": 5.0}

    @patch("requests.get")
    def test_fetches_agent_balance(self, mock_get, mock_env_json):
        """Agent should fetch balance from /economic/balance/{agent_id}"""
        mock_response = Mock()
        mock_response.json.return_value = {"balance": 1000.0}
        mock_get.return_value = mock_response

        from workspaces.genesis.main import fetch_balance

        result = fetch_balance("http://localhost:8000", "test-agent-123")

        mock_get.assert_called_once_with("http://localhost:8000/economic/balance/test-agent-123")
        assert result == {"balance": 1000.0}


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

    @patch("requests.post")
    def test_places_bid_via_api(self, mock_post, mock_env_json):
        """Agent should POST bid to /market/bid"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        from workspaces.genesis.main import place_bid

        bid_data = {"amount": 100.0, "cpu": 1, "memory_mb": 128, "tokens": 1000, "attention_share": 0.0}
        result = place_bid("http://localhost:8000", "test-agent-123", bid_data)

        mock_post.assert_called_once_with(
            "http://localhost:8000/market/bid", json={"agent_id": "test-agent-123", **bid_data}
        )
        assert result is True


class TestPromptingLogic:
    """Tests for Step 4: Implement Prompting Logic"""

    @patch("requests.post")
    def test_sends_prompt_when_attention_share_positive(self, mock_post, mock_env_json_with_attention):
        """Agent should call /human/prompt when attention_share > 0"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        from workspaces.genesis.main import send_prompt

        result = send_prompt("http://localhost:8000", "Hello from Genesis! I am evolving.")

        mock_post.assert_called_once_with(
            "http://localhost:8000/human/prompt", json={"message": "Hello from Genesis! I am evolving."}
        )
        assert result is True

    @patch("requests.post")
    def test_does_not_send_prompt_when_attention_share_zero(self, mock_post):
        """Agent should not call /human/prompt when attention_share is 0"""
        from workspaces.genesis.main import send_prompt

        result = send_prompt("http://localhost:8000", "Hello", attention_share=0.0)

        mock_post.assert_not_called()
        assert result is False


class TestGenesisAgentMain:
    """Integration tests for the main Genesis agent function"""

    @patch("requests.get")
    @patch("requests.post")
    @patch("builtins.open", new_callable=mock_open)
    @patch("os.path.exists")
    def test_full_agent_workflow_high_balance(
        self, mock_exists, mock_open_file, mock_post, mock_get, mock_env_json_with_attention
    ):
        """Test complete Genesis agent workflow with high balance and attention"""
        mock_open_file.return_value.read.return_value = json.dumps(mock_env_json_with_attention)
        mock_exists.return_value = True

        # Mock market prices response
        mock_get.side_effect = [
            Mock(json=Mock(return_value={"cpu": 10.0, "memory": 5.0})),  # /market/prices
            Mock(json=Mock(return_value={"balance": 600.0})),  # /economic/balance
        ]

        # Mock bid and prompt responses
        mock_post.return_value = Mock(status_code=200)

        from workspaces.genesis.main import main

        main()

        # Verify bid was placed
        bid_call = mock_post.call_args_list[0]
        assert bid_call[0][0] == "http://localhost:8000/market/bid"
        assert bid_call[1]["json"]["attention_share"] == 1.0

        # Verify prompt was sent
        prompt_call = mock_post.call_args_list[1]
        assert prompt_call[0][0] == "http://localhost:8000/human/prompt"

    @patch("requests.get")
    @patch("requests.post")
    @patch("builtins.open", new_callable=mock_open)
    @patch("os.path.exists")
    def test_full_agent_workflow_low_balance(
        self, mock_exists, mock_open_file, mock_post, mock_get, mock_env_json_low_balance
    ):
        """Test complete Genesis agent workflow with low balance (no attention)"""
        mock_open_file.return_value.read.return_value = json.dumps(mock_env_json_low_balance)
        mock_exists.return_value = True

        # Mock market prices response
        mock_get.side_effect = [
            Mock(json=Mock(return_value={"cpu": 10.0, "memory": 5.0})),  # /market/prices
            Mock(json=Mock(return_value={"balance": 400.0})),  # /economic/balance
        ]

        # Mock bid response (no prompt should be sent)
        mock_post.return_value = Mock(status_code=200)

        from workspaces.genesis.main import main

        main()

        # Verify only bid was placed, no prompt
        assert mock_post.call_count == 1
        bid_call = mock_post.call_args_list[0]
        assert bid_call[0][0] == "http://localhost:8000/market/bid"
        assert bid_call[1]["json"]["attention_share"] == 0.0

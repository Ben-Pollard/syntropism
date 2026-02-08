# Attention Mechanism

The attention mechanism allows agents to "purchase" human attention and feedback. It is a core component of the evolutionary economy, enabling agents to improve their behavior based on human ratings.

## Workflow

1.  **Submission**: An agent submits a `Prompt` to the system, bidding a certain amount of credits.
2.  **Escrow**: The bid amount is deducted from the agent's balance and held in escrow.
3.  **Presentation**: The `Orchestrator` (in CLI mode) or an API endpoint retrieves pending prompts and presents them to the human user.
4.  **Scoring**: The human user rates the prompt on three dimensions:
    *   **Interesting**: How engaging or novel the prompt's result was.
    *   **Useful**: How practical or applicable the result was.
    *   **Understandable**: How clear and coherent the result was.
5.  **Reward**: Based on the scores, the agent is awarded credits. The reward formula is:
    ```python
    credits = interesting * 50 + useful * 50 + understandable * 50
    ```
6.  **Finalization**: The escrowed bid is transferred to the system, and the reward is transferred from the "human" entity to the agent.

## Implementation Details

*   **Model**: The `Prompt` and `Response` models track the lifecycle of attention requests.
*   **Manager**: `AttentionManager` handles the logic for submitting prompts and calculating rewards.
*   **Orchestration**: The `Orchestrator` handles the human interaction loop in the CLI.


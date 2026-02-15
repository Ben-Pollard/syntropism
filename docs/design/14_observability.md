This design document outlines the transition to an **OpenInference-based observability stack** centered around **Arize Phoenix**. This approach treats LLM agents as distributed systems rather than black-box APIs, ensuring compatibility with your existing NATS and MCP architecture.

---

# Architectural Design: Agentic Observability & Evaluation Stack (2026)

## 1. Executive Summary

To support a high-concurrency, multi-agent system utilizing NATS for inter-service communication and MCP for tool execution, we recommend adopting the **Arize Phoenix** platform powered by **OpenInference (OI)** semantic conventions. This moves beyond generic infrastructure tracing into "Behavioral Tracing," enabling automated evaluation, golden-set curation, and systematic benchmarking without vendor lock-in.

---

## 2. The Recommended Stack

| Component | Technology | Role |
| --- | --- | --- |
| **Instrumentation** | **OpenInference SDKs** | Wraps agents/LLMs to emit structured spans (prompts, tool calls, costs). |
| **Transport** | **OpenTelemetry (OTel)** | The pipe that carries data from NATS agents to the backend. |
| **Trace Backend** | **Arize Phoenix** | Open-source server for trace visualization and embedding analysis. |
| **Evaluation** | **Phoenix Evals** | Automated LLM-as-a-Judge to score traces for hallucination/relevancy. |


---

## 3. Why This Approach?

### A. Standards-Based (The "OpenInference" Advantage)

Generic OTel traces lack the "vocabulary" for agents. OpenInference (OI) provides a standardized schema for attributes like `llm.prompt_template`, `tool.name`, and `retrieval.documents`. By using OI, our instrumentation remains compatible with any OTel-native tool (Langfuse, SigNoz, etc.), effectively "future-proofing" our telemetry.

### B. Solving the NATS "Trace Gap"

In event-driven systems (NATS), traces often break between publisher and subscriber.

* **The Solution:** We utilize OTel **Context Injection/Extraction**. The publisher agent injects the `traceparent` into the NATS message header; the subscriber extracts it to continue the trace tree. Arize Phoenix is specifically optimized to visualize these deeply nested, asynchronous agent loops.

### C. Evaluation-Led Development

Unlike a manual "local runner" script, Phoenix allows us to:

1. **Promote Traces to Datasets:** If an agent fails a specific edge case over NATS, we "promote" that trace to a benchmark dataset with one click.
2. **Continuous Benchmarking:** We run automated "Experiments" where new prompt versions are tested against these datasets, providing side-by-side performance deltas.

---

## 4. Key Architectural "Gotchas"

* **Header Propagation in NATS:** Standard NATS clients do not auto-propagate OTel headers. We must implement a lightweight wrapper for `nc.publish()` and `nc.subscribe()` to handle the `W3C Trace Context`.
* **MCP Protocol Visibility:** The Model Context Protocol (MCP) involves bidirectional state. To avoid "missing spans," we must instrument the **MCP Client** (the agent) rather than just the server, ensuring we capture the *intent* behind the tool call.
* **Storage Scaling:** High-agent-count systems generate 10x more spans than traditional REST APIs. We must configure the **OTel Collector** with `batch` and `tail_sampling` processors to avoid overwhelming the Phoenix instance with noise.
* **Judge Model Latency:** Using "LLM-as-a-Judge" for evaluations adds latency. We recommend running evaluations **asynchronously** (post-hoc) rather than in the critical path of the agent response.

---

## 5. Decision Rationale: Why not the "Manual Stack"?

A manual stack (Jaeger + Prometheus + Grafana) is excellent for identifying *if* a service is down, but it is blind to *why* an agent is hallucinating. Arize Phoenix provides the specialized UI needed for:

* **Embedding Space Visualization:** Identifying clusters of failed queries in RAG.
* **Step-by-Step Logic Trees:** Viewing the agent's "chain of thought" alongside tool outputs.
* **Dataset Management:** Turning logs into a scientific test suite.

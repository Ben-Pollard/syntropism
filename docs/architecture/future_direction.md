# Future Architectural Direction: Observability & Evaluation

## 1. Vision
To establish a world-class observability and evaluation platform for agentic systems, moving from simple logging to **Behavioral Tracing** and **Automated Evaluation**.

## 2. Core Pillars

### A. Unified Dependency Stack
- **Action**: Consolidate all infrastructure (NATS, OTel Collector, Arize Phoenix) into a single `docker-compose.yml`.
- **Rationale**: Simplifies developer onboarding and ensures environment parity.

### B. OpenInference Standardization
- **Action**: Adopt OpenInference semantic conventions for all LLM and tool-calling spans.
- **Rationale**: Enables advanced visualization in Arize Phoenix (e.g., logic trees, cost analysis) and avoids vendor lock-in.

### C. Distributed Trace Continuity
- **Action**: Implement W3C Trace Context propagation across NATS headers.
- **Rationale**: Connects disparate agent actions into a single, coherent trace, essential for debugging asynchronous event-driven loops.

### D. Evaluation-Led Development
- **Action**: Integrate Phoenix Evals into the CI/CD and benchmarking pipeline.
- **Rationale**: Augments manual log inspection with automated "LLM-as-a-Judge" and procedural scoring for hallucination, relevancy, and safety.

## 3. Implementation Roadmap

1.  **Phase 1: Infrastructure (Immediate)**
    - Finalize `docker-compose.yml` with Arize Phoenix and OTel Collector.
    - Configure OTel Collector with `batch` and `memory_limiter` processors.

2.  **Phase 2: Instrumentation (Short-term)**
    - Create a NATS wrapper for trace propagation.
    - Instrument `LLMProxy` and `MCPGateway` with OpenInference.

3.  **Phase 3: Evaluation (Medium-term)**
    - Define "Golden Sets" from production traces.
    - Implement automated experiments in the `BenchmarkRunner`.

## 4. Agreement
*This document represents the agreed-upon direction for the Syntropism observability stack.*

**Status**: Pending Approval

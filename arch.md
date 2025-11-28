1. Overview

The app analyzes a single, sorted log file (~10k+ lines).

Supports entity lookup, root-cause analysis, flow tracing, and pattern detection.

Uses a single hosted Llama 3.2 model via Ollama as the AI brain.

Supports FIND mode (deterministic entity search) and ANALYZE mode (reasoning, correlations, patterns).

All intermediate steps produce structured JSON; final output is human-readable.

2. Components
A. User Interface

Accepts natural language queries.

Returns structured JSON (for iterative processing) or final human-readable explanations.

B. LLM Layer (Ollama-hosted Llama 3.2)

Handles both modes:

FIND / Tool Mode → JSON output for entity extraction.

ANALYZE / Reasoning Mode → JSON observations, correlations, pattern detection.

Mode switching is dynamic and controlled by backend.

C. Backend / Tools

Log Access & Grep Engine

Reads CSV logs line-by-line or in chunks.

Performs regex or string-based extraction for entities.

Filters large log sets to feed only minimal relevant slices to LLM.

Entity Mapping & Normalization

Mapping file: converts user terms → normalized entities.

Normalized schema: defines log keys + relationships for iterative exploration (e.g., CM → MdId → RPD → Package).

Chunking & Filtering

Ensures log slices fit LLM context windows.

Optional pre-filtering by severity, module, or entity.

Iterative Recursion Controller

Maintains a queue/stack of entities to process.

Iteratively:

Pops an entity from queue

Performs FIND/ANALYZE on minimal relevant logs

Extracts next_entities → adds them to queue

Stores intermediate JSON results

Continues until queue is empty.

3. Data Flow

User query → backend maps entity aliases → normalized log keys.

Backend performs initial FIND → identifies relevant logs.

Backend extracts entities → adds next_entities to queue.

While queue is not empty:

Feed minimal relevant logs to LLM with appropriate mode.

LLM outputs JSON: next_entities, observations, mode_suggestion.

Store intermediate JSON results → enqueue new next_entities.

Once queue is empty → aggregate all JSON → generate human-readable explanation.

4. Handling Use Cases

Entity lookup: iterative FIND only.

Root cause analysis: iterative FIND → ANALYZE loops.

Flow for CM/modem: FIND logs → extract related entities → ANALYZE timeline/sequence.

Pattern analysis: ANALYZE mode over filtered chunks → iterative exploration.

Large logs: handled via streaming, chunking, minimal log feeding.

Aliases / inconsistent keys: mapping + normalized schema.

5. Principles

LLM = brain: interprets queries, reasons, outputs structured JSON.

Backend = hands: deterministic search, mapping, chunking, iterative recursion, aggregation.

Structured JSON first: drives recursion, ensures deterministic processing.

Final human-readable output: aggregates all steps for clarity.

Iterative recursion: safer than true recursion for large logs, avoids stack issues.

6. Optional Enhancements

Vector DB for domain knowledge or abbreviations (improves reasoning).

Summarization or reporting layer for final human-readable output (flow diagrams, pattern tables).
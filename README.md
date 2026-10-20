# SupportPilot - AI Support Agent with Escalation, Guardrails, Tracing, and Evals

SupportPilot is an AI customer-support agent built with FastAPI, ChromaDB, and OpenAI-compatible LLMs (e.g., Groq, Gemini, OpenAI).

When a customer submits a question, the agent classifies intent, retrieves grounded knowledge base chunks (RAG), drafts a cited reply in validated structured JSON, and decides **AUTO_ANSWER vs ESCALATE to a human**. Every decision is traced to SQLite and evaluated continuously.

---

## Architecture Diagram (ASCII)

```
                            Customer Message / Slack Mention
                                          │
                                          ▼
                             ┌────────────────────────┐
                             │  Pre-Check Guardrails  │ ──Injection / Money / Legal / "Human"──┐
                             └────────────────────────┘                                        │
                                          │                                                    │
                                          ▼ (pass)                                             │
                             ┌────────────────────────┐                                        │
                             │ ChromaDB Top-k Search  │ ──Best Score < Min Score Threshold─────┤
                             └────────────────────────┘                                        │
                                          │                                                    │
                                          ▼ (pass)                                             │
                             ┌────────────────────────┐                                        │
                             │ LLM Structured Output  │                                        │
                             │ (OpenAI-compatible)    │ ──Bad JSON (retry exhausted) / Err─────┤
                             └────────────────────────┘                                        │
                                          │                                                    │
                                          ▼                                                    │
                             ┌────────────────────────┐                                        │
                             │  Post-Check Guardrails │ ──Needs Human / Bad Citation / Low Conf┤
                             └────────────────────────┘                                        │
                                          │ (all pass)                                         │
                                          ▼                                                    ▼
                             ┌────────────────────────┐                           ┌────────────────────────┐
                             │      AUTO_ANSWER       │                           │        ESCALATE        │
                             │ Grounded, cited reply  │                           │ Ticket created (SQLite)│
                             │   to user / thread     │                           │ Polite handoff message │
                             └────────────────────────┘                           └────────────────────────┘
                                          │                                                    │
                                          └───────────────────────┬────────────────────────────┘
                                                                  ▼
                                                      ┌────────────────────────┐
                                                      │ Request Tracing (store)│
                                                      │ SQLite Traces & Stats  │
                                                      └────────────────────────┘
```

**Core Invariant:** **Fail Safe**. Any uncertainty, injection attempt, high-risk dispute, or runtime error immediately escalates to a human. The bot never guesses or hallucinates answers.

---

## How Guardrails Work

Guardrails operate at three distinct pipeline stages to protect both customer safety and API spend:

1. **Pre-Check (`guardrails.pre_check`)**:
   - Executes regex scanning before any LLM API call.
   - Blocks prompt-injection patterns (`ignore previous instructions`, `reveal system prompt`, `developer mode`, `jailbreak`).
   - Escalates high-risk keywords: payment disputes (`chargeback`, `charged twice`), legal threats (`lawyer`, `lawsuit`, `sue`), security incidents (`hacked`, `breach`), and explicit human requests (`speak with a human`, `manager`).

2. **Retrieval Check (`guardrails.check_retrieval`)**:
   - Compares the top retrieved chunk similarity score against `MIN_RETRIEVAL_SCORE` (default `0.30`).
   - If the knowledge base is empty or the best score falls below threshold, it immediately escalates without invoking the LLM, preventing ungrounded hallucinations on out-of-domain questions.

3. **Post-Check (`guardrails.post_check`)**:
   - Validates model output after structured JSON generation.
   - Escalates if:
     - `decision.needs_human == True`
     - The answer text is empty
     - No citations are provided
     - Any cited chunk ID was fabricated (not in the retrieved context)
     - Model self-reported confidence is below `CONFIDENCE_THRESHOLD` (default `0.70`)

4. **Fail-Safe Exception Handling**:
   - The entire generation block in `core.py` is wrapped in `try/except`. Any network failure, rate limit, or JSON validation error automatically logs `llm_error`, opens an escalation ticket, and provides a courteous customer handoff.

---

## Setup and Running

```bash
# 1. Virtual environment & dependencies
python -m venv .venv
source .venv/bin/activate       # On Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 2. Environment configuration
cp .env.example .env
# Edit .env with your LLM_API_KEY, LLM_BASE_URL, and LLM_MODEL

# 3. Run test suite (100% offline, hash embeddings + fake LLM)
pytest -q

# 4. Start the server
uvicorn app.main:create_app --factory --reload
# Endpoints: http://localhost:8000/docs
# Dashboard: http://localhost:8000/dashboard

# 5. Run the offline evaluation harness
python -m evals.run_eval

# 6. (Optional) Run the Slack Socket Mode Bot
python slack_bot.py
```

---

## Evaluation Results

Tested live on the 25 hand-labeled golden cases (`evals/golden.jsonl`) using Groq `openai/gpt-oss-120b`:

| Metric | Result (Counts) | Percentage | Note |
|---|---|---|---|
| **Action Accuracy** | **25 / 25** | **100.0%** | Correctly chose AUTO_ANSWER vs ESCALATE across all cases |
| **Unsafe Auto-Answer Rate** | **0 / 9** | **0.0%** | Zero high-risk/adversarial cases answered (lower is better) |
| **Escalation Recall** | **9 / 9** | **100.0%** | 100% of cases requiring human attention were caught |
| **Over-Escalation Rate** | **0 / 16** | **0.0%** | Zero answerable questions were unnecessarily escalated |
| **Auto-Answer Precision** | **16 / 16** | **100.0%** | Every auto-answer was appropriate |
| **Citation Hit Rate** | **16 / 16** | **100.0%** | All 16 auto-answered queries cited the ground-truth document |
| **Intent Accuracy** | **17 / 25** | **68.0%** | Pre-check escalations bypass LLM and default to `other` |
| **Latency p50 / p95** | **1534 ms / 3335 ms** | — | Real-world API roundtrip latency |

---

## Limitations

1. **Deterministic Pipeline**: The current agent follows a deterministic DAG (pre-check -> retrieve -> LLM -> post-check) rather than dynamic autonomous tool calling.
2. **Evaluation Dataset Size**: 25 starter cases provide a directional smoke test, but a single edge case alters percentages by 4-11%. A production baseline requires 100+ held-out human-labeled samples.
3. **Single-Turn Context**: Each incoming query is handled independently. Multi-turn conversation state and session history are currently not threaded.
4. **Local SQLite Persistence**: SQLite is used for traces and tickets, suitable for single-node prototypes but requires migration for distributed clusters.

---

## What I Would Do Next

1. **LLM-Driven Tool Calling**: Migrate from deterministic orchestration to LLM function calling with tools (`search_kb`, `lookup_order`, `check_account_status`, `create_ticket`), allowing multi-step reasoning.
2. **Per-Tenant Knowledge Bases**: Add tenant scoping (`tenant_id` metadata filtering in ChromaDB / pgvector) so enterprise customers can query private docs.
3. **Postgres + Redis Queue**: Decouple incoming requests from LLM generation using background worker queues (Celery / BullMQ / Redis Streams) with transactional PostgreSQL persistence.
4. **Human Feedback Loop**: Expose a UI for human support agents to resolve escalated tickets, correct draft responses, and automatically export approved resolutions back into `golden.jsonl` and fine-tuning datasets.

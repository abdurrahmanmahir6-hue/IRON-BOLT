# Mahir AI OS

**Version:** AR1 (Alpha Release 1) — Sprint 3 (Task 5) in progress
**Status:** Core Engine + OpenAI Provider Layer.

## Project Overview

Mahir AI OS is a modular, provider-agnostic AI Operating System — not a
single chatbot. It's designed around a Router, an Orchestrator, and
(in later sprints) an Agent Layer, a Skill Layer, and a Tool Layer, so
that new AI providers, agents, and tools can be added without
rewriting existing code. This project follows the **MAFS v1.0**
constitution: privacy-first, human-in-the-loop for irreversible
actions, least-privilege by default, and everything logged and
explainable.

## Architecture Diagram

```
User
  │
  ▼
Router          (core/router.py)      — keyword → agent_id
  │
  ▼
Orchestrator    (core/orchestrator.py) — wires Config/State/Router together
  │
  ├──▶ Provider Layer (providers/)     — OpenAI, Gemini, etc. (Sprint 3)
  ├──▶ Agent Layer   (Sprint 3+, not implemented)
  └──▶ Tool Layer    (behind the ToolDispatcher interface, not implemented)
  │
  ▼
Output
```

Supporting modules:
- `core/config.py` — loads and validates configuration from `.env`.
- `core/state.py` — in-memory session/task state (no persistence yet).
- `core/logger.py` — central logging, console + optional rotating file, optional JSON output.
- `core/interfaces.py` — abstract contracts (`ToolDispatcher`) for layers that don't exist yet.
- `core/startup_validation.py` — validates environment and API keys at startup.

## Folder Structure

```
mahir-ai-os/
├── core/
│   ├── __init__.py
│   ├── config.py
│   ├── state.py
│   ├── logger.py
│   ├── router.py
│   ├── orchestrator.py
│   ├── interfaces.py
│   └── startup_validation.py
├── providers/
│   ├── __init__.py
│   ├── base_provider.py
│   ├── openai_provider.py
│   ├── provider_manager.py
│   ├── registry.py
│   └── exceptions.py
├── tests/
│   ├── __init__.py
│   ├── test_config.py
│   ├── test_state.py
│   ├── test_router.py
│   ├── test_orchestrator.py
│   ├── test_logger.py
│   ├── test_startup_validation.py
│   ├── test_provider_runtime_config.py
│   └── test_openai_provider.py
├── main.py
├── requirements.txt
├── .gitignore
├── .env.example
├── README.md
└── sprint3.md
```

## Installation

```bash
git clone <your-repo-url>
cd mahir-ai-os
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # then fill in any keys you already have
```

## How to Run

```bash
python main.py
```

## Running tests

```bash
pytest -v
```

## Sprint Roadmap

| Sprint | Focus | Adds |
|---|---|---|
| 1 | Project Skeleton | repo, venv, base folders |
| 2 | Core Engine | `config.py`, `state.py`, `logger.py`, `router.py`, `orchestrator.py` |
| **3** | **Provider Layer** | `providers/` (OpenAI, Gemini), `startup_validation.py`, `pydantic` — **in progress** |
| 4 | Memory | SQLite-backed persistence for `AppState` |
| 5 | Agent Layer | First real AI agent implementation |
| 6 | Tool Layer | TAVILY, Google Search, and Python Interpreter |

## Environment Variables

Defined in `.env` (see `.env.example`):

| Variable | Description |
|---|---|
| `OPENAI_API_KEY` | Required for OpenAI Provider |
| `MODEL_NAME` | Default model (e.g., `gpt-5.5`) |
| `ACTIVE_PROVIDER` | Current active provider (e.g., `openai`) |

Secrets are never logged in plain text — `Config.masked_summary()` only
reports whether a key is set and its length.

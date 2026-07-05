# Mahir AI OS

**Version:** AR1 (Alpha Release 1) — Sprint 2 complete
**Status:** Core Engine only. No AI provider is called yet.

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
│   └── interfaces.py
├── tests/
│   ├── __init__.py
│   ├── test_config.py
│   ├── test_state.py
│   ├── test_router.py
│   ├── test_orchestrator.py
│   └── test_logger.py
├── main.py
├── requirements.txt
├── .gitignore
├── .env.example
└── README.md
```

> Folders from the original Sprint 1 skeleton that aren't in this
> deliverable yet — `agents/`, `skills/`, `tools/`, `memory/`,
> `database/`, `configs/`, `prompts/`, `docs/` — are intentionally
> absent. Each is created in the sprint that first needs it (see
> **Sprint Roadmap** below), so the repo never carries empty,
> speculative folders.

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

This prints a startup banner confirming every core module initialized,
then drops into an interactive prompt:

```
You: please fix this python bug
[coding_agent] [Sprint 2 placeholder] Input would be handled by 'coding_agent'. No Agent Layer exists yet.

You: exit
Exiting.
```

Type `exit`, `quit`, or `q` to stop (Ctrl+C / Ctrl+D also exit cleanly).

### Running tests

No third-party test framework is required:

```bash
python -m unittest discover -s tests -v
```

(If you have `pytest` installed, `pytest` also works — it auto-discovers these same tests.)

## Sprint Roadmap

| Sprint | Focus | Adds |
|---|---|---|
| 1 | Project Skeleton | repo, venv, base folders |
| **2** | **Core Engine** | `config.py`, `state.py`, `logger.py`, `router.py`, `orchestrator.py` — **done** |
| 3 | Configuration | real `.env` key loading, `pydantic` |
| 4 | Provider Layer | `providers/` (OpenAI, Gemini, base interface), `openai`, `google-genai`, `tavily-python` |
| 5 | Memory | SQLite-backed persistence for `AppState` |
| 6 | First AI | `python main.py` gets a real model reply |

Rule carried through every sprint: **the project must run at the end
of each sprint, even with few features. A broken project doesn't ship.**

## Environment Variables

Defined in `.env` (see `.env.example`); none are required for Sprint 2 to run:

| Variable | Used by | Required in Sprint 2? |
|---|---|---|
| `APP_NAME`, `APP_VERSION`, `ENVIRONMENT`, `LOG_LEVEL` | `core/config.py` | No — all have defaults |
| `OPENAI_API_KEY` | Sprint 4 Provider Layer | No |
| `GEMINI_API_KEY` | Sprint 4 Provider Layer | No |
| `TAVILY_API_KEY` | Sprint 4 Tool Layer | No |

Secrets are never logged in plain text — `Config.masked_summary()` only
reports whether a key is set and its length.

## Example Output

```
========================================
Mahir AI OS
Version AR1
Core Loaded
Configuration Loaded
Logger Ready
State Ready
Router Ready
Orchestrator Ready
System Initialized Successfully
========================================
Type a message and press Enter. Type 'exit' to quit.

You: look up the latest research papers
[research_agent] [Sprint 2 placeholder] Input would be handled by 'research_agent'. No Agent Layer exists yet.
```

## Known Limitations (tracked, not hidden)

- **Router is keyword-based, not an intent classifier.** Word-boundary
  matching (Sprint 2 fix) stops fragment false positives like "code"
  matching inside "encode"/"barcode". It does **not** resolve
  same-word-different-meaning cases (e.g. "what's my zip code" still
  matches the literal word "code"). A real tokenizer/intent classifier
  is planned for Sprint 3.
- **No Agent or Tool Layer yet.** `Orchestrator._dispatch_to_agent` and
  `_dispatch_to_tool` are documented seams, not implementations.
- **No persistence.** `AppState` lives only in memory for the current
  process; Sprint 5 adds SQLite-backed storage.

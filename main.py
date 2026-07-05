"""
main.py

Entry point for Mahir AI OS.

Sprint 2 scope:
    - Wires together Config, Logger, State, Router, and Orchestrator.
    - Prints a startup banner confirming every core module initialized.
    - Does NOT call any AI provider (that begins in Sprint 6).
"""

from __future__ import annotations

import uuid

from core.config import Config, ConfigError
from core.logger import configure_logging, get_logger
from core.orchestrator import Orchestrator
from core.state import AppState

BANNER_WIDTH = 40
EXIT_COMMANDS = {"exit", "quit", "q"}


def print_banner(config: Config) -> None:
    """Print the Sprint 2 startup banner."""
    line = "=" * BANNER_WIDTH
    print(line)
    print("Mahir AI OS")
    print(f"Version {config.app_version}")
    print("Core Loaded")
    print("Configuration Loaded")
    print("Logger Ready")
    print("State Ready")
    print("Router Ready")
    print("Orchestrator Ready")
    print("System Initialized Successfully")
    print(line)


def run_repl(orchestrator: Orchestrator, logger) -> None:
    """
    Interactive read-eval-print loop over the Orchestrator.

    Args:
        orchestrator: A ready-to-use Orchestrator instance.
        logger: Logger used to record each turn for the audit trail.

    Type "exit", "quit", or "q" to stop. Ctrl+C / Ctrl+D also exit
    cleanly instead of crashing with a traceback.
    """
    print("Type a message and press Enter. Type 'exit' to quit.\n")
    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            break

        if not user_input:
            continue
        if user_input.lower() in EXIT_COMMANDS:
            print("Exiting.")
            break

        result = orchestrator.process_input(user_input)
        logger.info("process_input(%r) -> %s", user_input, result)
        print(f"[{result.agent_id}] {result.message}\n")


def main() -> None:
    """Initialize the core system and confirm it runs end-to-end."""
    config = Config.load()

    try:
        # Non-strict: Sprint 2 makes no provider calls, so missing
        # provider keys must not block startup. Sprint 4+ should use
        # config.validate(strict=True) right before a live call.
        config.validate(strict=False)
    except ConfigError as exc:
        # Fail loudly and immediately rather than limping along with
        # bad config (MAFS Ch.2: Truth Over Flattery).
        print(f"Configuration error: {exc}")
        raise SystemExit(1) from exc

    configure_logging(level=config.log_level)
    logger = get_logger(__name__)
    logger.debug("Loaded config: %s", config.masked_summary())

    state = AppState()
    state.start_session(session_id=str(uuid.uuid4()))

    orchestrator = Orchestrator(config=config, state=state)

    print_banner(config)
    run_repl(orchestrator, logger)


if __name__ == "__main__":
    main()

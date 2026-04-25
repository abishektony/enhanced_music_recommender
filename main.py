"""Project entrypoint that forwards to the agentic CLI in src.main."""

from src.main import main as run_agentic_main


def main() -> None:
    run_agentic_main()


if __name__ == "__main__":
    main()

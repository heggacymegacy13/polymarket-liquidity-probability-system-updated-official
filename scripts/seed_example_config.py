from __future__ import annotations

from pathlib import Path

import yaml


def main() -> None:
    output_dir = Path("./config")
    output_dir.mkdir(parents=True, exist_ok=True)

    from polymarket_bot.interfaces.cli import init_config as cli_init_config

    # Reuse CLI logic.
    cli_init_config.callback(output_dir=output_dir)  # type: ignore[attr-defined]


if __name__ == "__main__":
    main()


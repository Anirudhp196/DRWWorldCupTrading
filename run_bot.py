#!/usr/bin/env python3
"""Run the Call Your Shot bot across all three markets (binary, points, goals).

Usage:
    python run_bot.py                  # LIVE trading
    python run_bot.py --dry-run        # simulate, log intended orders only
    python run_bot.py --dry-run --cycles 5 --interval 3
"""

from __future__ import annotations

import argparse
import asyncio
import logging

from bot import run_all_bots, run_dry_run
from config import load_settings


def main() -> None:
    parser = argparse.ArgumentParser(description="Call Your Shot trading bot")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Log the orders the bot would place without sending them.",
    )
    parser.add_argument(
        "--cycles",
        type=int,
        default=3,
        help="Number of dry-run cycles to observe (default: 3).",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=4.0,
        help="Seconds between dry-run cycles (default: 4).",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show DEBUG-level per-order logging in live mode.",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    # Quiet noisy websocket/library logs.
    logging.getLogger("aiohttp").setLevel(logging.WARNING)

    settings = load_settings()

    if args.dry_run:
        asyncio.run(
            run_dry_run(settings, cycles=args.cycles, interval=args.interval)
        )
    else:
        asyncio.run(run_all_bots(settings))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Discover live games, account state, and model fair values vs market."""

from __future__ import annotations

import asyncio
import json
from typing import Any

import aiohttp

from config import load_settings
from fair_value import FairValueEngine
from trading_client import _build_order_books


async def _get_json(session: aiohttp.ClientSession, url: str, token: str) -> Any:
    headers = {"Authorization": f"Bearer {token}"}
    async with session.get(url, headers=headers, ssl=False) as response:
        response.raise_for_status()
        return await response.json()


def _mid(ob) -> float | None:
    if ob.best_bid_px is None or ob.best_ask_px is None:
        return None
    return (ob.best_bid_px + ob.best_ask_px) / 2


async def main() -> None:
    settings = load_settings()
    base = settings.base_url.rstrip("/")
    api = f"{base}/api/games/trading-simulator"

    engine = FairValueEngine(simulations=settings.simulations)
    book = engine.refresh_sync()

    async with aiohttp.ClientSession() as session:
        games = await _get_json(session, api, settings.token)
        print("=== Live games ===")
        print(json.dumps(games, indent=2))

        game_map = {
            settings.game_id_binary: ("binary", book.binary),
            settings.game_id_points: ("points", book.points),
            settings.game_id_goals: ("goals", book.goals),
        }

        for game_id, (label, fair) in game_map.items():
            print(f"\n=== Game {game_id} ({label}) ===")
            try:
                account = await _get_json(session, f"{api}/{game_id}/account", settings.token)
                print(f"Cash: {account.get('cash')}  PnL: {account.get('pnl')}")
                nonzero = {k: v for k, v in account.get("positions", {}).items() if v}
                if nonzero:
                    print(f"Positions: {nonzero}")
            except Exception as exc:
                print(f"Account: {exc}")

            raw = await _get_json(session, f"{api}/{game_id}/orderbooks", settings.token)
            order_books = _build_order_books(raw)

            edges = []
            for symbol, ob in order_books.items():
                fv = fair.get(symbol)
                mid = _mid(ob)
                if fv is None or mid is None:
                    continue
                edges.append((fv - mid, symbol, fv, mid, ob.best_bid_px, ob.best_ask_px))

            edges.sort(key=lambda row: abs(row[0]), reverse=True)
            print("\nTop model vs market gaps (fair - mid):")
            for edge, symbol, fv, mid, bid, ask in edges[:8]:
                print(
                    f"  {symbol:24s} fair={fv:6.2f} mid={mid:6.2f} "
                    f"edge={edge:+6.2f}  bid={bid} ask={ask}"
                )


if __name__ == "__main__":
    asyncio.run(main())

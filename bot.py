"""Async trading bot for all three Call Your Shot markets.

Maximizes PnL by:
1. Running a calibrated Monte Carlo model (50k sims)
2. Comparing fair values to live order book
3. Aggressively taking mispriced liquidity
4. Posting passive quotes to earn spread on medium-edge symbols
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Dict, Set

import aiohttp

from config import Settings
from fair_value import ContractType, FairValueEngine
from strategy import QuoteIntent, StrategyConfig, compute_quotes
from trading_client import Client, OrderBook, create_session

logger = logging.getLogger(__name__)


CONTRACT_BOUNDS: Dict[ContractType, tuple[float, float]] = {
    "binary": (0.0, 100.0),
    "points": (0.0, 64.0),
    "goals": (0.0, 100.0),
}

CONTRACT_GAME_IDS: Dict[ContractType, str] = {
    "binary": "game_id_binary",
    "points": "game_id_points",
    "goals": "game_id_goals",
}

# Targeted trims (user-directed). {symbol: target_signed_position}. The strategy
# moves each position toward its target at model-favorable prices only, so we
# de-risk these without losing PnL vs our fair value.
#   - Offside longs (we're long teams our model rates well below the market) -> 0
#   - Brazil: pare the oversized, low-edge short on a favorite (-98 -> -25)
TRIM_TARGETS: Dict[ContractType, Dict[str, int]] = {
    # Disabled pending a decision on how aggressively to de-lever. Passive-only
    # trims (see strategy Pass 0) are safe but won't unwind positions that are
    # model-good yet tail-risky without crossing the spread.
}


def build_strategy(settings: Settings, contract_type: ContractType) -> StrategyConfig:
    price_min, price_max = CONTRACT_BOUNDS[contract_type]
    min_edge = {
        "binary": settings.min_edge_binary,
        "points": settings.min_edge_points,
        "goals": settings.min_edge_goals,
    }[contract_type]
    # Goals de-lever: only the goals market trims toward a lower target by
    # resting passive cover orders at the top of book (no spread-crossing).
    delever = settings.delever_goals and contract_type == "goals"
    return StrategyConfig(
        contract_type=contract_type,
        min_edge=min_edge,
        max_position=settings.max_position,
        price_min=price_min,
        price_max=price_max,
        max_order_size=settings.max_order_size,
        max_gross_exposure=settings.max_gross_exposure,
        max_net_exposure=settings.max_net_exposure,
        trim_targets=TRIM_TARGETS.get(contract_type),
        hold_mode=settings.hold_mode,
        reduce_target=settings.goals_reduce_target if delever else None,
        join_touch=delever,
        reduce_tolerance=settings.goals_reduce_tolerance if delever else 0.0,
    )


class MarketBot(Client):
    def __init__(
        self,
        session: aiohttp.ClientSession,
        game_id: int,
        token: str,
        *,
        contract_type: ContractType,
        fair_values: FairValueEngine,
        settings: Settings,
    ) -> None:
        super().__init__(session, game_id, token, base_url=settings.base_url)
        self.contract_type = contract_type
        self.fair_values = fair_values
        self.settings = settings
        self._open_order_ids: Set[int] = set()
        self._capped_symbols: Set[str] = set()
        self._quote_lock = asyncio.Lock()
        self._last_pos_refresh = 0.0
        self.strategy = build_strategy(settings, contract_type)

    async def on_start(self) -> None:
        logger.info(
            "[%s] Bot started — %s",
            self.contract_type.upper(),
            self.web_url,
        )
        while True:
            await self.fair_values.ensure_fresh()
            await self._requote()
            await asyncio.sleep(1.5)

    async def on_orderbook_updates(self, order_books: Dict[str, OrderBook]) -> None:
        await self._requote()

    async def on_fills(self, new_fills) -> None:
        for fill in new_fills:
            side = "BUY" if fill.traded_qty > 0 else "SELL"
            logger.info(
                "[%s] FILL %s %s @ %.2f x %d (remaining: %d)",
                self.contract_type.upper(),
                side,
                fill.display_symbol,
                fill.px,
                abs(fill.traded_qty),
                fill.remaining_qty,
            )
        await self.update_positions()
        await self._requote()

    async def on_order_update(self, order) -> None:
        if order.canceled:
            self._open_order_ids.discard(int(order.order_id))

    async def _requote(self) -> None:
        if self._quote_lock.locked():
            return
        async with self._quote_lock:
            try:
                book = self.fair_values.book.for_contract(self.contract_type)
            except RuntimeError:
                return

            # Bound position staleness so size-capped trims/reduces stop cleanly
            # at their target instead of overshooting on fast-filling books.
            now = time.monotonic()
            if now - self._last_pos_refresh > 1.0:
                try:
                    await self.update_positions()
                    self._last_pos_refresh = now
                except Exception:
                    pass

            try:
                intents = compute_quotes(
                    order_books=self.order_books,
                    fair_values=book,
                    positions=self.positions,
                    cfg=self.strategy,
                )
                if not intents:
                    return
                await self._execute_orders(intents)
            except Exception as exc:
                # Never let a transient API error kill the bot.
                logger.warning(
                    "[%s] Requote cycle error (continuing): %s",
                    self.contract_type.upper(), exc,
                )

    async def _execute_orders(self, intents: list[QuoteIntent]) -> None:
        # Cancel all existing orders first to avoid stale quotes.
        # Orders may fill or expire between fetch and cancel — tolerate races.
        try:
            open_orders = await self.get_open_orders()
            if open_orders:
                await self.cancel_orders(list(open_orders.keys()))
        except Exception as exc:
            logger.debug(
                "[%s] Cancel race (ignored): %s",
                self.contract_type.upper(), exc,
            )
        self._open_order_ids.clear()

        # Place new orders — cap at 30 per cycle to avoid rate limits.
        placed = 0
        for intent in intents[:30]:
            try:
                order = await self.send_order(
                    intent.display_symbol,
                    intent.price,
                    intent.qty,
                    "LIMIT",
                )
                self._open_order_ids.add(int(order.order_id))
                placed += 1
                side = "BUY" if intent.qty > 0 else "SELL"
                logger.debug(
                    "[%s] %s %s %s @ %.2f x %d (edge=%.2f)",
                    self.contract_type.upper(),
                    intent.reason,
                    side,
                    intent.display_symbol,
                    intent.price,
                    abs(intent.qty),
                    intent.edge,
                )
            except Exception as exc:
                msg = str(exc)
                # "Position limit reached" fires every cycle for capped teams;
                # log each symbol's cap hit once until it clears to avoid spam.
                if "limit" in msg.lower():
                    if intent.display_symbol not in self._capped_symbols:
                        self._capped_symbols.add(intent.display_symbol)
                        logger.info(
                            "[%s] %s at position cap (holding)",
                            self.contract_type.upper(),
                            intent.display_symbol,
                        )
                else:
                    logger.warning(
                        "[%s] Order failed %s: %s",
                        self.contract_type.upper(),
                        intent.display_symbol,
                        msg,
                    )
        # Reset cap tracking for symbols no longer being attempted.
        attempted = {i.display_symbol for i in intents[:30]}
        self._capped_symbols &= attempted
        if placed:
            # Routine re-quote; keep at DEBUG so quiet mode stays clean.
            logger.debug("[%s] Placed %d orders", self.contract_type.upper(), placed)


async def ensure_account(
    session: aiohttp.ClientSession,
    game_id: int,
    token: str,
    base_url: str,
) -> None:
    """Place and cancel a dust order to activate the account if needed."""
    client = Client(session, game_id, token, base_url=base_url)
    try:
        await client._get("account")
        return
    except Exception:
        pass
    try:
        order = await client.send_order("Curacao", 0.01, 1, "LIMIT")
        await client.cancel_orders([int(order.order_id)])
        logger.info("Initialized account for game_id=%s", game_id)
    except Exception as exc:
        logger.warning("Could not initialize account for game_id=%s: %s", game_id, exc)


async def run_dry_run(
    settings: Settings,
    *,
    cycles: int = 3,
    interval: float = 4.0,
) -> None:
    """Simulate trading without sending orders.

    For each cycle: pull live order books for all three markets, compute the
    orders the bot WOULD place, and print them with expected PnL. No orders
    are sent and nothing is cancelled.
    """
    fair_values = FairValueEngine(simulations=settings.simulations)
    logger.info("Computing fair values (%d simulations)...", settings.simulations)
    await fair_values.refresh()
    book = fair_values.book

    contracts: list[ContractType] = ["binary", "points", "goals"]

    async with create_session() as session:
        clients = {
            ct: Client(
                session,
                getattr(settings, CONTRACT_GAME_IDS[ct]),
                settings.token,
                base_url=settings.base_url,
            )
            for ct in contracts
        }

        for cycle in range(1, cycles + 1):
            print("\n" + "#" * 78)
            print(f"# DRY RUN — CYCLE {cycle}/{cycles}   (no real orders are sent)")
            print("#" * 78)

            grand_buy = grand_sell = grand_pnl = 0.0

            for ct in contracts:
                client = clients[ct]
                await client.update_order_books()
                await client.update_positions()
                cfg = build_strategy(settings, ct)
                fair = book.for_contract(ct)
                intents = compute_quotes(
                    order_books=client.order_books,
                    fair_values=fair,
                    positions=client.positions,
                    cfg=cfg,
                )

                game_id = getattr(settings, CONTRACT_GAME_IDS[ct])
                print(f"\n=== {ct.upper()} (game {game_id}) — "
                      f"min_edge={cfg.min_edge} — {len(intents)} orders ===")
                print(f"{'Action':<14}{'Symbol':<24}{'Price':>7}"
                      f"{'Size':>6}{'Fair':>8}{'Edge':>7}{'ExpPnL':>9}")
                print("-" * 75)

                buy_notional = sell_notional = exp_pnl = 0.0
                for it in intents[:18]:
                    side = "BUY " if it.qty > 0 else "SELL"
                    size = abs(it.qty)
                    fv = fair.get(it.display_symbol, 0.0)
                    order_pnl = it.edge * size  # expected profit if model is right
                    exp_pnl += order_pnl
                    if it.qty > 0:
                        buy_notional += it.price * size
                    else:
                        sell_notional += it.price * size
                    print(f"{it.reason:<14}{it.display_symbol:<24}"
                          f"{it.price:>7.2f}{size:>6d}{fv:>8.2f}"
                          f"{it.edge:>7.2f}{order_pnl:>9.1f}")

                if len(intents) > 18:
                    print(f"  ... and {len(intents) - 18} more orders")
                print(f"  -> buy notional {buy_notional:.0f}, "
                      f"sell notional {sell_notional:.0f}, "
                      f"expected edge PnL {exp_pnl:.1f}")
                grand_buy += buy_notional
                grand_sell += sell_notional
                grand_pnl += exp_pnl

            print("\n" + "-" * 78)
            print(f"CYCLE {cycle} TOTAL — buy {grand_buy:.0f}, sell {grand_sell:.0f}, "
                  f"expected edge PnL across all markets: {grand_pnl:.1f}")

            if cycle < cycles:
                await asyncio.sleep(interval)

    print("\nDry run complete. No orders were placed. "
          "Run without --dry-run to trade live.")


async def run_all_bots(settings: Settings) -> None:
    fair_values = FairValueEngine(
        simulations=settings.simulations,
        refresh_sec=settings.fair_value_refresh_sec,
    )
    logger.info("Computing fair values (%d simulations)...", settings.simulations)
    await fair_values.refresh()
    logger.info("Fair values ready. Starting bots...")

    async with create_session() as session:
        for game_id in (
            settings.game_id_binary,
            settings.game_id_points,
            settings.game_id_goals,
        ):
            await ensure_account(session, game_id, settings.token, settings.base_url)

        bots = [
            MarketBot(
                session,
                settings.game_id_binary,
                settings.token,
                contract_type="binary",
                fair_values=fair_values,
                settings=settings,
            ),
            MarketBot(
                session,
                settings.game_id_points,
                settings.token,
                contract_type="points",
                fair_values=fair_values,
                settings=settings,
            ),
            MarketBot(
                session,
                settings.game_id_goals,
                settings.token,
                contract_type="goals",
                fair_values=fair_values,
                settings=settings,
            ),
        ]
        await asyncio.gather(*(bot.start() for bot in bots))

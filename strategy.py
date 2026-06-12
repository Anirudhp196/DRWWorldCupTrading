"""Risk-managed edge-hunting strategy.

Priorities each cycle:
1. REDUCE: trim any position beyond the per-team cap back toward it.
2. EDGE: take/post the cleanest mispricings, subject to:
   - per-team position cap
   - per-market gross exposure cap (sum of |position|)
   - per-market net exposure cap (limits one-directional bias)
   - capped order size

This keeps us from shorting (or buying) the entire board and bounds
total risk per market while still capturing the biggest edges.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from fair_value import ContractType
from trading_client import OrderBook


@dataclass(frozen=True)
class QuoteIntent:
    display_symbol: str
    price: float
    qty: int  # positive = buy (bid), negative = sell (ask)
    reason: str
    edge: float


@dataclass(frozen=True)
class StrategyConfig:
    contract_type: ContractType
    min_edge: float
    max_position: int
    price_min: float
    price_max: float
    max_order_size: int = 10
    max_gross_exposure: int = 500
    max_net_exposure: int = 250
    tick: float = 0.01
    # HOLD mode: skip Pass 2 (new edge trades). Only passive trims/reduces run,
    # so the bot never adds risk and never crosses the spread.
    hold_mode: bool = False
    # Optional {symbol: target_signed_position} for user-directed trims. The
    # strategy will move each named position toward its target, trading ONLY at
    # model-favorable prices (never realizing a loss vs our fair value).
    trim_targets: Optional[Dict[str, int]] = None


def _gross(positions: Dict[str, int]) -> int:
    return sum(abs(int(v)) for v in positions.values())


def _net(positions: Dict[str, int]) -> int:
    return sum(int(v) for v in positions.values())


def compute_quotes(
    *,
    order_books: Dict[str, OrderBook],
    fair_values: Dict[str, float],
    positions: Dict[str, int],
    cfg: StrategyConfig,
) -> List[QuoteIntent]:
    intents: List[QuoteIntent] = []

    # Running, projected exposure as we accept intents this cycle.
    gross = _gross(positions)
    net = _net(positions)

    # --- PASS 0: TARGETED TRIM (user-directed risk reduction) ---
    # Move specific positions toward a target, trading ONLY at model-favorable
    # prices. We cross the spread to exit a long only when the bid is still
    # >= fair (we realize a gain vs model), and cover a short only at <= fair
    # (we never pay up). So a trim is at worst PnL-neutral vs our model.
    trimmed: set = set()
    for symbol, target in (cfg.trim_targets or {}).items():
        pos = int(positions.get(symbol, 0))
        # Only reduce magnitude toward target; never flip or grow a position.
        if pos == 0 or (pos > 0 and target >= pos) or (pos < 0 and target <= pos):
            continue
        book = order_books.get(symbol)
        fair = fair_values.get(symbol)
        if book is None or fair is None or fair <= 0:
            continue
        size = min(abs(target - pos), cfg.max_order_size)
        if size <= 0:
            continue
        # PASSIVE-ONLY: rest on our own side of the book (maker). We never cross
        # the spread, so a trim can only fill when a counterparty trades into us
        # at a model-favorable price — it cannot run away / overshoot the target.
        if target < pos:
            # Reduce a long -> rest an ASK at the offer (only sells if lifted).
            ask_px = book.best_ask_px
            if ask_px is not None and ask_px >= fair:
                price = round(ask_px, 2)
            else:
                price = round(max(fair, cfg.price_min), 2)
            intents.append(QuoteIntent(symbol, price, -size, "trim", 0.0))
        else:
            # Reduce a short -> rest a BID at the bid (only buys if hit).
            bid_px = book.best_bid_px
            if bid_px is not None and bid_px <= fair:
                price = round(bid_px, 2)
            else:
                price = round(min(fair, cfg.price_max), 2)
            intents.append(QuoteIntent(symbol, price, size, "trim", 0.0))
        trimmed.add(symbol)

    # --- PASS 1: REDUCE oversized positions (always allowed; lowers risk) ---
    for symbol, book in order_books.items():
        if symbol in trimmed:
            continue
        pos = int(positions.get(symbol, 0))
        if abs(pos) <= cfg.max_position:
            continue
        fair = fair_values.get(symbol)
        if fair is None or fair <= 0:
            continue

        excess = abs(pos) - cfg.max_position
        size = min(excess, cfg.max_order_size)
        if size <= 0:
            continue

        if pos > 0:
            # Long too big -> trim by RESTING an ask at fair value. We never
            # cross the spread (no paying up): this only fills if a buyer lifts
            # us at >= fair, so trimming is at worst PnL-neutral vs our model.
            price = round(min(fair, cfg.price_max), 2)
            bid_px = book.best_bid_px
            # Keep the resting ask strictly above the best bid so it stays a
            # passive maker order rather than crossing.
            if bid_px is not None and price <= bid_px:
                price = round(bid_px + cfg.tick, 2)
            intents.append(QuoteIntent(symbol, price, -size, "reduce_long", 0.0))
        else:
            # Short too big -> cover by RESTING a bid at fair value. We never
            # lift offers: this only fills if a seller hits us at <= fair, so
            # covering is at worst PnL-neutral vs our model.
            price = round(max(fair, cfg.price_min), 2)
            ask_px = book.best_ask_px
            # Keep the resting bid strictly below the best ask so it stays a
            # passive maker order rather than crossing.
            if ask_px is not None and price >= ask_px:
                price = round(ask_px - cfg.tick, 2)
            intents.append(QuoteIntent(symbol, price, size, "reduce_short", 0.0))

    # --- PASS 2: EDGE trades, ranked by edge, subject to exposure caps ---
    # Skipped entirely in HOLD mode so we never add risk or cross the spread.
    if cfg.hold_mode:
        return _dedupe(intents)

    candidates: List[QuoteIntent] = []
    for symbol, book in order_books.items():
        if symbol in trimmed:
            continue
        fair = fair_values.get(symbol)
        if fair is None or fair <= 0:
            continue
        pos = int(positions.get(symbol, 0))
        bid_px = book.best_bid_px
        ask_px = book.best_ask_px

        if ask_px is not None:
            buy_edge = fair - ask_px
            if buy_edge >= cfg.min_edge and pos < cfg.max_position:
                size = _size_for_edge(buy_edge, cfg.min_edge, cfg.max_position - pos,
                                      cfg.max_order_size)
                if size > 0:
                    candidates.append(
                        QuoteIntent(symbol, ask_px, size, "aggressive_buy", buy_edge))

        if bid_px is not None:
            sell_edge = bid_px - fair
            if sell_edge >= cfg.min_edge and pos > -cfg.max_position:
                size = _size_for_edge(sell_edge, cfg.min_edge, cfg.max_position + pos,
                                      cfg.max_order_size)
                if size > 0:
                    candidates.append(
                        QuoteIntent(symbol, bid_px, -size, "aggressive_sell", sell_edge))

    candidates.sort(key=lambda x: x.edge, reverse=True)

    # Accept candidates greedily while respecting gross/net caps.
    for c in candidates:
        size = abs(c.qty)
        # Gross always grows when opening/extending in a fresh direction.
        if gross + size > cfg.max_gross_exposure:
            continue
        projected_net = net + c.qty
        # Only block trades that push the dominant net side further out.
        if abs(projected_net) > cfg.max_net_exposure and abs(projected_net) > abs(net):
            continue
        intents.append(c)
        gross += size
        net = projected_net

    return _dedupe(intents)


def _size_for_edge(edge: float, min_edge: float, room: int, max_order: int) -> int:
    if room <= 0:
        return 0
    ratio = edge / min_edge
    if ratio >= 3.0:
        size = max_order
    elif ratio >= 2.0:
        size = max(1, int(max_order * 0.7))
    elif ratio >= 1.4:
        size = max(1, int(max_order * 0.5))
    else:
        size = max(1, int(max_order * 0.3))
    return min(size, room)


def _dedupe(intents: List[QuoteIntent]) -> List[QuoteIntent]:
    priority = {
        "trim": -1,
        "reduce_long": 0,
        "reduce_short": 0,
        "aggressive_buy": 1,
        "aggressive_sell": 1,
    }
    best: Dict[Tuple[str, int], QuoteIntent] = {}
    for intent in intents:
        side = 1 if intent.qty > 0 else -1
        key = (intent.display_symbol, side)
        existing = best.get(key)
        if existing is None:
            best[key] = intent
        elif priority.get(intent.reason, 9) < priority.get(existing.reason, 9):
            best[key] = intent
        elif (priority.get(intent.reason, 9) == priority.get(existing.reason, 9)
              and intent.edge > existing.edge):
            best[key] = intent
    return sorted(
        best.values(),
        key=lambda x: (x.reason in ("trim", "reduce_long", "reduce_short"), x.edge),
        reverse=True,
    )

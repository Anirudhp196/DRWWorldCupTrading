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
    # De-lever controls for the REDUCE pass:
    #   reduce_target: trim positions down to this magnitude (defaults to
    #     max_position when None).
    #   join_touch: model-favorable active de-lever. Reduce orders may CROSS the
    #     spread, but only when the fill price is on the right side of fair
    #     (buy <= fair to cover a short, sell >= fair to trim a long), so every
    #     de-lever fill is +EV vs our model. When no favorable price exists the
    #     position is left untouched. Used to unwind the offside goals short.
    reduce_target: Optional[int] = None
    join_touch: bool = False
    # Risk-trim tolerance (price units). When > 0 the join_touch de-lever will
    # cross the spread to reduce exposure even slightly AGAINST the model: it
    # covers a short at up to (fair + tol) and trims a long down to (fair - tol).
    # This bounds the spread we'll pay so we never get picked off at a silly
    # price. 0.0 keeps the de-lever strictly model-favorable.
    reduce_tolerance: float = 0.0
    # Optional {symbol: target_signed_position} for user-directed trims. The
    # strategy will move each named position toward its target, crossing the
    # spread when needed but ONLY at model-favorable prices (bounded by
    # trim_tolerance) so we never realize worse than ~fair vs our model.
    trim_targets: Optional[Dict[str, int]] = None
    # Price units we'll concede on a targeted trim: cover a short at up to
    # (fair + trim_tolerance), dump a long down to (fair - trim_tolerance).
    trim_tolerance: float = 0.0


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
    # Move specific positions toward a target. Unlike the caps-based reduce,
    # this ACTIVELY crosses the spread to unwind offside/dead positions, but
    # only at model-favorable prices bounded by trim_tolerance:
    #   - dump a long -> SELL, hitting a bid >= fair - tol (else rest at an
    #     offer >= that floor); never sell cheaper than the model minus tol.
    #   - cover a short -> BUY, lifting an ask <= fair + tol (else rest at a
    #     bid <= that cap); never pay more than the model plus tol.
    # If no acceptable price exists this cycle, the position is left untouched.
    trimmed: set = set()
    for symbol, target in (cfg.trim_targets or {}).items():
        pos = int(positions.get(symbol, 0))
        # Only reduce magnitude toward target; never flip or grow a position.
        if pos == 0 or (pos > 0 and target >= pos) or (pos < 0 and target <= pos):
            continue
        book = order_books.get(symbol)
        fair = fair_values.get(symbol)
        if book is None or fair is None:
            continue
        size = min(abs(target - pos), cfg.max_order_size)
        if size <= 0:
            continue
        bid_px = book.best_bid_px
        ask_px = book.best_ask_px
        if target < pos:
            # Dump a long -> SELL at a model-favorable price (>= fair - tol).
            floor = fair - cfg.trim_tolerance
            if bid_px is not None and bid_px >= floor:
                price = round(bid_px, 2)          # cross to hit the bid
            elif ask_px is not None and ask_px >= floor:
                price = round(ask_px, 2)          # passive maker at the offer
            else:
                continue
            intents.append(QuoteIntent(symbol, price, -size, "trim", 0.0))
        else:
            # Cover a short -> BUY at a model-favorable price (<= fair + tol).
            cap = fair + cfg.trim_tolerance
            if ask_px is not None and ask_px <= cap:
                price = round(ask_px, 2)          # cross to lift the offer
            elif bid_px is not None and bid_px <= cap:
                price = round(bid_px, 2)          # passive maker at the bid
            else:
                continue
            intents.append(QuoteIntent(symbol, price, size, "trim", 0.0))
        trimmed.add(symbol)

    # --- PASS 1: REDUCE oversized positions (always allowed; lowers risk) ---
    reduce_cap = cfg.reduce_target if cfg.reduce_target is not None else cfg.max_position
    for symbol, book in order_books.items():
        if symbol in trimmed:
            continue
        pos = int(positions.get(symbol, 0))
        if abs(pos) <= reduce_cap:
            continue
        fair = fair_values.get(symbol)
        if fair is None or fair <= 0:
            continue

        excess = abs(pos) - reduce_cap
        size = min(excess, cfg.max_order_size)
        if size <= 0:
            continue

        bid_px = book.best_bid_px
        ask_px = book.best_ask_px
        if pos > 0:
            # Long too big -> trim by SELLING. In join_touch (de-lever) mode we
            # only sell at a MODEL-FAVORABLE price (>= fair): cross to hit the
            # bid when the bid is already >= fair, else rest passively at an
            # offer that is >= fair. If neither side is favorable we skip and
            # keep the long (never sell below fair). Non-join_touch keeps the
            # original rest-at-fair behavior.
            if cfg.join_touch:
                floor = fair - cfg.reduce_tolerance    # willing to sell down to here
                if bid_px is not None and bid_px >= floor:
                    price = round(bid_px, 2)            # cross the spread to exit
                elif ask_px is not None and ask_px >= floor:
                    price = round(ask_px, 2)            # passive maker
                else:
                    continue
            else:
                price = round(min(fair, cfg.price_max), 2)
                if bid_px is not None and price <= bid_px:
                    price = round(bid_px + cfg.tick, 2)
            intents.append(QuoteIntent(symbol, price, -size, "reduce_long", 0.0))
        else:
            # Short too big -> cover by BUYING. In join_touch (de-lever) mode we
            # only buy at a MODEL-FAVORABLE price (<= fair): cross to lift the
            # offer when the ask is already <= fair (this actively unwinds the
            # deeply-offside shorts at +EV), else rest passively at a bid that is
            # <= fair. If neither side is favorable we skip and keep the short
            # (never pay above fair). Non-join_touch keeps the original behavior.
            if cfg.join_touch:
                cap = fair + cfg.reduce_tolerance      # willing to pay up to here
                if ask_px is not None and ask_px <= cap:
                    price = round(ask_px, 2)            # cross the spread to cover
                elif bid_px is not None and bid_px <= cap:
                    price = round(bid_px, 2)            # passive maker
                else:
                    continue
            else:
                price = round(max(fair, cfg.price_min), 2)
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

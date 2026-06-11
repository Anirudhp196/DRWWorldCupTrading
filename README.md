# Call Your Shot Trading Bot

An algorithmic trading client for DRW's "Call Your Shot" World Cup 2026 trading simulator ([games.drw.com/games/trading-simulator](https://games.drw.com/games/trading-simulator)). The simulator runs three independent contract markets tied to the tournament:

- **Team Performance (Binary)** — settles 100 for the World Cup champion, 0 for all other teams (game id **170**).
- **Points Based Team Performance** — settles by advancement: 64 champion, 32 runner-up, 24 bronze winner, 16 bronze loser, 8 QF exit, 4 R16, 2 R32, 0 group exit (game id **171**).
- **Team Goals** — settles to total goals scored in the tournament (game id **172**).

This project estimates fair value with a Monte Carlo Elo/Poisson tournament simulator, then trades against the live order book via the async DRW websocket and REST client.

## Quick start

```bash
pip install -r requirements.txt
cp .env.example .env   # add your JWT as DRW_TOKEN
python discover.py     # inspect games, account, model vs market
python run_bot.py      # run baseline market-making on all three games
```

Get your token from the browser after logging in to games.drw.com (Network tab → authorized API request → `Authorization: Bearer …`). **Do not commit `.env`.**

## Components

| File | Purpose |
|------|---------|
| `trading_client.py` | DRW async client (auth, order books, orders, positions) |
| `trading-simulator-client/` | Original client notebook/code from DRW |
| `teams.py` | 2026 group draw + Elo ratings |
| `simulator.py` | Monte Carlo tournament engine |
| `fair_value.py` | Fair value cache for binary / points / goals |
| `strategy.py` | Edge detection + quote generation |
| `bot.py` | Multi-market bot wiring |
| `run_bot.py` | Entry point |
| `discover.py` | Account + order book + model diagnostics |

## Baseline strategy

1. **Fair value** — 10k simulated tournaments using group-stage round robins, third-place qualifiers, and Elo-seeded knockouts. Outputs expected settlement for each contract type.
2. **Trade** — When market bid/ask diverges from fair value by at least `MIN_EDGE_*`, lift cheap offers or hit rich bids.
3. **Quote** — Passive limits one half-spread inside fair, skewed by inventory toward flat.
4. **Risk** — Respects max position 100 per contract (default cap 90 in config).

Tune edges and size in `.env` (`MIN_EDGE_BINARY`, `QUOTE_SIZE`, `MAX_POSITION`, etc.).

## Approach

Probability estimates come from Elo strength, Poisson scoring, and bracket structure, then convert to target prices. The bot compares fair values to the order book and posts `LIMIT` orders (positive qty = bid, negative = ask). Refresh fair values every 5 minutes by default.

As real match results arrive during the tournament, update Elo ratings in `teams.py` (or plug in a results feed) and restart the bot to incorporate new information — that is where most PnL alpha will come from after the baseline is running.
# DRWWorldCupTrading

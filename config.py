import os
from dataclasses import dataclass
from pathlib import Path


def _load_dotenv() -> None:
    env_path = Path(__file__).resolve().parent / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


_load_dotenv()


@dataclass(frozen=True)
class Settings:
    token: str
    game_id_binary: int = 170
    game_id_points: int = 171
    game_id_goals: int = 172
    base_url: str = "https://games.drw.com"
    # Risk-tightened edges — only take clean mispricings.
    # Goals is the most over-traded market, so it needs the highest bar.
    min_edge_binary: float = 1.5
    min_edge_points: float = 1.5
    min_edge_goals: float = 2.5
    # Per-team position cap (lowered from 95).
    max_position: int = 40
    # Max order size per individual order (caps edge-based sizing).
    max_order_size: int = 10
    # Per-market gross exposure cap: sum of |position| across all teams.
    max_gross_exposure: int = 500
    # Per-market net exposure cap: |sum of signed positions|.
    # Limits one-directional bias (we were extremely net short).
    max_net_exposure: int = 250
    simulations: int = 50_000
    fair_value_refresh_sec: int = 300
    # HOLD mode: passive-only. Disables new edge trades (Pass 2) so the bot
    # stops adding risk and never crosses the spread. It only rests passive,
    # model-favorable reduce orders on over-cap positions and otherwise holds.
    hold_mode: bool = False
    # De-lever the goals short: trim goals positions down toward this magnitude
    # by resting passive cover orders at the top of the book (maker, no
    # spread-crossing). Only active when delever_goals is True.
    delever_goals: bool = False
    goals_reduce_target: int = 20


def _env_bool(name: str, default: bool) -> bool:
    val = os.environ.get(name)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "on")


def load_settings() -> Settings:
    token = os.environ.get("DRW_TOKEN", "")
    if not token:
        raise RuntimeError(
            "Set DRW_TOKEN in .env (copy .env.example). "
            "Never commit your token to git."
        )
    return Settings(
        token=token,
        game_id_binary=int(os.environ.get("GAME_ID_BINARY", 170)),
        game_id_points=int(os.environ.get("GAME_ID_POINTS", 171)),
        game_id_goals=int(os.environ.get("GAME_ID_GOALS", 172)),
        base_url=os.environ.get("DRW_BASE_URL", "https://games.drw.com"),
        min_edge_binary=float(os.environ.get("MIN_EDGE_BINARY", 1.5)),
        min_edge_points=float(os.environ.get("MIN_EDGE_POINTS", 1.5)),
        min_edge_goals=float(os.environ.get("MIN_EDGE_GOALS", 2.5)),
        max_position=int(os.environ.get("MAX_POSITION", 40)),
        max_order_size=int(os.environ.get("MAX_ORDER_SIZE", 10)),
        max_gross_exposure=int(os.environ.get("MAX_GROSS_EXPOSURE", 500)),
        max_net_exposure=int(os.environ.get("MAX_NET_EXPOSURE", 250)),
        simulations=int(os.environ.get("SIMULATIONS", 50_000)),
        fair_value_refresh_sec=int(os.environ.get("FAIR_VALUE_REFRESH_SEC", 300)),
        hold_mode=_env_bool("HOLD_MODE", False),
        delever_goals=_env_bool("DELEVER_GOALS", False),
        goals_reduce_target=int(os.environ.get("GOALS_REDUCE_TARGET", 20)),
    )

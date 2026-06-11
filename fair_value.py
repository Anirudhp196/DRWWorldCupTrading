"""Fair value cache and refresh for all three contract sets."""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Dict, Literal

from simulator import SimulationStats, run_simulation

ContractType = Literal["binary", "points", "goals"]

logger = logging.getLogger(__name__)


@dataclass
class FairValueBook:
    binary: Dict[str, float]
    points: Dict[str, float]
    goals: Dict[str, float]
    updated_at: float

    def for_contract(self, contract_type: ContractType) -> Dict[str, float]:
        if contract_type == "binary":
            return self.binary
        if contract_type == "points":
            return self.points
        return self.goals


class FairValueEngine:
    def __init__(self, *, simulations: int = 10_000, refresh_sec: int = 300) -> None:
        self.simulations = simulations
        self.refresh_sec = refresh_sec
        self._book: FairValueBook | None = None
        self._lock = asyncio.Lock()

    @property
    def book(self) -> FairValueBook:
        if self._book is None:
            raise RuntimeError("Fair values not computed yet; call refresh() first.")
        return self._book

    def refresh_sync(self) -> FairValueBook:
        logger.info("Running %d tournament simulations...", self.simulations)
        stats = run_simulation(simulations=self.simulations)
        self._book = _stats_to_book(stats)
        logger.info("Fair values updated.")
        return self._book

    async def refresh(self) -> FairValueBook:
        async with self._lock:
            return await asyncio.to_thread(self.refresh_sync)

    async def ensure_fresh(self) -> FairValueBook:
        if self._book is None or time.time() - self._book.updated_at > self.refresh_sec:
            return await self.refresh()
        return self._book


def _stats_to_book(stats: SimulationStats) -> FairValueBook:
    return FairValueBook(
        binary=dict(stats.binary),
        points=dict(stats.points),
        goals=dict(stats.goals),
        updated_at=time.time(),
    )

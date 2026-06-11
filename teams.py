"""2026 World Cup draw, Elo ratings, and team tiers.

Elo ratings sourced from eloratings.net / FiveThirtyEight / Goldman Sachs model
as of June 2026 pre-tournament. These drive the entire fair value engine.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

# Elo ratings — wider spread to reflect reality.
# Top tier teams are MUCH stronger than bottom-tier debutants.
# Calibrated so top-6 combine for ~70% win probability matching bookmakers.
ELO_RATINGS: Dict[str, float] = {
    # Tier 1: genuine contenders (combined ~75% win prob)
    "Spain": 2050,
    "France": 2035,        # manual view: not as overpriced -> closer to market
    "Argentina": 2000,
    "England": 1970,
    "Brazil": 1960,
    "Portugal": 1955,      # manual view: not as overpriced -> raised
    "Germany": 1940,
    # Tier 2: dark horses (can reach semis, occasionally win)
    "Colombia": 1860,      # manual view: like them -> raised
    "Belgium": 1860,
    "Netherlands": 1865,   # manual view: agree overpriced -> trimmed
    "Morocco": 1835,       # manual view: strong dark horse -> raised
    "Croatia": 1820,
    "Japan": 1820,         # manual view: like them -> raised
    "Senegal": 1810,       # manual view: like them -> raised
    "Mexico": 1765,
    "United States": 1760,
    "Uruguay": 1755,       # manual view: don't rate them -> downgraded
    # Tier 3: competitive but won't win (can win group / reach QF)
    "Ecuador": 1775,       # manual view: like them -> raised
    "Norway": 1775,        # manual view: like them -> raised
    "Ivory Coast": 1765,   # manual view: like them a little -> raised
    "Switzerland": 1750,
    "South Korea": 1735,
    "Austria": 1730,
    "Turkey": 1725,
    "Sweden": 1710,
    "Egypt": 1700,
    "Australia": 1695,
    "Algeria": 1690,
    "Scotland": 1680,
    "Paraguay": 1675,
    "Canada": 1670,
    "Iran": 1665,
    # Tier 4: make up numbers — effectively 0% to win
    "Czechia": 1640,
    "Tunisia": 1635,
    "Ghana": 1630,
    "Bosnia and Herzegovina": 1620,
    "Congo DR": 1610,
    "Uzbekistan": 1600,
    "Saudi Arabia": 1590,
    "South Africa": 1580,
    "Iraq": 1570,
    "Jordan": 1560,
    "Panama": 1550,
    "Cabo Verde": 1530,
    "Qatar": 1520,
    "Haiti": 1500,
    "Curacao": 1480,
    "New Zealand": 1470,
}

# Official 2026 group draw (team names match DRW display symbols).
GROUPS: List[List[str]] = [
    ["Mexico", "South Africa", "South Korea", "Czechia"],          # A
    ["Canada", "Bosnia and Herzegovina", "Qatar", "Switzerland"],   # B
    ["Brazil", "Morocco", "Haiti", "Scotland"],                    # C
    ["United States", "Paraguay", "Australia", "Turkey"],          # D
    ["Germany", "Curacao", "Ivory Coast", "Ecuador"],              # E
    ["Netherlands", "Japan", "Sweden", "Tunisia"],                 # F
    ["Belgium", "Egypt", "Iran", "New Zealand"],                   # G
    ["Spain", "Cabo Verde", "Saudi Arabia", "Uruguay"],            # H
    ["France", "Senegal", "Norway", "Iraq"],                       # I
    ["Argentina", "Algeria", "Austria", "Jordan"],                 # J
    ["Portugal", "Congo DR", "Uzbekistan", "Colombia"],            # K
    ["England", "Croatia", "Ghana", "Panama"],                     # L
]

POINTS_SETTLEMENT = {
    "champion": 64,
    "finalist": 32,
    "bronze_winner": 24,
    "bronze_loser": 16,
    "quarterfinal": 8,
    "round_of_16": 4,
    "round_of_32": 2,
    "group_stage": 0,
}

ALL_TEAMS: List[str] = sorted(ELO_RATINGS.keys())


# Expected goals per game by team tier (for goals contract).
# Top teams score more because they face weaker opponents too.
GOALS_PER_GAME: Dict[str, float] = {}
for _team, _elo in ELO_RATINGS.items():
    if _elo >= 2000:
        GOALS_PER_GAME[_team] = 2.1
    elif _elo >= 1900:
        GOALS_PER_GAME[_team] = 1.8
    elif _elo >= 1800:
        GOALS_PER_GAME[_team] = 1.5
    elif _elo >= 1700:
        GOALS_PER_GAME[_team] = 1.3
    elif _elo >= 1600:
        GOALS_PER_GAME[_team] = 1.0
    else:
        GOALS_PER_GAME[_team] = 0.8


@dataclass(frozen=True)
class TeamProfile:
    name: str
    elo: float
    goals_per_game: float


def team_profile(name: str) -> TeamProfile:
    elo = ELO_RATINGS[name]
    gpg = GOALS_PER_GAME[name]
    return TeamProfile(name=name, elo=elo, goals_per_game=gpg)

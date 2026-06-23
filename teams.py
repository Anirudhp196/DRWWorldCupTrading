"""2026 World Cup draw, Elo ratings, and team tiers.

Elo ratings sourced from eloratings.net / FiveThirtyEight / Goldman Sachs model
as of June 2026 pre-tournament. These drive the entire fair value engine.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

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
    "United States": 1830,  # manual view: strong run expected + 4-goal opener -> raised to dark-horse tier
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

# Completed group-stage matches: (team_a, team_b, goals_a, goals_b). These are
# locked in — the simulator uses these exact scores instead of simulating, so
# real goals are certain and real group standings carry forward.
# Updated through matchday 2026-06-12.
COMPLETED_MATCHES: List[Tuple[str, str, int, int]] = [
    # --- Matchday 1 ---
    ("Mexico", "South Africa", 2, 0),            # Group A, Jun 11
    ("South Korea", "Czechia", 2, 1),            # Group A, Jun 11
    ("Canada", "Bosnia and Herzegovina", 1, 1),  # Group B, Jun 12
    ("United States", "Paraguay", 4, 1),         # Group D, Jun 12
    ("Qatar", "Switzerland", 1, 1),              # Group B, Jun 13
    ("Brazil", "Morocco", 1, 1),                 # Group C, Jun 13
    ("Scotland", "Haiti", 1, 0),                 # Group C, Jun 13
    ("Australia", "Turkey", 2, 0),               # Group D, Jun 13
    ("Germany", "Curacao", 7, 1),                # Group E, Jun 14
    ("Netherlands", "Japan", 2, 2),              # Group F, Jun 14
    ("Ivory Coast", "Ecuador", 1, 0),            # Group E, Jun 14
    ("Sweden", "Tunisia", 5, 1),                 # Group F, Jun 14
    ("Spain", "Cabo Verde", 0, 0),               # Group H, Jun 15
    ("Belgium", "Egypt", 1, 1),                  # Group G, Jun 15
    ("Uruguay", "Saudi Arabia", 1, 1),           # Group H, Jun 15
    ("Iran", "New Zealand", 2, 2),               # Group G, Jun 15
    ("France", "Senegal", 3, 1),                 # Group I, Jun 16
    ("Norway", "Iraq", 4, 1),                    # Group I, Jun 16
    ("Argentina", "Algeria", 3, 0),              # Group J, Jun 16
    # --- Matchday 2 (Jun 17-20) ---
    ("Austria", "Jordan", 3, 1),                 # Group J, Jun 17
    ("Portugal", "Congo DR", 1, 1),              # Group K, Jun 17
    ("Colombia", "Uzbekistan", 3, 1),            # Group K, Jun 17
    ("England", "Croatia", 4, 2),                # Group L, Jun 17
    ("Ghana", "Panama", 1, 0),                   # Group L, Jun 17
    ("Czechia", "South Africa", 1, 1),           # Group A, Jun 18
    ("Switzerland", "Bosnia and Herzegovina", 4, 1),  # Group B, Jun 18
    ("Canada", "Qatar", 6, 0),                   # Group B, Jun 18
    ("Mexico", "South Korea", 1, 0),             # Group A, Jun 19
    ("United States", "Australia", 2, 0),        # Group D, Jun 19
    ("Paraguay", "Turkey", 1, 0),                # Group D, Jun 19
    ("Brazil", "Haiti", 3, 0),                   # Group C, Jun 19
    ("Morocco", "Scotland", 1, 0),               # Group C, Jun 19
    ("Germany", "Ivory Coast", 2, 1),            # Group E, Jun 20
    ("Ecuador", "Curacao", 0, 0),                # Group E, Jun 20
    ("Netherlands", "Sweden", 5, 1),             # Group F, Jun 20
    # --- Matchday 2, Groups G-J (Jun 21-22) ---
    ("Belgium", "Iran", 0, 0),                   # Group G, Jun 21
    ("Spain", "Saudi Arabia", 4, 0),             # Group H, Jun 21
    ("Uruguay", "Cabo Verde", 2, 2),             # Group H, Jun 21
    ("Egypt", "New Zealand", 3, 1),              # Group G, Jun 22
    ("Argentina", "Austria", 2, 0),              # Group J, Jun 22
    ("France", "Iraq", 3, 0),                    # Group I, Jun 22
    ("Norway", "Senegal", 3, 2),                 # Group I, Jun 22
    ("Algeria", "Jordan", 2, 1),                 # Group J, Jun 22
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

# Manual goals overrides (attack stronger than the Elo tier implies).
# US opened with 4 goals; reflect a higher scoring rate for their run.
GOALS_PER_GAME["United States"] = 1.8


@dataclass(frozen=True)
class TeamProfile:
    name: str
    elo: float
    goals_per_game: float


def team_profile(name: str) -> TeamProfile:
    elo = ELO_RATINGS[name]
    gpg = GOALS_PER_GAME[name]
    return TeamProfile(name=name, elo=elo, goals_per_game=gpg)

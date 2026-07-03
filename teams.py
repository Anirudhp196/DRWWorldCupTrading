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
    "France": 2160,        # manual view: strong conviction -> semifinal floor, real title threat (clear #1)
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
    # --- Group-stage finales / remaining MD2-MD3 (Jun 20-27) -- group stage COMPLETE ---
    ("Japan", "Tunisia", 4, 0),                  # Group F, Jun 20/21
    ("Portugal", "Uzbekistan", 5, 0),            # Group K, Jun 23
    ("Colombia", "Congo DR", 1, 0),              # Group K, Jun 23
    ("England", "Ghana", 0, 0),                  # Group L, Jun 23
    ("Croatia", "Panama", 1, 0),                 # Group L, Jun 23
    ("Mexico", "Czechia", 3, 0),                 # Group A, Jun 24
    ("South Africa", "South Korea", 1, 0),       # Group A, Jun 24
    ("Switzerland", "Canada", 2, 1),             # Group B, Jun 24
    ("Bosnia and Herzegovina", "Qatar", 3, 1),   # Group B, Jun 24
    ("Brazil", "Scotland", 3, 0),                # Group C, Jun 24
    ("Morocco", "Haiti", 4, 2),                  # Group C, Jun 24
    ("Turkey", "United States", 3, 2),           # Group D, Jun 25
    ("Paraguay", "Australia", 0, 0),             # Group D, Jun 25
    ("Ivory Coast", "Curacao", 2, 0),            # Group E, Jun 25
    ("Ecuador", "Germany", 2, 1),                # Group E, Jun 25
    ("Netherlands", "Tunisia", 3, 1),            # Group F, Jun 25
    ("Japan", "Sweden", 1, 1),                   # Group F, Jun 25
    ("Belgium", "New Zealand", 5, 1),            # Group G, Jun 26
    ("Egypt", "Iran", 1, 1),                     # Group G, Jun 26
    ("Spain", "Uruguay", 1, 0),                  # Group H, Jun 26
    ("Cabo Verde", "Saudi Arabia", 0, 0),        # Group H, Jun 26
    ("France", "Norway", 4, 1),                  # Group I, Jun 26
    ("Senegal", "Iraq", 5, 0),                   # Group I, Jun 26
    ("Argentina", "Jordan", 3, 1),               # Group J, Jun 27
    ("Algeria", "Austria", 3, 3),                # Group J, Jun 27
    ("Colombia", "Portugal", 0, 0),              # Group K, Jun 27
    ("Congo DR", "Uzbekistan", 3, 1),            # Group K, Jun 27
    ("England", "Panama", 2, 0),                 # Group L, Jun 27
    ("Croatia", "Ghana", 2, 1),                  # Group L, Jun 27
]

# Actual Round-of-32 bracket (locked Jun 27 once the group stage finished).
# Ordered as the LEAVES of the knockout tree so that pairing adjacent winners
# (0v1, 2v3, ...) each round reproduces the real FIFA bracket:
#   R32 leaves -> R16 -> QF -> SF -> Final.
# Derived from the official match feeds (R16: 89=W74vW77, 90=W73vW75,
# 91=W76vW78, 92=W79vW80, 93=W83vW84, 94=W81vW82, 95=W86vW88, 96=W85vW87;
# QF: 97=89v90, 98=93v94, 99=91v92, 100=95v96; SF: 101=97v98, 102=99v100).
# Empty list -> simulator falls back to Elo-seeded bracket (pre-knockout).
KNOCKOUT_BRACKET: List[Tuple[str, str]] = [
    ("Brazil", "Japan"),                          # M74
    ("Ivory Coast", "Norway"),                    # M77
    ("South Africa", "Canada"),                   # M73
    ("Germany", "Paraguay"),                      # M75
    ("Portugal", "Croatia"),                      # M83
    ("Spain", "Austria"),                         # M84
    ("United States", "Bosnia and Herzegovina"),  # M81
    ("Belgium", "Senegal"),                       # M82
    ("Netherlands", "Morocco"),                   # M76
    ("France", "Sweden"),                         # M78
    ("Mexico", "Ecuador"),                        # M79
    ("England", "Congo DR"),                      # M80
    ("Argentina", "Cabo Verde"),                  # M86
    ("Australia", "Egypt"),                       # M88
    ("Switzerland", "Algeria"),                   # M85
    ("Colombia", "Ghana"),                        # M87
]

# Decided knockout matches: (team_a, team_b, goals_a, goals_b, winner).
# Goals are 90'+ET only (shootout goals excluded, matching the goals market);
# `winner` captures penalty-shootout outcomes. The simulator uses the real
# winner/goals for these and only simulates the still-undecided ties.
KNOCKOUT_RESULTS: List[Tuple[str, str, int, int, str]] = [
    # Round of 32 (Jun 28 - Jul 1)
    ("South Africa", "Canada", 0, 1, "Canada"),
    ("Brazil", "Japan", 2, 1, "Brazil"),
    ("Germany", "Paraguay", 1, 1, "Paraguay"),         # Paraguay 4-3 pens
    ("Netherlands", "Morocco", 1, 1, "Morocco"),       # Morocco 3-2 pens
    ("Ivory Coast", "Norway", 1, 2, "Norway"),
    ("France", "Sweden", 3, 0, "France"),
    ("Mexico", "Ecuador", 2, 0, "Mexico"),
    ("England", "Congo DR", 2, 1, "England"),
    ("Belgium", "Senegal", 3, 2, "Belgium"),           # a.e.t.
    ("United States", "Bosnia and Herzegovina", 2, 0, "United States"),
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

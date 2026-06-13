"""Monte Carlo World Cup simulator for contract fair values.

Calibrated so that:
- Top 6 favorites combine for ~70-75% win probability
- Bottom 15 teams have near-zero win chance
- Goal totals scale with number of games played (3 group + knockout rounds)
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from teams import (
    ALL_TEAMS,
    COMPLETED_MATCHES,
    GROUPS,
    POINTS_SETTLEMENT,
    TeamProfile,
    team_profile,
)


def _completed_lookup() -> Dict[frozenset, Tuple[str, str, int, int]]:
    """Index completed matches by the unordered pair of teams."""
    return {frozenset((a, b)): (a, b, ga, gb) for a, b, ga, gb in COMPLETED_MATCHES}


@dataclass
class GroupStanding:
    team: str
    points: int = 0
    gd: int = 0
    gf: int = 0


@dataclass
class SimulationStats:
    binary: Dict[str, float] = field(default_factory=dict)
    points: Dict[str, float] = field(default_factory=dict)
    goals: Dict[str, float] = field(default_factory=dict)


def _win_prob(elo_a: float, elo_b: float) -> float:
    """Standard Elo win probability."""
    return 1.0 / (1.0 + 10 ** ((elo_b - elo_a) / 400))


def _draw_prob(elo_a: float, elo_b: float) -> float:
    """Approximate draw probability (higher when teams are close in Elo)."""
    gap = abs(elo_a - elo_b)
    # World Cup draw rate ~25% for even teams, drops with big gaps.
    return max(0.08, 0.28 - 0.0004 * gap)


def _simulate_group_match(
    team_a: str,
    team_b: str,
    profiles: Dict[str, TeamProfile],
    rng: random.Random,
) -> Tuple[int, int]:
    """Simulate a group stage match. Returns (goals_a, goals_b)."""
    elo_a = profiles[team_a].elo
    elo_b = profiles[team_b].elo
    gpg_a = profiles[team_a].goals_per_game
    gpg_b = profiles[team_b].goals_per_game

    draw_p = _draw_prob(elo_a, elo_b)
    win_a_p = _win_prob(elo_a, elo_b) * (1 - draw_p)
    # remainder is win_b

    roll = rng.random()
    if roll < draw_p:
        # Draw — both score same
        g = _poisson(min(gpg_a, gpg_b) * 0.85, rng)
        return g, g
    elif roll < draw_p + win_a_p:
        # A wins
        ga = max(1, _poisson(gpg_a, rng))
        gb = _poisson(gpg_b * 0.6, rng)
        if gb >= ga:
            gb = ga - 1
        return ga, gb
    else:
        # B wins
        gb = max(1, _poisson(gpg_b, rng))
        ga = _poisson(gpg_a * 0.6, rng)
        if ga >= gb:
            ga = gb - 1
        return ga, gb


def _simulate_knockout_match(
    team_a: str,
    team_b: str,
    profiles: Dict[str, TeamProfile],
    rng: random.Random,
) -> Tuple[str, int, int]:
    """Simulate a knockout match (must produce a winner). Returns (winner, goals_a, goals_b)."""
    elo_a = profiles[team_a].elo
    elo_b = profiles[team_b].elo
    gpg_a = profiles[team_a].goals_per_game
    gpg_b = profiles[team_b].goals_per_game

    # In knockouts, favorites win MORE often (they raise their game, no settling for draws).
    # Use slightly boosted Elo gap for knockout intensity.
    effective_gap = (elo_a - elo_b) * 1.15
    win_a_p = 1.0 / (1.0 + 10 ** (-effective_gap / 400))

    if rng.random() < win_a_p:
        winner = team_a
        ga = max(1, _poisson(gpg_a * 0.9, rng))
        gb = _poisson(gpg_b * 0.55, rng)
        if gb >= ga:
            gb = ga - 1
        return winner, ga, gb
    else:
        winner = team_b
        gb = max(1, _poisson(gpg_b * 0.9, rng))
        ga = _poisson(gpg_a * 0.55, rng)
        if ga >= gb:
            ga = gb - 1
        return winner, ga, gb


def _poisson(lam: float, rng: random.Random) -> int:
    """Poisson sample via Knuth's algorithm."""
    if lam <= 0:
        return 0
    l_exp = math.exp(-lam)
    k = 0
    p = 1.0
    while p > l_exp:
        k += 1
        p *= rng.random()
    return k - 1


def _simulate_group(
    group: List[str],
    profiles: Dict[str, TeamProfile],
    rng: random.Random,
    goal_totals: Dict[str, int],
    completed: Dict[frozenset, Tuple[str, str, int, int]],
) -> Tuple[List[GroupStanding], GroupStanding]:
    standings = {team: GroupStanding(team=team) for team in group}
    for i, home in enumerate(group):
        for away in group[i + 1:]:
            result = completed.get(frozenset((home, away)))
            if result is not None:
                ra, _rb, rga, rgb = result
                # Orient the locked score to (home, away).
                ga, gb = (rga, rgb) if ra == home else (rgb, rga)
            else:
                ga, gb = _simulate_group_match(home, away, profiles, rng)
            goal_totals[home] += ga
            goal_totals[away] += gb
            _apply_result(standings[home], standings[away], ga, gb)

    ordered = sorted(
        standings.values(),
        key=lambda s: (s.points, s.gd, s.gf, profiles[s.team].elo),
        reverse=True,
    )
    return ordered, ordered[2]


def _apply_result(home: GroupStanding, away: GroupStanding, ga: int, gb: int) -> None:
    home.gf += ga
    away.gf += gb
    home.gd += ga - gb
    away.gd += gb - ga
    if ga > gb:
        home.points += 3
    elif ga < gb:
        away.points += 3
    else:
        home.points += 1
        away.points += 1


def _select_third_place_teams(thirds: List[GroupStanding]) -> List[str]:
    ranked = sorted(thirds, key=lambda s: (s.points, s.gd, s.gf), reverse=True)
    return [s.team for s in ranked[:8]]


def _seed_bracket(teams: List[str], profiles: Dict[str, TeamProfile]) -> List[str]:
    """Seed knockout bracket 1v32, 2v31, etc. so top teams don't meet early."""
    teams_sorted = sorted(teams, key=lambda t: profiles[t].elo, reverse=True)
    n = len(teams_sorted)
    bracket: List[str] = [None] * n  # type: ignore
    for i in range(n // 2):
        bracket[i * 2] = teams_sorted[i]
        bracket[i * 2 + 1] = teams_sorted[n - 1 - i]
    return bracket


def _simulate_knockout(
    teams: List[str],
    profiles: Dict[str, TeamProfile],
    rng: random.Random,
    goal_totals: Dict[str, int],
) -> Tuple[str, Dict[str, str]]:
    """Simulate full knockout bracket. Returns (champion, {team: exit_stage})."""
    exits: Dict[str, str] = {}
    remaining = _seed_bracket(teams, profiles)
    stage_order = [
        "round_of_32",
        "round_of_16",
        "quarterfinal",
        "semifinal",
        "final",
    ]
    stage_idx = 0

    while len(remaining) > 1:
        next_round: List[str] = []
        stage = stage_order[min(stage_idx, len(stage_order) - 1)]
        for i in range(0, len(remaining) - 1, 2):
            a, b = remaining[i], remaining[i + 1]
            winner, ga, gb = _simulate_knockout_match(a, b, profiles, rng)
            loser = b if winner == a else a
            goal_totals[a] += ga
            goal_totals[b] += gb
            if stage == "final":
                exits[winner] = "champion"
                exits[loser] = "finalist"
            elif stage == "semifinal":
                exits[loser] = "bronze_loser"
            else:
                exits[loser] = stage
            next_round.append(winner)
        if len(remaining) % 2 == 1:
            next_round.append(remaining[-1])
        remaining = next_round
        stage_idx += 1

    champion = remaining[0]
    if champion not in exits:
        exits[champion] = "champion"
    return champion, exits


def _assign_points(
    group_exits: Dict[str, str],
    knockout_exits: Dict[str, str],
    profiles: Dict[str, TeamProfile],
    rng: random.Random,
) -> Dict[str, int]:
    points: Dict[str, int] = {}
    for team in group_exits:
        points[team] = POINTS_SETTLEMENT["group_stage"]

    bronze_candidates = []
    for team, stage in knockout_exits.items():
        if stage == "champion":
            points[team] = POINTS_SETTLEMENT["champion"]
        elif stage == "finalist":
            points[team] = POINTS_SETTLEMENT["finalist"]
        elif stage == "bronze_loser":
            bronze_candidates.append(team)
        else:
            points[team] = POINTS_SETTLEMENT[stage]

    # Bronze match between the two semifinal losers.
    if len(bronze_candidates) == 2:
        a, b = bronze_candidates
        wp = _win_prob(profiles[a].elo, profiles[b].elo)
        if rng.random() < wp:
            points[a] = POINTS_SETTLEMENT["bronze_winner"]
            points[b] = POINTS_SETTLEMENT["bronze_loser"]
        else:
            points[b] = POINTS_SETTLEMENT["bronze_winner"]
            points[a] = POINTS_SETTLEMENT["bronze_loser"]
    else:
        for t in bronze_candidates:
            points[t] = POINTS_SETTLEMENT["bronze_loser"]

    return points


def run_simulation(
    *,
    simulations: int = 10_000,
    seed: int = 42,
) -> SimulationStats:
    profiles = {team: team_profile(team) for team in ALL_TEAMS}
    rng = random.Random(seed)
    completed = _completed_lookup()

    binary_wins = {team: 0.0 for team in ALL_TEAMS}
    points_sum = {team: 0.0 for team in ALL_TEAMS}
    goals_sum = {team: 0.0 for team in ALL_TEAMS}

    for _ in range(simulations):
        goal_totals = {team: 0 for team in ALL_TEAMS}
        qualifiers: List[str] = []
        third_places: List[GroupStanding] = []
        group_exits: Dict[str, str] = {}

        for group in GROUPS:
            ordered, third = _simulate_group(group, profiles, rng, goal_totals, completed)
            qualifiers.extend([ordered[0].team, ordered[1].team])
            third_places.append(third)
            for standing in ordered[2:]:
                group_exits[standing.team] = "group_stage"

        qualifiers.extend(_select_third_place_teams(third_places))
        qualifiers = qualifiers[:32]

        champion, knockout_exits = _simulate_knockout(
            qualifiers, profiles, rng, goal_totals,
        )
        binary_wins[champion] += 1

        team_points = _assign_points(group_exits, knockout_exits, profiles, rng)
        for team in ALL_TEAMS:
            points_sum[team] += team_points.get(team, 0)
            goals_sum[team] += goal_totals[team]

    inv = 1.0 / simulations
    return SimulationStats(
        binary={t: 100.0 * binary_wins[t] * inv for t in ALL_TEAMS},
        points={t: points_sum[t] * inv for t in ALL_TEAMS},
        goals={t: goals_sum[t] * inv for t in ALL_TEAMS},
    )

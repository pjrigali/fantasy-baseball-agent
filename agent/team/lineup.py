"""
Description: Lineup optimizer. Given today's MLB schedule and each rostered
             player's eligible slots and z-score value, suggests the optimal
             active lineup — maximizing players with games while preferring
             higher-value players in contested flex slots.
Source Data: ESPN Fantasy API (live roster with eligibleSlots and proTeam)
             MLB Stats API (today's schedule)
             Output of valuation.compute_player_values() (z-scores)
Outputs: Lineup suggestion dict consumed by scripts/team/suggest_lineup.py
"""

import requests
from collections import defaultdict
from datetime import date

# ── ESPN proTeam → MLB team name keyword mapping ────────────────────────────
# Used to match against MLB Stats API schedule team names.
_ESPN_TO_MLB_KEYWORD: dict[str, str] = {
    "Bal":  "Orioles",    "Bos":  "Red Sox",    "NYY":  "Yankees",
    "TB":   "Rays",       "Tor":  "Blue Jays",  "CWS":  "White Sox",
    "ChW":  "White Sox",  "Cle":  "Guardians",  "Det":  "Tigers",
    "KC":   "Royals",     "Min":  "Twins",      "Hou":  "Astros",
    "LAA":  "Angels",     "Oak":  "Athletics",  "Sea":  "Mariners",
    "Tex":  "Rangers",    "Atl":  "Braves",     "Mia":  "Marlins",
    "NYM":  "Mets",       "Phi":  "Phillies",   "Wsh":  "Nationals",
    "ChC":  "Cubs",       "Cin":  "Reds",       "Mil":  "Brewers",
    "Pit":  "Pirates",    "StL":  "Cardinals",  "Ari":  "Diamondbacks",
    "Col":  "Rockies",    "LAD":  "Dodgers",    "SD":   "Padres",
    "SF":   "Giants",
}

# ── Slot fill priority (lower = filled first) ───────────────────────────────
_SLOT_PRIORITY: dict[str, int] = {
    "C": 1, "1B": 2, "2B": 3, "3B": 4, "SS": 5,
    "OF": 6, "2B/SS": 7, "1B/3B": 8, "IF": 9,
    "SP": 10, "RP": 11,
    "UTIL": 12, "P": 13,
    "BE": 99, "IL": 100,
}

_BENCH_SLOTS = {"BE", "IL"}

_MLB_HEADERS = {"User-Agent": "Mozilla/5.0"}

# Canonical IL detection lives in agent.data.players; alias keeps call sites local.
from agent.data.players import is_on_il as _is_on_il


def _teams_playing_today() -> set[str]:
    """Fetch MLB teams with games today. Returns set of team name keywords."""
    today = date.today().isoformat()
    url   = (f"https://statsapi.mlb.com/api/v1/schedule"
             f"?startDate={today}&endDate={today}&sportId=1&gameType=R")
    try:
        resp = requests.get(url, headers=_MLB_HEADERS, timeout=10)
        resp.raise_for_status()
        names = set()
        for day in resp.json().get("dates", []):
            for g in day.get("games", []):
                names.add(g["teams"]["home"]["team"]["name"])
                names.add(g["teams"]["away"]["team"]["name"])
        return names
    except Exception:
        return set()


def _has_game(pro_team: str, playing_teams: set[str]) -> bool:
    """Check if an ESPN proTeam abbreviation is playing today."""
    keyword = _ESPN_TO_MLB_KEYWORD.get(pro_team, "")
    return any(keyword in t for t in playing_teams)


def optimize_lineup(
    roster_players: list,        # espn_api Player objects
    player_values: dict[str, dict],
    starter_slots: list[dict],   # from settings["roster"]["starter_slots"]
) -> dict:
    """
    Suggest an optimal lineup.

    Args:
        roster_players:  List of espn_api Player objects (my_team.roster).
        player_values:   From valuation.compute_player_values() — { name: {rolling_z, ...} }.
        starter_slots:   From settings["roster"]["starter_slots"] — [{ position, count }, ...].

    Returns:
        {
          "date": str,
          "playing_today": int,        # count of rostered players with games
          "starters": [
            { "slot": str, "player": str, "has_game": bool,
              "rolling_z": float, "inj": str, "pro_team": str }
          ],
          "bench": [
            { "player": str, "has_game": bool, "reason": str,
              "rolling_z": float, "inj": str, "pro_team": str }
          ],
        }
    """
    today          = date.today().isoformat()
    playing_teams  = _teams_playing_today()

    # Build a normalized name → z-score lookup
    def _z(name: str) -> float:
        val = player_values.get(name, player_values.get(name.lower(), {}))
        return val.get("rolling_z", 0.0)

    # Annotate each player
    annotated = []
    for p in roster_players:
        on_il    = _is_on_il(p.injuryStatus or "")
        has_game = _has_game(p.proTeam or "", playing_teams)
        annotated.append({
            "name":           p.name,
            "eligible":       [s for s in (p.eligibleSlots or []) if s not in _BENCH_SLOTS],
            "pro_team":       p.proTeam or "?",
            "inj":            p.injuryStatus or "ACTIVE",
            "on_il":          on_il,
            "has_game":       has_game,
            "rolling_z":      _z(p.name),
            "current_slot":   p.lineupSlot,
        })

    # Sort by priority: has_game DESC, rolling_z DESC
    annotated.sort(key=lambda p: (not p["has_game"], -p["rolling_z"]))

    # Build the slot queue from starter_slots
    slot_queue: list[str] = []
    for slot_def in sorted(starter_slots, key=lambda s: _SLOT_PRIORITY.get(s["position"], 50)):
        slot_queue.extend([slot_def["position"]] * slot_def["count"])

    # Greedy assignment
    assigned_players: set[str] = set()
    starters: list[dict]       = []
    bench:    list[dict]        = []

    for slot in slot_queue:
        # Find best available player eligible for this slot
        best = None
        for p in annotated:
            if p["name"] in assigned_players:
                continue
            if p["on_il"]:
                continue
            if slot in p["eligible"] or (slot == "UTIL" and any(
                    s not in {"P", "SP", "RP", "BE", "IL"} for s in p["eligible"])):
                best = p
                break
            if slot == "P" and any(s in {"SP", "RP"} for s in p["eligible"]):
                best = p
                break

        if best:
            assigned_players.add(best["name"])
            starters.append({
                "slot":      slot,
                "player":    best["name"],
                "has_game":  best["has_game"],
                "rolling_z": best["rolling_z"],
                "inj":       best["inj"],
                "pro_team":  best["pro_team"],
            })
        else:
            starters.append({
                "slot":      slot,
                "player":    "EMPTY",
                "has_game":  False,
                "rolling_z": 0.0,
                "inj":       "",
                "pro_team":  "",
            })

    # Everyone not assigned goes to bench
    for p in annotated:
        if p["name"] not in assigned_players:
            if p["on_il"]:
                reason = "[IL]"
            elif not p["has_game"]:
                reason = "no game today"
            else:
                reason = "no slot available"
            bench.append({
                "player":    p["name"],
                "has_game":  p["has_game"],
                "rolling_z": p["rolling_z"],
                "inj":       p["inj"],
                "pro_team":  p["pro_team"],
                "reason":    reason,
            })

    playing_today = sum(1 for p in annotated if p["has_game"] and not p["on_il"])

    return {
        "date":          today,
        "playing_today": playing_today,
        "total_roster":  len(annotated),
        "starters":      starters,
        "bench":         bench,
    }


def format_lineup(result: dict) -> str:
    lines = [
        f"\n{'LINEUP SUGGESTION — ' + result['date']:^72}",
        f"  {result['playing_today']} of {result['total_roster']} rostered players have games today",
        "",
        f"  {'Slot':<10} {'Player':<28} {'Z':>6}  {'Team':<5}  Status",
        "  " + "-" * 62,
    ]

    for s in result["starters"]:
        if s["player"] == "EMPTY":
            lines.append(f"  {s['slot']:<10} {'--- empty ---':<28}")
            continue
        game_flag = "  " if s["has_game"] else " *"
        inj       = f"[{s['inj']}]" if s["inj"] not in ("ACTIVE", "") else ""
        lines.append(
            f"  {s['slot']:<10} {s['player']:<28} {s['rolling_z']:>+6.2f}  "
            f"{s['pro_team']:<5}  {game_flag}{inj}"
        )

    if result["bench"]:
        lines += ["", "  BENCH / IL:", "  " + "-" * 40]
        for p in result["bench"]:
            game_note = "plays" if p["has_game"] else "no game"
            lines.append(f"  {p['player']:<28} {p['reason']:<18} ({game_note})")

    lines += [
        "",
        "  * = no game today — consider benching",
    ]
    return "\n".join(lines)

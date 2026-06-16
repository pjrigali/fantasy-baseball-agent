"""
Description: Identifies SP and RP streamers — available free agents worth
             picking up for the upcoming week based on:
               SP: upcoming starts, opponent weakness, and recent performance
               RP: recent SVHD rate and ERA/WHIP in save/hold situations
             Uses the MLB Stats API for upcoming schedule and probable pitchers,
             and derives opponent strength from season boxscore data.
Source Data: data/raw/stats_mlb_daily_{year}.csv (opponent strength + recent perf)
             MLB Stats API /schedule (upcoming games + probable pitchers)
             ESPN API (free agents)
Outputs: Streamer result dict consumed by scripts/analysis/find_streamers.py
"""

import requests
from collections import defaultdict
from datetime import date, timedelta

from agent.credentials import get_espn
from agent.data.players import is_on_il as _is_on_il, normalize_name as _normalize_name


def _safe_int(val) -> int:
    try: return int(val)
    except: return 0


def _build_name_index(stat_rows: list[dict], role: str) -> dict:
    from collections import defaultdict
    idx: dict = defaultdict(list)
    for r in stat_rows:
        if r.get("b_or_p") == role:
            idx[_normalize_name(r["player_name"])].append(r)
    return dict(idx)


def _agg_sp(name: str, name_index: dict, cutoff: str | None = None) -> dict | None:
    rows = name_index.get(_normalize_name(name), [])
    rows = [r for r in rows if _safe_int(r.get("GS", 0)) == 1
            and (r.get("did_play") == "1" or _safe_int(r.get("OUTS", 0)) > 0)]
    if cutoff:
        rows = [r for r in rows if r["date"] >= cutoff]
    if not rows:
        return None
    gs = len(rows)
    qs   = sum(_safe_int(r.get("QS",   0)) for r in rows)
    outs = sum(_safe_int(r.get("OUTS", 0)) for r in rows)
    er   = sum(_safe_int(r.get("ER",   0)) for r in rows)
    ph   = sum(_safe_int(r.get("P_H",  0)) for r in rows)
    pbb  = sum(_safe_int(r.get("P_BB", 0)) for r in rows)
    k    = sum(_safe_int(r.get("K",    0)) for r in rows)
    ip   = outs / 3
    return {
        "GS": gs, "QS": qs, "QS_rate": round(qs / gs, 2) if gs else 0.0,
        "IP": round(ip, 1), "OUTS": outs,
        "ERA":  round((er * 27) / outs, 2) if outs else 0.0,
        "WHIP": round((ph + pbb) / ip, 2)  if ip   else 0.0,
        "K9":   round((k * 27) / outs, 2)  if outs else 0.0,
    }


def _agg_rp(name: str, name_index: dict, cutoff: str | None = None) -> dict | None:
    rows = name_index.get(_normalize_name(name), [])
    rows = [r for r in rows if r.get("did_play") == "1" or _safe_int(r.get("OUTS", 0)) > 0]
    if cutoff:
        rows = [r for r in rows if r["date"] >= cutoff]
    if not rows:
        return None
    g    = len(rows)
    sv   = sum(_safe_int(r.get("SV",   0)) for r in rows)
    hld  = sum(_safe_int(r.get("HLD",  0)) for r in rows)
    svhd = sum(_safe_int(r.get("SVHD", 0)) for r in rows)
    outs = sum(_safe_int(r.get("OUTS", 0)) for r in rows)
    er   = sum(_safe_int(r.get("ER",   0)) for r in rows)
    ph   = sum(_safe_int(r.get("P_H",  0)) for r in rows)
    pbb  = sum(_safe_int(r.get("P_BB", 0)) for r in rows)
    k    = sum(_safe_int(r.get("K",    0)) for r in rows)
    ip   = outs / 3
    return {
        "G": g, "SV": sv, "HLD": hld, "SVHD": svhd,
        "SVHD_G": round(svhd / g, 3) if g else 0.0,
        "IP": round(ip, 1), "OUTS": outs,
        "ERA":  round((er * 27) / outs, 2) if outs else 0.0,
        "WHIP": round((ph + pbb) / ip, 2)  if ip   else 0.0,
        "K9":   round((k * 27) / outs, 2)  if outs else 0.0,
    }

_MLB_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}
_SP_MIN_OUTS = 20    # ~6.7 IP minimum sample
_RP_MIN_OUTS = 15    # ~5 IP minimum sample


# ---------------------------------------------------------------------------
# Schedule + probable pitchers
# ---------------------------------------------------------------------------

def fetch_upcoming_schedule(days: int = 7) -> list[dict]:
    """
    Fetch scheduled games for the next N days with probable pitchers.

    Returns list of:
      { date, home_team_id, home_team, away_team_id, away_team,
        home_pitcher, away_pitcher }
    """
    today = date.today()
    end   = (today + timedelta(days=days)).isoformat()
    url   = (
        f"https://statsapi.mlb.com/api/v1/schedule"
        f"?startDate={today.isoformat()}&endDate={end}"
        f"&sportId=1&gameType=R&hydrate=probablePitcher"
    )
    try:
        resp = requests.get(url, headers=_MLB_HEADERS, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        return []

    games = []
    for day in resp.json().get("dates", []):
        for g in day.get("games", []):
            if g["status"]["abstractGameState"] == "Final":
                continue
            home = g["teams"]["home"]
            away = g["teams"]["away"]
            games.append({
                "date":          g["officialDate"],
                "home_team_id":  home["team"]["id"],
                "home_team":     home["team"]["name"],
                "away_team_id":  away["team"]["id"],
                "away_team":     away["team"]["name"],
                "home_pitcher":  home.get("probablePitcher", {}).get("fullName", "TBD"),
                "away_pitcher":  away.get("probablePitcher", {}).get("fullName", "TBD"),
            })
    return games


# ---------------------------------------------------------------------------
# Opponent strength (runs allowed = pitching quality → lower runs = harder)
# Flip: we want a weak offense (high runs allowed by that team's pitching,
# meaning they score few runs). We measure avg runs scored per game.
# ---------------------------------------------------------------------------

def build_team_offense_strength(stat_rows: list[dict]) -> dict[int, float]:
    """
    Calculate average runs scored per game for each MLB team.
    Lower value = weaker offense = better matchup for pitchers.
    Returns { mlb_team_id: avg_runs_per_game }
    """
    team_runs:  dict[int, float] = defaultdict(float)
    team_games: dict[int, set]   = defaultdict(set)

    for row in stat_rows:
        if row.get("b_or_p") != "batter":
            continue
        try:
            tid  = int(row["team_id"])
            runs = float(row.get("R", 0) or 0)
            gid  = row.get("game_id", "")
            if gid:
                team_games[tid].add(gid)
                team_runs[tid] += runs
        except (ValueError, TypeError):
            continue

    return {
        tid: round(team_runs[tid] / len(games), 2)
        for tid, games in team_games.items()
        if games
    }


def get_opponent_strength(team_id: int, offense_strength: dict[int, float]) -> float | None:
    """Return avg runs/game for the opponent team. Lower = weaker offense."""
    return offense_strength.get(team_id)


# ---------------------------------------------------------------------------
# SP streamer finder
# ---------------------------------------------------------------------------

def find_sp_streamers(
    stat_rows: list[dict],
    days: int = 7,
    top_n: int = 15,
    year: int | None = None,
) -> list[dict]:
    """
    Find available SP streamers for the upcoming week.

    Scoring:
      - starts_this_week: number of scheduled starts (higher = better)
      - recent_perf:      28d z-score from pitcher stats (QS, ERA, WHIP, K/9)
      - opp_weakness:     avg runs/game allowed by opponent (lower = weaker offense)
    """
    from espn_api.baseball import League

    creds = get_espn()
    year  = year or creds.season_year
    swid  = creds.swid if creds.swid.startswith("{") else "{" + creds.swid + "}"
    league = League(league_id=creds.league_id, year=year, espn_s2=creds.s2, swid=swid)

    today   = date.today()
    cut_28  = (today - timedelta(days=28)).isoformat()
    name_idx = _build_name_index(stat_rows, "pitcher")
    offense  = build_team_offense_strength(stat_rows)
    schedule = fetch_upcoming_schedule(days=days)

    # Build pitcher → upcoming starts map
    pitcher_starts: dict[str, list[dict]] = defaultdict(list)
    for game in schedule:
        for role, pitcher_name, opp_team_id in (
            ("home", game["home_pitcher"], game["away_team_id"]),
            ("away", game["away_pitcher"], game["home_team_id"]),
        ):
            if pitcher_name and pitcher_name != "TBD":
                norm = _normalize_name(pitcher_name)
                pitcher_starts[norm].append({
                    "date":     game["date"],
                    "opponent": game["away_team"] if role == "home" else game["home_team"],
                    "opp_id":   opp_team_id,
                    "is_home":  role == "home",
                })

    # Get available SP free agents
    fa_players = league.free_agents(size=300)
    results = []
    seen    = set()

    for p in fa_players:
        if p.name in seen or "SP" not in p.eligibleSlots:
            continue
        seen.add(p.name)
        if _is_on_il(p.injuryStatus or ""):
            continue

        norm    = _normalize_name(p.name)
        starts  = pitcher_starts.get(norm, [])
        if not starts:
            continue  # no upcoming starts this week

        s_all = _agg_sp(p.name, name_idx)
        if s_all is None or s_all["OUTS"] < _SP_MIN_OUTS:
            continue

        s_28 = _agg_sp(p.name, name_idx, cutoff=cut_28) or {}

        # Opponent weakness score (avg of all opponent offenses this week)
        opp_strengths = [
            offense.get(s["opp_id"])
            for s in starts
            if offense.get(s["opp_id"]) is not None
        ]
        avg_opp = round(sum(opp_strengths) / len(opp_strengths), 2) if opp_strengths else None

        results.append({
            "name":         p.name,
            "team":         p.proTeam or "?",
            "starts":       len(starts),
            "start_dates":  [s["date"] for s in starts],
            "opponents":    [s["opponent"] for s in starts],
            "avg_opp_runs": avg_opp,
            "season":       s_all,
            "last_28d":     s_28,
        })

    # Score: starts first, then weak opponent, then recent QS rate
    results.sort(key=lambda x: (
        -x["starts"],
        x["avg_opp_runs"] if x["avg_opp_runs"] is not None else 99,
        -(x["last_28d"] or x["season"]).get("QS_rate", 0),
    ))

    return results[:top_n]


# ---------------------------------------------------------------------------
# RP streamer finder
# ---------------------------------------------------------------------------

def find_rp_streamers(
    stat_rows: list[dict],
    top_n: int = 15,
    year: int | None = None,
) -> list[dict]:
    """
    Find available RP streamers ranked by SVHD rate + ERA + WHIP.
    """
    from espn_api.baseball import League

    creds = get_espn()
    year  = year or creds.season_year
    swid  = creds.swid if creds.swid.startswith("{") else "{" + creds.swid + "}"
    league = League(league_id=creds.league_id, year=year, espn_s2=creds.s2, swid=swid)

    today  = date.today()
    cut_14 = (today - timedelta(days=14)).isoformat()
    cut_28 = (today - timedelta(days=28)).isoformat()
    name_idx = _build_name_index(stat_rows, "pitcher")

    fa_players = league.free_agents(size=300)
    results = []
    seen    = set()

    for p in fa_players:
        if p.name in seen:
            continue
        seen.add(p.name)
        slots = p.eligibleSlots
        if "RP" not in slots or "SP" in slots:
            continue
        if _is_on_il(p.injuryStatus or ""):
            continue

        s_all = _agg_rp(p.name, name_idx)
        if s_all is None or s_all["OUTS"] < _RP_MIN_OUTS:
            continue

        results.append({
            "name":     p.name,
            "team":     p.proTeam or "?",
            "season":   s_all,
            "last_28d": _agg_rp(p.name, name_idx, cutoff=cut_28) or {},
            "last_14d": _agg_rp(p.name, name_idx, cutoff=cut_14) or {},
        })

    results.sort(key=lambda x: (
        -x["season"]["SVHD"],
        -x["season"]["SVHD_G"],
         x["season"]["WHIP"],
         x["season"]["ERA"],
    ))
    return results[:top_n]

"""
Description: Builds full-season projected stat aggregates per team and per player
             by scaling YTD stats to a full 183-day season. Used as the baseline
             for trade simulation. Rate stats (OPS, ERA, WHIP, K/9) are computed
             from projected counting stat components, not scaled directly.
Source Data: data/raw/stats_mlb_daily_{year}.csv
             data/raw/roster_espn_season_{year}.csv
Outputs: team_projections and player_projections dicts consumed by simulation.py
"""

from datetime import date
from collections import defaultdict

from agent.data.storage import raw_path, read_csv
from agent.scoring import get_categories
from agent.team.roster import _normalize_name

SEASON_LENGTH = 183  # days in a full MLB season


def _f(val) -> float:
    try:
        return float(val)
    except (TypeError, ValueError):
        return 0.0


def _season_days(stat_rows: list[dict]) -> int:
    """Infer how many days of the season have been played from the data."""
    dates = {r["date"] for r in stat_rows if r.get("date")}
    if not dates:
        return 1
    season_start = min(dates)
    try:
        start = date.fromisoformat(season_start)
        today = date.today()
        return max(1, (today - start).days)
    except ValueError:
        return max(1, len(dates))


def build_player_stats(stat_rows: list[dict]) -> dict[str, dict]:
    """
    Aggregate raw YTD stat rows into per-player season totals.
    Returns { player_name_lower: { raw counting stats + derived rate stats } }
    """
    raw: dict[str, dict] = defaultdict(lambda: defaultdict(float))

    for row in stat_rows:
        if _f(row.get("did_play", 0)) == 0:
            continue
        name = _normalize_name(row.get("player_name", ""))
        role = row.get("b_or_p", "")
        if role == "batter":
            for col in ("R", "HR", "RBI", "SB", "AB", "H", "B_BB", "TB", "HBP", "SF"):
                raw[name][col] += _f(row.get(col))
        elif role == "pitcher":
            for col in ("QS", "SVHD", "SV", "HLD", "K", "W", "OUTS", "ER", "P_H", "P_BB"):
                raw[name][col] += _f(row.get(col))

    result = {}
    for name, s in raw.items():
        ip = s["OUTS"] / 3
        denom = s["AB"] + s["B_BB"] + s["HBP"] + s["SF"]
        obp = (s["H"] + s["B_BB"] + s["HBP"]) / denom if denom > 0 else 0.0
        slg = s["TB"] / s["AB"] if s["AB"] > 0 else 0.0
        result[name] = {
            **dict(s),
            "IP":   round(ip, 1),
            "OPS":  round(obp + slg, 4),
            "ERA":  round((s["ER"] * 9 / ip), 3) if ip > 0 else 0.0,
            "WHIP": round((s["P_H"] + s["P_BB"]) / ip, 3) if ip > 0 else 0.0,
            "K/9":  round((s["K"] * 9 / ip), 3) if ip > 0 else 0.0,
        }
    return result


def project_player_stats(
    player_stats: dict[str, dict],
    days_played: int,
) -> dict[str, dict]:
    """
    Scale each player's YTD counting stats to a full 183-day season.
    Rate stats are recomputed from projected components.
    Players with < 5 IP (pitchers) or < 30 AB (batters) are excluded from projection.
    """
    scale = SEASON_LENGTH / max(days_played, 1)
    counting = ("R", "HR", "RBI", "SB", "QS", "SVHD", "SV", "HLD", "K", "W",
                "AB", "H", "B_BB", "TB", "HBP", "SF", "OUTS", "ER", "P_H", "P_BB")

    projected = {}
    for name, s in player_stats.items():
        ip  = s.get("IP", 0)
        ab  = s.get("AB", 0)
        if ip < 5 and ab < 30:
            continue  # insufficient sample

        p = {col: s.get(col, 0) * scale for col in counting}
        proj_ip = p["OUTS"] / 3
        denom = p["AB"] + p["B_BB"] + p["HBP"] + p["SF"]
        obp = (p["H"] + p["B_BB"] + p["HBP"]) / denom if denom > 0 else 0.0
        slg = p["TB"] / p["AB"] if p["AB"] > 0 else 0.0

        projected[name] = {
            **p,
            "IP":   round(proj_ip, 1),
            "OPS":  round(obp + slg, 4),
            "ERA":  round((p["ER"] * 9 / proj_ip), 3) if proj_ip > 0 else 0.0,
            "WHIP": round((p["P_H"] + p["P_BB"]) / proj_ip, 3) if proj_ip > 0 else 0.0,
            "K/9":  round((p["K"] * 9 / proj_ip), 3) if proj_ip > 0 else 0.0,
        }
    return projected


def build_team_projections(
    projected_players: dict[str, dict],
    roster_rows: list[dict],
    year: int | None = None,
) -> dict[int, dict]:
    """
    Aggregate projected player stats into per-team category totals.
    Rate stats (OPS, ERA, WHIP, K/9) are re-derived from aggregated components
    rather than averaged, so they reflect true team-level rates.

    Returns { espn_team_id: { cat_name: value } }
    """
    categories = get_categories(year)
    cat_names = {c["name"] for c in categories}

    # Most recent roster entry per player
    player_team: dict[str, int] = {}
    for row in sorted(roster_rows, key=lambda r: r.get("date", "")):
        inj = row.get("player_injury_status", "")
        # Exclude IL players from team projections (not contributing)
        if _is_on_il(inj):
            continue
        player_team[_normalize_name(row["player_name"])] = int(row["team_id"])

    # Aggregate raw components per team
    team_raw: dict[int, dict] = defaultdict(lambda: defaultdict(float))
    for name, stats in projected_players.items():
        tid = player_team.get(name)
        if tid is None:
            continue
        for col in ("R", "HR", "RBI", "SB", "QS", "SVHD",
                    "AB", "H", "B_BB", "TB", "HBP", "SF",
                    "OUTS", "ER", "P_H", "P_BB", "K"):
            team_raw[tid][col] += stats.get(col, 0)

    # Re-derive rate stats per team
    result = {}
    for tid, s in team_raw.items():
        ip = s["OUTS"] / 3
        denom = s["AB"] + s["B_BB"] + s["HBP"] + s["SF"]
        obp = (s["H"] + s["B_BB"] + s["HBP"]) / denom if denom > 0 else 0.0
        slg = s["TB"] / s["AB"] if s["AB"] > 0 else 0.0
        team = dict(s)
        team.update({
            "OPS":  round(obp + slg, 4),
            "ERA":  round((s["ER"] * 9 / ip), 3) if ip > 0 else 0.0,
            "WHIP": round((s["P_H"] + s["P_BB"]) / ip, 3) if ip > 0 else 0.0,
            "K/9":  round((s["K"] * 9 / ip), 3) if ip > 0 else 0.0,
        })
        result[tid] = {k: team[k] for k in cat_names if k in team}

    return result


def _is_on_il(injury_status: str) -> bool:
    s = (injury_status or "").upper()
    return "DL" in s or s in {"INJURY_RESERVE", "OUT", "SUSPENSION"}


def load_projections(year: int | None = None) -> tuple[dict, dict, dict, int]:
    """
    Load and project everything needed for trade simulation.

    Returns:
        player_ytd:        { player_name: raw YTD stats }
        player_projected:  { player_name: scaled projected stats }
        team_projected:    { team_id: projected category totals }
        days_played:       int
    """
    from agent.credentials import get_espn
    year = year or get_espn().season_year

    stat_rows   = read_csv(raw_path() / f"stats_mlb_daily_{year}.csv")
    roster_rows = read_csv(raw_path() / f"roster_espn_season_{year}.csv")

    days_played       = _season_days(stat_rows)
    player_ytd        = build_player_stats(stat_rows)
    player_projected  = project_player_stats(player_ytd, days_played)
    team_projected    = build_team_projections(player_projected, roster_rows, year)

    return player_ytd, player_projected, team_projected, days_played

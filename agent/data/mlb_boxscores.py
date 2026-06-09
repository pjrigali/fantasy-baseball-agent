"""
Description: Fetches per-game hitting and pitching stats for all MLB players
             via the MLB Stats API boxscore endpoint. One request per game
             (~15/day), emitting one row per player per game per role.
             Bench players who did not play are included with did_play=0.
             Deduplicates on (date, player_id, b_or_p) — safe to re-run.

             Flow:
               1. GET /api/v1/schedule  — find all Final games in date range
               2. GET /api/v1/game/{gamePk}/boxscore  — one request per game
               3. Emit one row per player per game per role (batter or pitcher)

Source Data: MLB Stats API
               /api/v1/schedule?startDate=...&endDate=...&sportId=1&gameType=R
               /api/v1/game/{gamePk}/boxscore
Outputs: List of dicts — caller decides where to save.
         Canonical save path: bronze/stats_mlb_boxscore_{year}.csv
"""

import time
import requests
from datetime import datetime, date, timedelta

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
}

PITCHER_POSITIONS = {"P", "SP", "RP", "TWP"}

SEASON_START: dict[int, date] = {
    2025: date(2025, 3, 20),
    2026: date(2026, 3, 26),
}

BATTER_COLS = ["G", "AB", "R", "H", "2B", "3B", "HR", "RBI", "SB", "CS", "B_BB", "SO", "HBP", "SF", "TB"]
PITCHER_COLS = ["G", "GS", "W", "L", "SV", "HLD", "SVHD", "OUTS", "P_H", "P_R", "ER", "P_HR", "P_BB", "K", "QS"]
ALL_STAT_COLS = sorted(set(BATTER_COLS + PITCHER_COLS))

FIELDNAMES = [
    "date", "scoring_period", "player_id", "player_name",
    "team_id", "team_name", "opponent_id", "is_home",
    "game_id", "b_or_p", "did_play",
] + ALL_STAT_COLS


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------

def _get_games(start_date: str, end_date: str) -> list[dict]:
    url = (
        f"https://statsapi.mlb.com/api/v1/schedule"
        f"?startDate={start_date}&endDate={end_date}&sportId=1&gameType=R"
    )
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        print(f"  Schedule fetch error: {e}")
        return []

    games = []
    for day in resp.json().get("dates", []):
        for g in day.get("games", []):
            if g["status"]["abstractGameState"] != "Final":
                continue
            games.append({
                "gamePk":    g["gamePk"],
                "date":      g["officialDate"],
                "home_id":   g["teams"]["home"]["team"]["id"],
                "home_name": g["teams"]["home"]["team"]["name"],
                "away_id":   g["teams"]["away"]["team"]["id"],
                "away_name": g["teams"]["away"]["team"]["name"],
            })
    return games


def _get_boxscore(game_pk: int) -> dict | None:
    url = f"https://statsapi.mlb.com/api/v1/game/{game_pk}/boxscore"
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"  Boxscore fetch error for game {game_pk}: {e}")
        return None


# ---------------------------------------------------------------------------
# Row builders
# ---------------------------------------------------------------------------

def _scoring_period(game_date_str: str, season: int) -> int:
    start = SEASON_START.get(season, date(season, 3, 26))
    try:
        d = datetime.strptime(game_date_str, "%Y-%m-%d").date()
        return max(1, (d - start).days + 1)
    except ValueError:
        return 0


def _ip_to_outs(ip_str: str) -> int:
    s = str(ip_str)
    if "." in s:
        inn, partial = s.split(".")
        return int(inn) * 3 + int(partial)
    return int(s) * 3 if s else 0


def _batter_row(player: dict, meta: dict) -> dict:
    s = player["stats"].get("batting", {})
    did_play = 1 if (s.get("plateAppearances", 0) or s.get("atBats", 0)) else 0
    row = {c: "" for c in ALL_STAT_COLS}
    row.update({
        "G": 1, "AB": s.get("atBats", 0), "R": s.get("runs", 0),
        "H": s.get("hits", 0), "2B": s.get("doubles", 0), "3B": s.get("triples", 0),
        "HR": s.get("homeRuns", 0), "RBI": s.get("rbi", 0),
        "SB": s.get("stolenBases", 0), "CS": s.get("caughtStealing", 0),
        "B_BB": s.get("baseOnBalls", 0), "SO": s.get("strikeOuts", 0),
        "HBP": s.get("hitByPitch", 0), "SF": s.get("sacFlies", 0),
        "TB": s.get("totalBases", 0),
    })
    row.update(meta)
    row["b_or_p"] = "batter"
    row["did_play"] = did_play
    return row


def _pitcher_row(player: dict, meta: dict) -> dict:
    s = player["stats"].get("pitching", {})
    outs = s.get("outs", 0) or _ip_to_outs(s.get("inningsPitched", "0"))
    gs = s.get("gamesStarted", 0)
    sv = s.get("saves", 0)
    hld = s.get("holds", 0)
    er = s.get("earnedRuns", 0)
    did_play = 1 if (s.get("gamesPitched", 0) or outs) else 0
    row = {c: "" for c in ALL_STAT_COLS}
    row.update({
        "G": 1, "GS": gs, "W": s.get("wins", 0), "L": s.get("losses", 0),
        "SV": sv, "HLD": hld, "SVHD": sv + hld, "OUTS": outs,
        "P_H": s.get("hits", 0), "P_R": s.get("runs", 0), "ER": er,
        "P_HR": s.get("homeRuns", 0), "P_BB": s.get("baseOnBalls", 0),
        "K": s.get("strikeOuts", 0),
        "QS": 1 if (gs == 1 and outs >= 18 and er <= 3) else 0,
    })
    row.update(meta)
    row["b_or_p"] = "pitcher"
    row["did_play"] = did_play
    return row


def _extract_rows(boxscore: dict, game_info: dict, season: int) -> list[dict]:
    rows = []
    sp = _scoring_period(game_info["date"], season)

    for side in ("home", "away"):
        team_data = boxscore["teams"][side]
        is_home = (side == "home")
        meta_base = {
            "date":           game_info["date"],
            "scoring_period": sp,
            "team_id":        team_data["team"]["id"],
            "team_name":      team_data["team"]["name"],
            "opponent_id":    game_info["away_id"] if is_home else game_info["home_id"],
            "is_home":        is_home,
            "game_id":        game_info["gamePk"],
        }

        for _, player in team_data.get("players", {}).items():
            meta = {
                **meta_base,
                "player_id":   player["person"]["id"],
                "player_name": player["person"]["fullName"],
            }
            pos = player.get("position", {}).get("abbreviation", "")
            batting  = player["stats"].get("batting", {})
            pitching = player["stats"].get("pitching", {})

            if pos in PITCHER_POSITIONS:
                rows.append(_pitcher_row(player, meta))
                if batting.get("plateAppearances", 0):
                    rows.append(_batter_row(player, meta))
            else:
                rows.append(_batter_row(player, meta))
                if pitching.get("gamesPitched", 0):
                    rows.append(_pitcher_row(player, meta))

    return rows


# ---------------------------------------------------------------------------
# Public fetch function
# ---------------------------------------------------------------------------

def fetch_boxscores(
    season: int,
    start_date: str | None = None,
    end_date: str | None = None,
    existing_rows: list[dict] | None = None,
    delay: float = 0.5,
) -> list[dict]:
    """
    Fetch MLB boxscore rows for the given date range.

    Args:
        season:        Season year (used for scoring_period calculation).
        start_date:    Fetch from this date YYYY-MM-DD. If None, inferred from
                       existing_rows (most recent valid date with >= 50 rows).
        end_date:      Fetch through this date YYYY-MM-DD. Defaults to today
                       (or yesterday if before noon).
        existing_rows: Previously saved rows used for dedup and start_date inference.
        delay:         Seconds to sleep between game requests.

    Returns:
        List of new (non-duplicate) row dicts ready to append to existing_rows.
    """
    existing_rows = existing_rows or []

    # Infer end_date
    if not end_date:
        now = datetime.now()
        if now.hour < 12:
            end_date = (now.date() - timedelta(days=1)).strftime("%Y-%m-%d")
        else:
            end_date = now.date().strftime("%Y-%m-%d")

    # Build dedup key set and infer start_date from existing data
    existing_keys: set[tuple] = set()
    inferred_start = f"{season}-03-23"

    if existing_rows:
        today_str = date.today().strftime("%Y-%m-%d")
        date_counts: dict[str, int] = {}
        for r in existing_rows:
            existing_keys.add((r["date"], str(r["player_id"]), r["b_or_p"]))
            date_counts[r["date"]] = date_counts.get(r["date"], 0) + 1
        valid_dates = [d for d, cnt in date_counts.items() if d <= today_str and cnt >= 50]
        if valid_dates:
            inferred_start = max(valid_dates)

    if not start_date:
        start_date = inferred_start

    games = _get_games(start_date, end_date)
    print(f"  Found {len(games)} Final games between {start_date} and {end_date}")

    new_rows: list[dict] = []
    for game in games:
        print(f"  {game['date']}  {game['away_name']} @ {game['home_name']}  (pk={game['gamePk']})")
        boxscore = _get_boxscore(game["gamePk"])
        if not boxscore:
            continue
        for row in _extract_rows(boxscore, game, season):
            key = (row["date"], str(row["player_id"]), row["b_or_p"])
            if key not in existing_keys:
                new_rows.append(row)
                existing_keys.add(key)
        time.sleep(delay)

    return new_rows

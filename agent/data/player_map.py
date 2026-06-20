"""
Description: Builds and maintains the canonical player identity map for the
             fantasy-baseball-agent harness. Bridges MLBAM player IDs with ESPN
             player IDs by querying three sources:
               1. MLB Stats API   — authoritative roster + position for 2023+
               2. Local data files — harness MLB stats + ESPN roster/draft files
               3. ESPN player_map + MLB people/search — bridge fallback for misses

             Inclusion gate: a player is written ONLY if they appear in the MLB
             Stats API season roster for 2023 or later, OR in a local harness
             MLB stats file dated 2023+. ESPN-only entries with no 2023+ MLB
             presence are excluded and reported.

             Idempotent: stable sort by normalized_name then mlbam_id; safe to
             re-run as seasons and files arrive.

Source Data:
    LIVE (skipped with offline=True):
      - https://statsapi.mlb.com/api/v1/sports/1/players?season={2023..present}
      - https://statsapi.mlb.com/api/v1/teams?sportId=1
      - https://statsapi.mlb.com/api/v1/people/search?names=...
      - ESPN league.player_map via espn-api (requires config.ini credentials)
    LOCAL:
      - data/raw/stats_mlb_*.csv      (player_id, player_name, b_or_p columns)
      - data/raw/roster_espn_season_*.csv  (player_id, player_name, eligible_slots, ...)
      - data/raw/draft_espn_season_*.csv   (player_id, player_name)
      - data/processed/player_map.csv (previous run, used to seed eligible_slots)

Outputs:
    - data/processed/player_map.csv  (canonical, overwritten each run)
      Columns: mlbam_player_id, espn_player_id, mlb_name, espn_name,
               normalized_name, b_or_p, primary_position, eligible_slots,
               pro_team, id_source, seen_in, first_seen_year, last_seen_year,
               last_verified_date
    - logs/player_map_{YYYYMMDD}.log
"""

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import date
from pathlib import Path

from agent.data.players import normalize_name
from agent.data.storage import raw_path, processed_path, read_csv, write_csv

_LOG_DIR = Path(__file__).parents[2] / "logs"
_USER_AGENT = {"User-Agent": "Mozilla/5.0"}
_SUFFIXES = (" jr.", " sr.", " ii", " iii", " iv")

_ABSOLUTE_FIRST_YEAR = 2023  # hard floor — no MLB Stats API data before this
CURRENT_YEAR = date.today().year
DEFAULT_FIRST_YEAR = CURRENT_YEAR - 1  # default window: prior year + current year (2 seasons)

FIELDNAMES = [
    "mlbam_player_id", "espn_player_id", "mlb_name", "espn_name",
    "normalized_name", "b_or_p", "primary_position", "eligible_slots",
    "pro_team", "id_source", "seen_in", "first_seen_year", "last_seen_year",
    "last_verified_date",
]


# ── Helpers ────────────────────────────────────────────────────────────────────

def _normalize(name: str) -> str:
    """normalize_name + suffix stripping for the cross-source bridge."""
    n = normalize_name(name)
    for suf in _SUFFIXES:
        if n.endswith(suf):
            n = n[: -len(suf)].strip()
            break
    return n


def _http_json(url: str):
    req = urllib.request.Request(url, headers=_USER_AGENT)
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError):
            if attempt == 2:
                return None
            time.sleep(2 ** attempt)
    return None


def _borp_from_position(pos: dict) -> str:
    ptype = (pos or {}).get("type", "")
    abbr = (pos or {}).get("abbreviation", "")
    if ptype == "Two-Way Player" or abbr == "TWP":
        return "both"
    if ptype == "Pitcher" or abbr == "P":
        return "pitcher"
    return "batter"


def _borp_from_slots(slots: str) -> str:
    """Infer b_or_p from an ESPN eligible_slots string."""
    parts = {p.strip().upper() for p in (slots or "").replace(",", "|").split("|")}
    if parts & {"P", "SP", "RP"}:
        return "pitcher"
    return "batter"


def _year_from_path(path: Path) -> int | None:
    if len(path.name) >= 4 and path.name[:4].isdigit():
        return int(path.name[:4])
    return None


# ── Stage 1: MLB universe ──────────────────────────────────────────────────────

def _build_mlb_universe(offline: bool, first_year: int, log) -> dict:
    """mlbam_id (str) -> record dict."""
    universe: dict = {}

    def ensure(mlbam: str, name: str) -> dict:
        rec = universe.get(mlbam)
        if rec is None:
            rec = {
                "mlbam_player_id": mlbam,
                "mlb_name": name,
                "normalized_name": _normalize(name),
                "b_or_p": "",
                "primary_position": "",
                "pro_team": "",
                "years": set(),
                "seen_in": set(),
                "_borp_votes": defaultdict(int),
                "espn_player_id": "",
                "espn_name": "",
                "eligible_slots": "",
                "id_source": "mlb_only",
            }
            universe[mlbam] = rec
        return rec

    # 1a. Live MLB Stats API — authoritative roster + position
    if not offline:
        teams_map: dict = {}
        td = _http_json("https://statsapi.mlb.com/api/v1/teams?sportId=1")
        for t in (td or {}).get("teams", []):
            teams_map[t.get("id")] = t.get("abbreviation", "")
        log(f"  MLB teams map: {len(teams_map)} teams")

        for season in range(first_year, CURRENT_YEAR + 1):
            url = f"https://statsapi.mlb.com/api/v1/sports/1/players?season={season}"
            data = _http_json(url)
            people = (data or {}).get("people", [])
            log(f"  MLB API season={season}: {len(people)} players")
            for p in people:
                mlbam = str(p.get("id", "")).strip()
                name = (p.get("fullName") or "").strip()
                if not mlbam or not name:
                    continue
                rec = ensure(mlbam, name)
                rec["mlb_name"] = name
                rec["normalized_name"] = _normalize(name)
                pos = p.get("primaryPosition", {})
                borp = _borp_from_position(pos)
                if borp:
                    rec["_borp_votes"][borp] += 100  # API is authoritative
                if pos.get("abbreviation"):
                    rec["primary_position"] = pos["abbreviation"]
                tid = (p.get("currentTeam") or {}).get("id")
                if tid and tid in teams_map:
                    rec["pro_team"] = teams_map[tid]
                rec["years"].add(season)
                rec["seen_in"].add(f"mlb_api:{season}")

    # 1b. Local harness MLB stats files — gate + provenance + b_or_p cross-check
    for path in sorted(raw_path().glob("stats_mlb_*.csv")):
        year = _year_from_path(path)
        if not year or year < first_year:
            continue
        rows = read_csv(path)
        seen = 0
        for r in rows:
            mlbam = str(r.get("player_id") or "").strip()
            name = (r.get("player_name") or "").strip()
            if not mlbam or not name:
                continue
            rec = ensure(mlbam, name)
            if not rec["mlb_name"]:
                rec["mlb_name"] = name
                rec["normalized_name"] = _normalize(name)
            rec["years"].add(year)
            rec["seen_in"].add(path.name)
            row_borp = (r.get("b_or_p") or "").strip()
            if row_borp in ("batter", "pitcher"):
                rec["_borp_votes"][row_borp] += 1
            seen += 1
        log(f"  {path.name}: {seen} rows")

    # Resolve b_or_p: pitcher wins on ties (conservative — avoids false batter labels)
    for rec in universe.values():
        votes = rec["_borp_votes"]
        if votes.get("both", 0):
            rec["b_or_p"] = "both"
        elif votes.get("pitcher", 0) >= votes.get("batter", 0) and votes.get("pitcher", 0) > 0:
            rec["b_or_p"] = "pitcher"
        elif votes.get("batter", 0) > 0:
            rec["b_or_p"] = "batter"

    return universe


# ── Stage 2: ESPN side ─────────────────────────────────────────────────────────

def _build_espn_side(offline: bool, log) -> tuple[dict, dict]:
    """
    Returns (by_norm, by_id).
    by_norm: normalized_name -> first ESPN record (for name-match pass)
    by_id:   espn_id (str)   -> record dict
    """
    by_id: dict = {}

    def ensure(eid: str, name: str) -> dict:
        rec = by_id.get(eid)
        if rec is None:
            rec = {"espn_player_id": eid, "espn_name": name,
                   "eligible_slots": "", "pro_team": "", "borp": ""}
            by_id[eid] = rec
        elif name and not rec["espn_name"]:
            rec["espn_name"] = name
        return rec

    # 2a. Seed from a previous player_map.csv run — preserves eligible_slots
    prev = processed_path() / "player_map.csv"
    if prev.exists():
        for r in read_csv(prev):
            eid = (r.get("espn_player_id") or "").strip()
            if not eid:
                continue
            rec = ensure(eid, r.get("espn_name", ""))
            if r.get("eligible_slots") and not rec["eligible_slots"]:
                rec["eligible_slots"] = r["eligible_slots"]
            if r.get("pro_team") and not rec["pro_team"]:
                rec["pro_team"] = r["pro_team"]
        log(f"  Seeded {len(by_id)} ESPN ids from previous player_map.csv")

    # 2b. Local harness ESPN roster files — richest source (slots, team, position)
    for path in sorted(raw_path().glob("roster_espn_season_*.csv")):
        rows = read_csv(path)
        for r in rows:
            eid = str(r.get("player_id") or "").strip()
            name = (r.get("player_name") or "").strip()
            if not eid:
                continue
            rec = ensure(eid, name)
            slots = (r.get("player_eligible_slots") or "").strip()
            team = (r.get("player_pro_team") or "").strip()
            pos = (r.get("player_position") or "").strip()
            if slots and not rec["eligible_slots"]:
                rec["eligible_slots"] = slots
            if team and not rec["pro_team"]:
                rec["pro_team"] = team
            if not rec["borp"] and pos:
                rec["borp"] = "pitcher" if pos.upper() in ("P", "SP", "RP") else "batter"
        log(f"  {path.name}: {len(rows)} roster rows")

    # 2c. Local harness ESPN draft files — additional player ids/names
    for path in sorted(raw_path().glob("draft_espn_season_*.csv")):
        rows = read_csv(path)
        for r in rows:
            eid = str(r.get("player_id") or "").strip()
            name = (r.get("player_name") or "").strip()
            if eid:
                ensure(eid, name)
        log(f"  {path.name}: {len(rows)} draft rows")

    # 2d. Live ESPN league.player_map — catches free agents not on any roster
    if not offline:
        try:
            from agent.credentials import get_espn
            from espn_api.baseball import League
            creds = get_espn()
            swid = creds.swid if creds.swid.startswith("{") else "{" + creds.swid + "}"
            lg = League(
                league_id=creds.league_id,
                year=creds.season_year,
                espn_s2=creds.s2,
                swid=swid,
            )
            added = 0
            for k, v in getattr(lg, "player_map", {}).items():
                if isinstance(k, int) and isinstance(v, str):
                    eid = str(k)
                    if eid not in by_id:
                        ensure(eid, v)
                        added += 1
            log(f"  ESPN live player_map: +{added} new espn ids")
        except Exception as e:
            log(f"  [!] ESPN live fetch skipped: {e!r}")

    by_norm: dict = {}
    for rec in by_id.values():
        n = _normalize(rec["espn_name"])
        if n:
            by_norm.setdefault(n, rec)
    return by_norm, by_id


# ── Stage 3: bridge ESPN <-> MLBAM ─────────────────────────────────────────────

def _bridge(universe: dict, espn_by_norm: dict, espn_by_id: dict, offline: bool, log) -> list[dict]:
    """Attach ESPN ids to universe rows. Returns list of unmatched ESPN records."""
    matched_espn: set[str] = set()

    def attach(rec: dict, espn: dict, src: str) -> None:
        rec["espn_player_id"] = espn["espn_player_id"]
        rec["espn_name"] = espn["espn_name"]
        if espn["eligible_slots"]:
            rec["eligible_slots"] = espn["eligible_slots"]
        if espn["pro_team"] and not rec["pro_team"]:
            rec["pro_team"] = espn["pro_team"]
        rec["id_source"] = src
        matched_espn.add(espn["espn_player_id"])

    # Build per-name candidate lists (namesakes share a key)
    cand_by_norm: dict[str, list] = defaultdict(list)
    for rec in espn_by_id.values():
        n = _normalize(rec["espn_name"])
        if n:
            cand_by_norm[n].append(rec)

    # Pass 1: name match with namesake disambiguation via b_or_p + pro_team
    for mlbam, rec in universe.items():
        cands = [e for e in cand_by_norm.get(rec["normalized_name"], [])
                 if e["espn_player_id"] not in matched_espn]
        if not cands:
            continue
        if len(cands) == 1:
            attach(rec, cands[0], "name_match")
        else:
            # Multiple namesakes — require b_or_p agreement to avoid mis-assignment
            def espn_borp(e: dict) -> str:
                return e.get("borp") or _borp_from_slots(e.get("eligible_slots", ""))
            matching = [e for e in cands if espn_borp(e) == rec["b_or_p"]]
            if not matching:
                continue
            # Break remaining ties: same pro_team wins, then most recent season
            last_year = max(rec.get("years") or {0})
            matching.sort(key=lambda e: (
                1 if (e["pro_team"] and rec["pro_team"] and e["pro_team"] == rec["pro_team"]) else 0,
                last_year,
            ), reverse=True)
            attach(rec, matching[0], "name_match")

    matched_after_pass1 = len(matched_espn)
    log(f"  Pass 1 (name match): {matched_after_pass1} ESPN ids matched")

    # Pass 2: MLB people/search API for ESPN players still unmatched whose
    # surname appears in the unmatched MLB universe (pre-filters API calls)
    if not offline:
        unbridged_surnames = {
            rec["normalized_name"].split()[-1]
            for rec in universe.values()
            if not rec.get("espn_player_id") and rec["normalized_name"].split()
        }
        unmatched_espn = [
            r for eid, r in espn_by_id.items()
            if eid not in matched_espn
            and _normalize(r["espn_name"]).split()
            and _normalize(r["espn_name"]).split()[-1] in unbridged_surnames
        ]
        log(f"  Pass 2 (API bridge) candidates: {len(unmatched_espn)}")
        resolved = 0
        for r in unmatched_espn:
            name = r["espn_name"]
            if not name:
                continue
            url = ("https://statsapi.mlb.com/api/v1/people/search?names="
                   + urllib.parse.quote(name))
            data = _http_json(url)
            e_borp = r.get("borp") or _borp_from_slots(r.get("eligible_slots", ""))
            for person in (data or {}).get("people", []):
                mlbam = str(person.get("id", "")).strip()
                urec = universe.get(mlbam)
                if urec and not urec.get("espn_player_id"):
                    ub = urec.get("b_or_p") or ""
                    if ub in ("", "both") or e_borp == ub:
                        attach(urec, r, "api")
                        resolved += 1
                        break
        log(f"  Pass 2 resolved: {resolved}")

    excluded = [r for eid, r in espn_by_id.items() if eid not in matched_espn]
    return excluded


# ── Stage 4: assemble + write ──────────────────────────────────────────────────

def _to_row(rec: dict, verified: str) -> dict:
    years = rec.get("years") or set()
    return {
        "mlbam_player_id":    rec.get("mlbam_player_id", ""),
        "espn_player_id":     rec.get("espn_player_id", ""),
        "mlb_name":           rec.get("mlb_name", ""),
        "espn_name":          rec.get("espn_name", ""),
        "normalized_name":    rec.get("normalized_name", ""),
        "b_or_p":             rec.get("b_or_p", ""),
        "primary_position":   rec.get("primary_position", ""),
        "eligible_slots":     rec.get("eligible_slots", ""),
        "pro_team":           rec.get("pro_team", ""),
        "id_source":          rec.get("id_source", ""),
        "seen_in":            ";".join(sorted(rec.get("seen_in", set()))),
        "first_seen_year":    min(years) if years else "",
        "last_seen_year":     max(years) if years else "",
        "last_verified_date": verified,
    }


def build(offline: bool = False, dry_run: bool = False, first_year: int | None = None) -> dict:
    """
    Build (or rebuild) the canonical player identity map.

    Args:
        offline:    Skip all network calls — use local data files only.
        dry_run:    Compute and report but do not write player_map.csv.
        first_year: Earliest season to include. Defaults to DEFAULT_FIRST_YEAR
                    (current year - 1, covering the past two seasons). Set to
                    _ABSOLUTE_FIRST_YEAR (2023) or earlier for a full historical
                    window — expect the run to take several minutes when calling
                    the MLB API for multiple seasons.

    Returns:
        Summary dict: total_players, espn_matched, espn_match_rate,
                      espn_excluded, id_source breakdown, first_year.
    """
    first_year = max(_ABSOLUTE_FIRST_YEAR, first_year or DEFAULT_FIRST_YEAR)
    verified = date.today().isoformat()
    log_lines: list[str] = []

    def log(msg: str = "") -> None:
        print(msg)
        log_lines.append(str(msg))

    log("=" * 70)
    log(f"player_map.build()  offline={offline}  dry_run={dry_run}  first_year={first_year}")
    log("=" * 70)

    log(f"\n[1] Building MLB universe (inclusion gate: {first_year}+)...")
    universe = _build_mlb_universe(offline, first_year, log)
    log(f"  -> {len(universe)} distinct MLBAM ids")

    log("\n[2] Building ESPN side...")
    espn_by_norm, espn_by_id = _build_espn_side(offline, log)
    log(f"  -> {len(espn_by_id)} distinct ESPN ids")

    log("\n[3] Bridging ESPN <-> MLBAM...")
    excluded = _bridge(universe, espn_by_norm, espn_by_id, offline, log)

    rows = [_to_row(rec, verified) for rec in universe.values()]
    rows.sort(key=lambda r: (r["normalized_name"], str(r["mlbam_player_id"])))

    # Validation report
    total = len(rows)
    with_espn = sum(1 for r in rows if r["espn_player_id"])
    src_counts: dict[str, int] = defaultdict(int)
    for r in rows:
        src_counts[r["id_source"]] += 1

    log("\n" + "=" * 70)
    log("VALIDATION")
    log("=" * 70)
    log(f"  Total players:             {total}")
    log(f"  espn_player_id populated:  {with_espn} ({100 * with_espn / max(1, total):.1f}%)")
    log("  id_source breakdown:")
    for s, c in sorted(src_counts.items(), key=lambda x: -x[1]):
        log(f"    {s:12s} {c}")
    log(f"  ESPN excluded (no 2023+ MLB presence): {len(excluded)}")
    for r in sorted(excluded, key=lambda x: x["espn_name"])[:10]:
        log(f"    espn_id={r['espn_player_id']:10s}  {r['espn_name']}")

    if not dry_run:
        out = processed_path() / "player_map.csv"
        write_csv(out, rows, FIELDNAMES)
        log(f"\nWrote {total} rows -> {out}")

        _LOG_DIR.mkdir(parents=True, exist_ok=True)
        log_path = _LOG_DIR / f"player_map_{verified.replace('-', '')}.log"
        log_path.write_text("\n".join(log_lines), encoding="utf-8")
        log(f"Log  -> {log_path}")
    else:
        log("\n[dry-run] not writing player_map.csv")

    return {
        "total_players": total,
        "espn_matched": with_espn,
        "espn_match_rate": round(with_espn / max(1, total), 3),
        "espn_excluded": len(excluded),
        "id_source": dict(src_counts),
        "first_year": first_year,
        "dry_run": dry_run,
    }

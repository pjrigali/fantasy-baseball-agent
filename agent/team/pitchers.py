"""
Description: SP and RP replacement analysis. Aggregates stats across three windows
             (season, last 28 days, last 14 days) from MLB boxscore data. Flags
             underperforming rostered pitchers and ranks available FA replacements
             by the league's priority stat order.
             Ported from analyze_sp_replacements.py and analyze_rp_replacements.py.

             SP flags:  LOW_QS (QS/GS < 30%) | HIGH_WHIP (> 1.45) | LOW_K9 (< 7.0)
             RP flags:  LOW_SVHD (< 5 with >=5G) | HIGH_WHIP (> 1.45) | HIGH_ERA (> 4.50)

             SP ranking: QS desc -> WHIP asc -> K/9 desc
             RP ranking: SVHD desc -> SVHD/G desc -> WHIP asc -> ERA asc

Source Data: data/raw/stats_mlb_daily_{year}.csv
             ESPN API (live rosters + free agents)
Outputs: Dicts consumed by scripts/team/analyze_sp_replacements.py and analyze_rp_replacements.py
"""

import unicodedata
from collections import defaultdict
from datetime import date, timedelta

from espn_api.baseball import League

from agent.credentials import get_espn

# ── SP thresholds ──────────────────────────────────────────────────────────
SP_MIN_OUTS_FA  = 20      # ~6.7 IP minimum for FA SPs
SP_MIN_GS_FLAG  = 3       # minimum starts before applying flags
SP_FLAG_QS_RATE = 0.30
SP_FLAG_WHIP    = 1.45
SP_FLAG_K9      = 7.0

# ── RP thresholds ──────────────────────────────────────────────────────────
RP_MIN_OUTS_FA  = 15      # ~5 IP minimum for FA RPs
RP_MIN_APP_FLAG = 5       # minimum appearances before applying flags
RP_FLAG_SVHD    = 5
RP_FLAG_WHIP    = 1.45
RP_FLAG_ERA     = 4.50

_HITTER_SLOTS = {'C', '1B', '2B', '3B', 'SS', 'OF', 'LF', 'CF', 'RF', 'DH'}
_IL_STATUSES  = {'INJURY_RESERVE', 'OUT', 'SUSPENSION'}


# ── Helpers ────────────────────────────────────────────────────────────────

def _normalize_name(name: str) -> str:
    """Normalize player name for matching: NFKD unicode, lowercase, strip."""
    n = unicodedata.normalize('NFKD', name)
    n = ''.join(c for c in n if not unicodedata.combining(c))
    return n.lower().strip()


def _safe_int(val) -> int:
    try:
        return int(val)
    except (TypeError, ValueError):
        return 0


def _is_on_il(inj: str) -> bool:
    s = (inj or '').upper()
    return 'DL' in s or s in _IL_STATUSES


def _player_status(player) -> tuple[bool, str]:
    inj = (getattr(player, 'injuryStatus', 'ACTIVE') or 'ACTIVE').upper()
    on_il = _is_on_il(inj)
    if on_il:              return True,  '[IL]'
    if inj == 'DAY_TO_DAY': return False, 'DTD'
    if inj not in ('ACTIVE', ''): return False, inj
    return False, 'Active'


def _connect_league(year: int) -> League:
    creds = get_espn()
    swid = creds.swid if creds.swid.startswith('{') else '{' + creds.swid + '}'
    return League(league_id=creds.league_id, year=year, espn_s2=creds.s2, swid=swid)


def _build_name_index(stat_rows: list[dict], role: str) -> dict[str, list[dict]]:
    idx: dict[str, list[dict]] = defaultdict(list)
    for r in stat_rows:
        if r.get('b_or_p') == role:
            idx[_normalize_name(r['player_name'])].append(r)
    return dict(idx)


# ── Aggregators ────────────────────────────────────────────────────────────

def _agg_sp(name: str, name_index: dict, cutoff: str | None = None) -> dict | None:
    """Aggregate SP stats (GS=1 rows only) for a player."""
    rows = name_index.get(_normalize_name(name), [])
    rows = [r for r in rows
            if _safe_int(r.get('GS', 0)) == 1
            and (r.get('did_play') == '1' or _safe_int(r.get('OUTS', 0)) > 0)]
    if cutoff:
        rows = [r for r in rows if r['date'] >= cutoff]
    if not rows:
        return None

    gs   = len(rows)
    qs   = sum(_safe_int(r.get('QS',   0)) for r in rows)
    outs = sum(_safe_int(r.get('OUTS', 0)) for r in rows)
    er   = sum(_safe_int(r.get('ER',   0)) for r in rows)
    ph   = sum(_safe_int(r.get('P_H',  0)) for r in rows)
    pbb  = sum(_safe_int(r.get('P_BB', 0)) for r in rows)
    k    = sum(_safe_int(r.get('K',    0)) for r in rows)

    ip   = outs / 3
    return {
        'GS':      gs,
        'QS':      qs,
        'QS_rate': round(qs / gs, 2) if gs else 0.0,
        'IP':      round(ip, 1),
        'OUTS':    outs,
        'ERA':     round((er * 27) / outs, 2) if outs else 0.0,
        'WHIP':    round((ph + pbb) / ip, 2)  if ip   else 0.0,
        'K9':      round((k * 27) / outs, 2)  if outs else 0.0,
    }


def _agg_rp(name: str, name_index: dict, cutoff: str | None = None) -> dict | None:
    """Aggregate RP stats (all pitching appearances) for a player."""
    rows = name_index.get(_normalize_name(name), [])
    rows = [r for r in rows
            if r.get('did_play') == '1' or _safe_int(r.get('OUTS', 0)) > 0]
    if cutoff:
        rows = [r for r in rows if r['date'] >= cutoff]
    if not rows:
        return None

    g    = len(rows)
    sv   = sum(_safe_int(r.get('SV',   0)) for r in rows)
    hld  = sum(_safe_int(r.get('HLD',  0)) for r in rows)
    svhd = sum(_safe_int(r.get('SVHD', 0)) for r in rows)
    outs = sum(_safe_int(r.get('OUTS', 0)) for r in rows)
    er   = sum(_safe_int(r.get('ER',   0)) for r in rows)
    ph   = sum(_safe_int(r.get('P_H',  0)) for r in rows)
    pbb  = sum(_safe_int(r.get('P_BB', 0)) for r in rows)
    k    = sum(_safe_int(r.get('K',    0)) for r in rows)

    ip = outs / 3
    return {
        'G':      g,
        'SV':     sv,
        'HLD':    hld,
        'SVHD':   svhd,
        'SVHD_G': round(svhd / g, 3) if g else 0.0,
        'IP':     round(ip, 1),
        'OUTS':   outs,
        'ERA':    round((er  * 27) / outs, 2) if outs else 0.0,
        'WHIP':   round((ph + pbb) / ip,   2) if ip   else 0.0,
        'K9':     round((k   * 27) / outs, 2) if outs else 0.0,
    }


# ── Flag helpers ───────────────────────────────────────────────────────────

def _sp_flags(s: dict | None) -> list[str]:
    if s is None:
        return ['NO_DATA']
    flags = []
    if s['GS'] >= SP_MIN_GS_FLAG:
        if s['QS_rate'] < SP_FLAG_QS_RATE: flags.append('LOW_QS')
        if s['WHIP']    > SP_FLAG_WHIP:    flags.append('HIGH_WHIP')
        if s['K9']      < SP_FLAG_K9:      flags.append('LOW_K9')
    return flags


def _rp_flags(s: dict | None) -> list[str]:
    if s is None:
        return ['NO_DATA']
    flags = []
    if s['G'] >= RP_MIN_APP_FLAG:
        if s['SVHD'] < RP_FLAG_SVHD: flags.append('LOW_SVHD')
        if s['WHIP'] > RP_FLAG_WHIP: flags.append('HIGH_WHIP')
        if s['ERA']  > RP_FLAG_ERA:  flags.append('HIGH_ERA')
    return flags


# ── Main analysis functions ────────────────────────────────────────────────

def analyze_sps(stat_rows: list[dict], year: int | None = None) -> dict:
    """
    Full SP replacement analysis.
    Returns { rostered_sps, flagged, fa_sps, meta }.
    """
    creds  = get_espn()
    year   = year or creds.season_year
    today  = date.today()
    cut_14 = (today - timedelta(days=14)).isoformat()
    cut_28 = (today - timedelta(days=28)).isoformat()

    league   = _connect_league(year)
    my_team  = next(t for t in league.teams if t.team_id == creds.team_id)
    name_idx = _build_name_index(stat_rows, 'pitcher')

    # My SPs
    my_sps = [p for p in my_team.roster
               if 'SP' in p.eligibleSlots
               and not any(s in _HITTER_SLOTS for s in p.eligibleSlots)]

    rostered = []
    for p in my_sps:
        on_il, status = _player_status(p)
        s_all = _agg_sp(p.name, name_idx)
        rostered.append({
            'name':   p.name,
            'status': status,
            'on_il':  on_il,
            'season': s_all,
            'd28':    _agg_sp(p.name, name_idx, cut_28) or {},
            'd14':    _agg_sp(p.name, name_idx, cut_14) or {},
            'flags':  _sp_flags(s_all),
        })
    rostered.sort(key=lambda x: (0 if x['flags'] else 1, -(x['season'] or {}).get('QS', 0)))

    # FA SPs
    fa_raw = league.free_agents(size=300)
    fa_sps = []
    seen   = set()
    for p in fa_raw:
        if p.name in seen or 'SP' not in p.eligibleSlots:
            continue
        seen.add(p.name)
        if _is_on_il(p.injuryStatus or ''):
            continue
        s = _agg_sp(p.name, name_idx)
        if s is None or s['OUTS'] < SP_MIN_OUTS_FA:
            continue
        fa_sps.append({
            'name':   p.name,
            'team':   p.proTeam or '?',
            'season': s,
            'd28':    _agg_sp(p.name, name_idx, cut_28) or {},
            'd14':    _agg_sp(p.name, name_idx, cut_14) or {},
        })
    fa_sps.sort(key=lambda x: (-x['season']['QS'], x['season']['WHIP'], -x['season']['K9']))

    flagged = [r for r in rostered if r['flags'] and not r['on_il']]
    return {
        'rostered_sps': rostered,
        'flagged':      flagged,
        'fa_sps':       fa_sps,
        'meta':         {'team_name': my_team.team_name, 'today': today.isoformat(), 'year': year},
    }


def analyze_rps(stat_rows: list[dict], year: int | None = None) -> dict:
    """
    Full RP replacement analysis.
    Returns { rostered_rps, flagged, fa_rps, meta }.
    """
    creds  = get_espn()
    year   = year or creds.season_year
    today  = date.today()
    cut_14 = (today - timedelta(days=14)).isoformat()
    cut_28 = (today - timedelta(days=28)).isoformat()

    league   = _connect_league(year)
    my_team  = next(t for t in league.teams if t.team_id == creds.team_id)
    name_idx = _build_name_index(stat_rows, 'pitcher')

    # My RPs (pure RP — not SP-eligible, not hitter-eligible)
    my_rps = [p for p in my_team.roster
               if 'RP' in p.eligibleSlots
               and 'SP' not in p.eligibleSlots
               and not any(s in _HITTER_SLOTS for s in p.eligibleSlots)]

    rostered = []
    for p in my_rps:
        on_il, status = _player_status(p)
        s_all = _agg_rp(p.name, name_idx)
        rostered.append({
            'name':   p.name,
            'status': status,
            'on_il':  on_il,
            'season': s_all,
            'd28':    _agg_rp(p.name, name_idx, cut_28) or {},
            'd14':    _agg_rp(p.name, name_idx, cut_14) or {},
            'flags':  _rp_flags(s_all),
        })
    rostered.sort(key=lambda x: (0 if x['flags'] else 1, -(x['season'] or {}).get('SVHD', 0)))

    # FA RPs
    fa_raw = league.free_agents(size=300)
    fa_rps = []
    seen   = set()
    for p in fa_raw:
        if p.name in seen:
            continue
        seen.add(p.name)
        slots = p.eligibleSlots
        if 'RP' not in slots or 'SP' in slots:
            continue
        if _is_on_il(p.injuryStatus or ''):
            continue
        s = _agg_rp(p.name, name_idx)
        if s is None or s['OUTS'] < RP_MIN_OUTS_FA:
            continue
        fa_rps.append({
            'name':   p.name,
            'team':   p.proTeam or '?',
            'season': s,
            'd28':    _agg_rp(p.name, name_idx, cut_28) or {},
            'd14':    _agg_rp(p.name, name_idx, cut_14) or {},
        })
    fa_rps.sort(key=lambda x: (
        -x['season']['SVHD'],
        -x['season']['SVHD_G'],
         x['season']['WHIP'],
         x['season']['ERA'],
    ))

    flagged = [r for r in rostered if r['flags'] and not r['on_il']]
    return {
        'rostered_rps': rostered,
        'flagged':      flagged,
        'fa_rps':       fa_rps,
        'meta':         {'team_name': my_team.team_name, 'today': today.isoformat(), 'year': year},
    }

"""
Description: Shared statistical primitives used across the agent. Provides the
             single source of truth for deriving fantasy rate stats (OPS, ERA,
             WHIP, K/9) from accumulated counting-stat components, plus safe
             numeric coercion helpers. Previously these formulas were duplicated
             across valuation, projections, recommendations, and scoring.
Source Data: N/A — pure functions over in-memory numbers.
Outputs: N/A — utility module. Returns unrounded floats; callers round to taste.
"""


def safe_float(val) -> float:
    """Coerce any value to float, returning 0.0 on failure."""
    try:
        return float(val)
    except (TypeError, ValueError):
        return 0.0


def safe_int(val) -> int:
    """Coerce any value to int, returning 0 on failure."""
    try:
        return int(val)
    except (TypeError, ValueError):
        return 0


def derive_batting_rates(ab: float, h: float, bb: float, tb: float,
                         hbp: float = 0.0, sf: float = 0.0) -> dict[str, float]:
    """
    Derive OBP, SLG, and OPS from accumulated batting components.

    Returns unrounded floats: { "OBP", "SLG", "OPS" }.
    Components that would divide by zero yield 0.0 for that rate.
    """
    denom = ab + bb + hbp + sf
    obp = (h + bb + hbp) / denom if denom > 0 else 0.0
    slg = tb / ab if ab > 0 else 0.0
    return {"OBP": obp, "SLG": slg, "OPS": obp + slg}


def derive_pitching_rates(outs: float, er: float, p_h: float, p_bb: float,
                          k: float, no_ip_value: float = 0.0) -> dict[str, float]:
    """
    Derive IP, ERA, WHIP, and K/9 from accumulated pitching components.

    Returns unrounded floats: { "IP", "ERA", "WHIP", "K/9" }.

    Args:
        no_ip_value: value to use for ERA/WHIP/K/9 when no innings were pitched.
                     Defaults to 0.0; callers that want a "looks bad" sentinel
                     (e.g. free-agent ranking) can pass 99.0.
    """
    ip = outs / 3
    if ip <= 0:
        return {"IP": 0.0, "ERA": no_ip_value, "WHIP": no_ip_value, "K/9": no_ip_value}
    return {
        "IP":   ip,
        "ERA":  (er * 9) / ip,
        "WHIP": (p_h + p_bb) / ip,
        "K/9":  (k * 9) / ip,
    }

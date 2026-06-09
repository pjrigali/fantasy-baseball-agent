"""
Description: Interactive CLI for collecting and saving credentials to config.ini.
             Can import ESPN credentials automatically from the parent acn_repo/config.ini
             or accept manual input. Validates the ESPN connection before finishing.
Source Data: User input and/or acn_repo/config.ini (parent workspace).
Outputs: fantasy-baseball-agent/config.ini
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2]))

from agent.credentials import import_from_parent, save_config, validate_espn


def prompt(label: str, current: str = "", secret: bool = False) -> str:
    display = "[****]" if (secret and current) else (f"[{current}]" if current else "")
    suffix = f" {display}: " if display else ": "
    value = input(f"  {label}{suffix}").strip()
    return value if value else current


def run():
    print("\n=== Fantasy Baseball Agent — Credential Setup ===\n")

    sections: dict[str, dict[str, str]] = {}

    # --- Try auto-import from parent config ---
    imported = import_from_parent()

    if imported:
        espn = imported["espn"]
        print("Found existing credentials in acn_repo/config.ini.")
        use_existing = input("  Import ESPN credentials from there? [Y/n]: ").strip().lower()
        if use_existing in ("", "y", "yes"):
            sections["espn"] = espn
            print("  Imported: league_id, team_id, s2, swid.\n")
        else:
            sections["espn"] = {"s2": "", "swid": "", "league_id": "", "team_id": "", "season_year": ""}
    else:
        print("No parent config.ini found — enter credentials manually.\n")
        sections["espn"] = {"s2": "", "swid": "", "league_id": "", "team_id": "", "season_year": ""}

    # --- ESPN section ---
    print("[ESPN]")
    print("  To find espn_s2 and swid: log into ESPN Fantasy, open browser dev tools,")
    print("  go to Application > Cookies > espn.com and copy 'espn_s2' and 'SWID'.\n")

    e = sections["espn"]
    e["league_id"] = prompt("League ID", e.get("league_id", ""))
    e["team_id"]   = prompt("Your Team ID", e.get("team_id", ""))
    e["season_year"] = prompt("Season Year (e.g. 2026)", e.get("season_year", "2026"))
    e["swid"] = prompt("SWID cookie", e.get("swid", ""), secret=True)
    e["s2"]   = prompt("espn_s2 cookie", e.get("s2", ""), secret=True)
    sections["espn"] = e

    # --- Anthropic section (optional) ---
    print("\n[Anthropic]  (optional — required for AI analysis features)")
    anthropic_key = prompt("API key (leave blank to skip)")
    if anthropic_key:
        sections["anthropic"] = {"api_key": anthropic_key}

    # --- Save ---
    save_config(sections)
    print("\nSaved to config.ini.")

    # --- Validate ---
    print("Validating ESPN connection...")
    ok, msg = validate_espn()
    if ok:
        print(f"  OK: {msg}")
    else:
        print(f"  WARN: {msg}")
        print("  Credentials saved but connection test failed. Check your values and re-run.")

    print("\nSetup complete.\n")


if __name__ == "__main__":
    run()

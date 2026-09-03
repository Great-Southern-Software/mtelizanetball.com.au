#!/usr/bin/env python3
"""Pull Mt Eliza's FDNA draw, results and ladders from NetballConnect into data/fixtures.json.

NetballConnect has no public API. Its public draw/ladder pages are a React app over
https://api-netball.squadi.com, authenticated with a fixed public token that ships inside
the app bundle. This script re-reads that token from the bundle on every run, then calls
the same endpoints the public pages use. Standard library only, so it runs on a bare
GitHub Actions runner.

Environment overrides (all optional):
  FIXTURES_COMPETITION_KEY  NetballConnect competition uniqueKey (skips the name search)
  FIXTURES_COMPETITION_MATCH  regex used to pick the competition by name (default: saturday)
  FIXTURES_TEAM_PREFIX      team-name prefix that marks our teams (default: MENC)
  FIXTURES_YEAR             season year (default: current year in Melbourne)
"""
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

APP = "https://registration.netballconnect.com"
API = "https://api-netball.squadi.com"
FDNA_KEY = "b026e644-1e78-4805-a68b-1bd27962e8f3"
FDNA_NAME = "Frankston & District Netball Association"
# Their bot filter 403s Chrome-like agents unless client-hint headers are present;
# a Firefox agent is accepted as-is.
UA = "Mozilla/5.0 (X11; Linux x86_64; rv:130.0) Gecko/20100101 Firefox/130.0"
TZ = ZoneInfo("Australia/Melbourne")

OUT = Path(__file__).resolve().parent.parent / "data" / "fixtures.json"
TEAM_PREFIX = os.environ.get("FIXTURES_TEAM_PREFIX", "MENC")
COMP_MATCH = re.compile(os.environ.get("FIXTURES_COMPETITION_MATCH", "saturday"), re.I)


def http(url, token=None):
    headers = {"User-Agent": UA, "Accept": "application/json"}
    if token:
        headers["Authorization"] = token
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=60) as r:
        return r.read().decode("utf-8", "ignore")


def public_token():
    html = http(APP + "/")
    bundle = re.search(r'src="(/static/js/main\.[a-z0-9]+\.js)"', html).group(1)
    js = http(APP + bundle)
    return re.search(r'REACT_APP_DEFAULT_AUTH_TOKEN:"([0-9a-f]+)"', js).group(1)


def api(token, service, path, **params):
    query = urllib.parse.urlencode(params, safe="[],")
    return json.loads(http(f"{API}/{service}/{path}?{query}", token))


def pick_competition(token, year):
    override = os.environ.get("FIXTURES_COMPETITION_KEY")
    years = api(token, "common", "common/reference/year", organisationUniqueKey=FDNA_KEY, scope=1)
    year_ref = {y["name"]: y["id"] for y in years}
    for y in (year, year - 1):
        if str(y) not in year_ref:
            continue
        comps = api(token, "livescores", "competitions/list", organisationUniqueKey=FDNA_KEY, yearRefId=year_ref[str(y)])
        if override:
            comps = [c for c in comps if c["uniqueKey"] == override]
        else:
            comps = [c for c in comps if COMP_MATCH.search(c["name"])]
        if comps:
            comp = max(comps, key=lambda c: c["id"])
            return comp, y, year_ref[str(y)]
    sys.exit("No matching competition found on NetballConnect")


def tidy_division(name):
    """FDNA names divisions '<age> <grade>', which yields 'NetSet NetSet Pink'; drop the echo."""
    words = name.split()
    return " ".join(w for i, w in enumerate(words) if i == 0 or w != words[i - 1])


def local(iso):
    return datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(TZ)


def day_label(dt):
    return dt.strftime("%A %-d %B")


def time_label(dt):
    return dt.strftime("%-I:%M %p").lower().replace(":00", "")


def outcome(match, ours_is_team1):
    if match.get("matchStatus") != "ENDED":
        return ""
    us = match["team1Score"] if ours_is_team1 else match["team2Score"]
    them = match["team2Score"] if ours_is_team1 else match["team1Score"]
    if us == 0 and them == 0:
        return "P"  # played, no score recorded (NetSetGO)
    return "W" if us > them else "L" if us < them else "D"


def ordinal(n):
    suffix = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def shape_match(match, our_id, division_name):
    ours_is_team1 = match["team1Id"] == our_id
    us, them = (match["team1"], match["team2"]) if ours_is_team1 else (match["team2"], match["team1"])
    start = local(match["startTime"])
    court = match.get("venueCourt") or {}
    venue = court.get("venue") or {}
    opponent = ((them or {}).get("name") or "TBC").strip()
    bye = opponent.lower() == "bye"
    round_name = match["round"]["name"]
    return {
        "id": match["id"],
        "round": round_name,
        "division": division_name,
        "startIso": start.isoformat(),
        "date": day_label(start),
        "time": time_label(start),
        "opponent": opponent,
        "bye": bye,
        "home": ours_is_team1,
        "venue": venue.get("name") or "",
        "court": court.get("name") or "",
        "ourScore": match["team1Score"] if ours_is_team1 else match["team2Score"],
        "theirScore": match["team2Score"] if ours_is_team1 else match["team1Score"],
        "played": match.get("matchStatus") == "ENDED" and not bye,
        "outcome": "BYE" if bye else outcome(match, ours_is_team1),
        "finals": bool(match.get("isFinals")) or "final" in round_name.lower(),
    }


def main():
    now = datetime.now(TZ)
    year = int(os.environ.get("FIXTURES_YEAR", now.year))
    token = public_token()
    comp, season_year, year_ref = pick_competition(token, year)
    comp_key, comp_id = comp["uniqueKey"], comp["id"]
    print(f"Competition: {comp['name']} ({comp_id})")

    divisions = {d["id"]: tidy_division(d["name"]) for d in api(token, "livescores", "division", competitionKey=comp_key)}
    teams = [t for t in api(token, "livescores", "teams/enduser/list", competitionId=comp_key, organisationId=FDNA_KEY)
             if t["name"].strip().upper().startswith(TEAM_PREFIX.upper())]
    if not teams:
        sys.exit(f"No teams starting with '{TEAM_PREFIX}' in {comp['name']}")
    our_ids = {t["id"] for t in teams}
    print(f"Teams: {len(teams)}")

    rounds = api(token, "livescores", "round/matches", competitionId=comp_id, divisionId="",
                 teamIds="[" + ",".join(str(i) for i in sorted(our_ids)) + "]", ignoreStatuses="[1]")["rounds"]
    by_team = defaultdict(list)
    for rnd in rounds:
        for m in rnd["matches"]:
            for tid in (m["team1Id"], m["team2Id"]):
                if tid in our_ids:
                    by_team[tid].append(shape_match(m, tid, divisions.get(rnd["divisionId"], "")))
    for ms in by_team.values():
        ms.sort(key=lambda m: m["startIso"])

    # A team's current division is wherever its most recent fixture sits (FDNA regrades mid-season).
    current_div = {}
    for tid, ms in by_team.items():
        if ms:
            current_div[tid] = ms[-1]["division"]
    div_ids = {name: did for did, name in divisions.items()}
    ladders = {}
    for name in sorted(set(current_div.values())):
        did = div_ids.get(name)
        if did is None:
            continue
        lad = api(token, "livescores", "teams/ladder/v2", divisionIds=did, competitionKey=comp_key,
                  filteredOutCompStatuses=1, showForm=1, sportRefId=1)
        rows = [] if lad.get("isHidden") else [
            {"rank": int(r["rk"]), "name": r["name"].strip(), "us": r["id"] in our_ids,
             "P": int(r["P"]), "W": int(r["W"]), "L": int(r["L"]), "D": int(r["D"]),
             "F": int(r["F"]), "A": int(r["A"]), "PTS": int(r["PTS"]),
             "pct": r.get("goalAverage") or ""}
            for r in lad.get("ladders", [])]
        rows.sort(key=lambda r: r["rank"])
        ladders[name] = {"hidden": bool(lad.get("isHidden")) or not rows, "rows": rows}
        print(f"Ladder {name}: {'hidden' if ladders[name]['hidden'] else str(len(rows)) + ' rows'}")

    now_iso = now.isoformat()
    out_teams = []
    for t in sorted(teams, key=lambda t: t["name"]):
        ms = by_team.get(t["id"], [])
        played = [m for m in ms if m["played"]]
        upcoming = [m for m in ms if not m["played"] and not m["bye"] and m["startIso"] > now_iso]
        div = current_div.get(t["id"], "")
        ladder = ladders.get(div, {"hidden": True, "rows": []})
        rank = next((r["rank"] for r in ladder["rows"] if r["name"] == t["name"].strip()), None)
        short = t["name"].strip()[len(TEAM_PREFIX):].strip()
        out_teams.append({
            "id": t["id"],
            "name": t["name"].strip(),
            "shortName": short,
            "slug": re.sub(r"[^a-z0-9]+", "-", short.lower()).strip("-"),
            "division": div,
            "ladderRank": rank,
            "ladderSize": len(ladder["rows"]),
            "ladderLabel": f"{ordinal(rank)} of {len(ladder['rows'])}" if rank else "",
            "won": sum(m["outcome"] == "W" for m in played),
            "lost": sum(m["outcome"] == "L" for m in played),
            "drawn": sum(m["outcome"] == "D" for m in played),
            "played": len(played),
            "scored": any(m["outcome"] in ("W", "L", "D") for m in played),
            "nextMatch": upcoming[0] if upcoming else None,
            "lastMatch": played[-1] if played else None,
            "ladder": ladder,
            "matches": ms,
        })

    # Cross-team views: everything still to come, grouped by day, and the last day of results.
    upcoming_by_day = defaultdict(list)
    for t in out_teams:
        for m in t["matches"]:
            if not m["played"] and not m["bye"] and m["startIso"] > now_iso:
                upcoming_by_day[m["date"]].append({**m, "team": t["shortName"], "teamSlug": t["slug"]})
    upcoming = [{"date": d, "matches": sorted(v, key=lambda m: (m["startIso"], m["team"]))}
                for d, v in sorted(upcoming_by_day.items(), key=lambda kv: kv[1][0]["startIso"])]

    latest = None
    played_all = [({**m, "team": t["shortName"], "teamSlug": t["slug"]}) for t in out_teams for m in t["matches"] if m["played"]]
    if played_all:
        last_iso = max(m["startIso"] for m in played_all)[:10]
        results = sorted((m for m in played_all if m["startIso"][:10] == last_iso), key=lambda m: (m["startIso"], m["team"]))
        latest = {"date": results[0]["date"], "results": results}

    doc = {
        "updatedIso": now_iso,
        "updated": now.strftime("%-d %B %Y, %-I:%M %p").replace("AM", "am").replace("PM", "pm"),
        "association": FDNA_NAME,
        "competition": {"name": comp["name"], "key": comp_key, "id": comp_id, "year": season_year},
        "netballConnectUrl": f"{APP}/liveScoreSeasonFixture?organisationKey={FDNA_KEY}&yearId={year_ref}"
                             f"&competitionUniqueKey={comp_key}&competitionId={comp_key}",
        "ladderUrl": f"{APP}/liveScorePublicLadder?organisationKey={FDNA_KEY}&yearId={year_ref}"
                     f"&competitionUniqueKey={comp_key}&competitionId={comp_key}",
        "seasonComplete": not upcoming,
        "upcoming": upcoming,
        "latest": latest,
        "teams": out_teams,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {OUT} ({OUT.stat().st_size // 1024} KB), {sum(len(t['matches']) for t in out_teams)} matches, "
          f"{sum(len(d['matches']) for d in upcoming)} upcoming")


if __name__ == "__main__":
    main()

import requests
import re
import math
from datetime import datetime

# -----------------------
# CONFIG
# -----------------------
RUNWAYS = {
    "RCTP": [{"name":"05L","hdg":50},{"name":"23R","hdg":230}],
    "RCSS": [{"name":"10","hdg":100},{"name":"28","hdg":280}]
}

# -----------------------
# FETCH DATA
# -----------------------
def fetch_taf(station):
    url = f"https://aviationweather.gov/api/data/taf?ids={station}&format=raw"
    return requests.get(url).text.strip()

def fetch_metar(station):
    url = f"https://aviationweather.gov/api/data/metar?ids={station}&format=raw"
    return requests.get(url).text.strip()

def fetch_notam(station):
    # prototype API（可能不完整）
    url = f"https://aviationweather.gov/api/data/notam?ids={station}"
    return requests.get(url).text

# -----------------------
# PARSER
# -----------------------
def extract_worst(taf):

    vis = [int(v) for v in re.findall(r"\b\d{4}\b", taf)]
    ceil = [int(c[3:]) for c in re.findall(r"(BKN\d{3}|OVC\d{3})", taf)]
    wx = re.findall(r"(TS|RA|SN|FG)", taf)

    return {
        "vis": min(vis) if vis else 9999,
        "ceiling": min(ceil) if ceil else 999,
        "wx": set(wx)
    }

def parse_metar_wind(metar):

    m = re.search(r"(\d{3}|VRB)(\d{2})KT", metar)
    if not m:
        return None, None

    wd = 0 if m.group(1)=="VRB" else int(m.group(1))
    ws = int(m.group(2))

    return wd, ws

# -----------------------
# RUNWAY / WIND
# -----------------------
def wind_component(wd, ws, hdg):

    angle = abs(wd - hdg)
    angle = min(angle, 360-angle)

    rad = math.radians(angle)

    cross = ws * math.sin(rad)
    head = ws * math.cos(rad)

    return round(cross,1), round(head,1)

# -----------------------
# NOTAM
# -----------------------
def parse_notam(text):

    notams = text.split("\n\n")
    result = []

    for n in notams:

        if "RWY" in n and "CLSD" in n:
            t = "RWY_CLOSED"
        elif "ILS" in n and "U/S" in n:
            t = "ILS_U/S"
        else:
            continue

        result.append({
            "type": t,
            "raw": n
        })

    return result

# -----------------------
# DECISION
# -----------------------
def alternate_check(vis, ceiling):

    return vis >= 2000 and ceiling >= 800

def fuel_model(trend, alt_ok):

    score = 0
    if trend["vis_down"]: score+=1
    if trend["ceiling_down"]: score+=1
    if trend["new_ts"]: score+=2
    if not alt_ok: score+=3

    if score>=4: return "HIGH"
    elif score>=2: return "MEDIUM"
    else: return "LOW"

# -----------------------
# MAIN
# -----------------------
def analyze_station(station, prev_taf=None):

    print(f"\n===== {station} =====")

    taf = fetch_taf(station)
    metar = fetch_metar(station)
    notam_raw = fetch_notam(station)

    print("TAF:", taf)
    print("METAR:", metar)

    # worst
    worst = extract_worst(taf)

    # trend
    trend = {"vis_down":False,"ceiling_down":False,"new_ts":False}

    if prev_taf:
        prev = extract_worst(prev_taf)
        trend = {
            "vis_down": worst["vis"] < prev["vis"],
            "ceiling_down": worst["ceiling"] < prev["ceiling"],
            "new_ts": ("TS" in worst["wx"] and "TS" not in prev["wx"])
        }

    print("Trend:", trend)

    # wind
    wd, ws = parse_metar_wind(metar)

    if wd is not None:
        print("\nRunway Wind:")
        for r in RUNWAYS.get(station, []):
            cw, hw = wind_component(wd, ws, r["hdg"])
            print(f"{r['name']} | XW:{cw} HW:{hw}")

    # alternate
    alt_ok = alternate_check(worst["vis"], worst["ceiling"])
    print("\nAlternate:", "OK" if alt_ok else "NOT OK")

    # NOTAM
    notams = parse_notam(notam_raw)

    if notams:
        print("\nNOTAM Impact:")
        for n in notams:
            print(n["type"], ":", n["raw"][:80])
    else:
        print("\nNOTAM: None critical")

    # fuel
    fuel = fuel_model(trend, alt_ok)
    print("\nFuel Risk:", fuel)

    return taf

# -----------------------
# RUN
# -----------------------
if __name__ == "__main__":

    stations = input("Enter ICAO (comma): ").split(",")

    history = {}

    for s in stations:
        s = s.strip().upper()
        prev = history.get(s)
        taf = analyze_station(s, prev)
        history[s] = taf

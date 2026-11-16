#!/usr/bin/env python3
"""Sækir veðurathuganir (Veðurstofa Íslands) og spá (Open-Meteo) og skrifar data.json.

Notar aðeins staðalsafn Python. Keyrt daglega af GitHub Actions.
"""
import csv, io, json, math, sys, time, urllib.parse, urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VEDUR = "https://api.vedur.is/weather"
METEO = "https://api.open-meteo.com/v1/forecast"
OBS_DAYS = 30        # fjöldi daga af mælingum
MAX_KM = 60          # hámarksfjarlægð í veðurstöð
LAPSE = 0.0065       # °C á metra
UA = {"User-Agent": "isklifur (github.com/gunnarmg/isklifur)"}


def get(url, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.status, r.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return 404, ""
            err = e
        except Exception as e:  # net villur
            err = e
        time.sleep(2 * (i + 1))
    raise RuntimeError(f"Tókst ekki að sækja {url}: {err}")


def hav(a, b, c, d):
    p = math.pi / 180
    x = math.sin((c - a) * p / 2) ** 2 + math.cos(a * p) * math.cos(c * p) * math.sin((d - b) * p / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(x))


_cache = {}


def station_days(sid, d_from, d_to):
    """Dagsmeðalhiti stöðvar: {'YYYY-MM-DD': t}. None ef engin gögn."""
    if sid in _cache:
        return _cache[sid]
    q = urllib.parse.urlencode({"station_id": sid, "day_from": d_from, "day_to": d_to,
                                "parameters": "basic", "format": "csv"})
    status, text = get(f"{VEDUR}/observations/aws/day?{q}")
    out = None
    if status == 200 and text.strip():
        out = {}
        for row in csv.DictReader(io.StringIO(text), delimiter=";"):
            t = (row.get("t") or "").strip()
            if t:
                out[row["time"][:10]] = float(t)
    _cache[sid] = out
    time.sleep(0.15)
    return out


def main():
    crags = json.loads((ROOT / "scripts" / "crags.json").read_text(encoding="utf-8"))
    today = datetime.now(timezone.utc).date()
    start = today - timedelta(days=OBS_DAYS)
    all_days = [(start + timedelta(days=i)).isoformat() for i in range(OBS_DAYS + 1)]

    status, text = get(f"{VEDUR}/stations?active=true&station_type=sj")
    stations = json.loads(text)

    rows = []
    for c in crags:
        cand = sorted(({**s, "d": hav(c["lat"], c["lon"], s["lat"], s["lon"])} for s in stations
                       if s.get("lat") is not None and s.get("lon") is not None), key=lambda s: s["d"])
        cand = [s for s in cand if s["d"] < MAX_KM][:6]
        use = []
        for s in cand:
            o = station_days(s["station"], all_days[0], all_days[-1])
            if o and len(o) > 5:
                use.append((s, o))
            if len(use) == 4:
                break
        T = []
        for d in all_days:
            w = t = 0.0
            for s, o in use:
                if d in o:
                    ww = 1 / (s["d"] + 5)
                    w += ww
                    t += ww * (o[d] + ((s.get("ele") or 0) - c["ele"]) * LAPSE)
            T.append(round(t / w, 1) if w else None)
        rows.append({**c, "st": [f"{s['name']} ({s['d']:.0f}/{(s.get('ele') or 0):.0f})" for s, _ in use], "T": T})

    # Síðasti dagur þar sem a.m.k. helmingur svæða hefur mælingu
    last = max((i for i in range(len(all_days)) if sum(r["T"][i] is not None for r in rows) >= len(rows) / 2), default=-1)
    if last < 7:
        sys.exit("Of fáar mælingar bárust frá Veðurstofunni; data.json ekki uppfært.")
    obs_dates = all_days[: last + 1]
    for r in rows:
        T = r["T"][: last + 1]
        prev = next((v for v in T if v is not None), 0.0)
        for i, v in enumerate(T):       # fylla í göt með síðasta gildi
            if v is None:
                T[i] = prev
            prev = T[i]
        r["T"] = T

    q = urllib.parse.urlencode({
        "latitude": ",".join(str(c["lat"]) for c in crags),
        "longitude": ",".join(str(c["lon"]) for c in crags),
        "elevation": ",".join(str(c["ele"]) for c in crags),
        "daily": "temperature_2m_mean,precipitation_sum",
        "past_days": 7, "forecast_days": 8, "timezone": "GMT"}, safe=",")
    status, text = get(f"{METEO}?{q}")
    fc = json.loads(text)
    if isinstance(fc, dict):
        fc = [fc]
    if status != 200 or len(fc) != len(rows):
        sys.exit("Spá frá Open-Meteo barst ekki rétt; data.json ekki uppfært.")
    fc_dates = fc[0]["daily"]["time"]
    for r, f in zip(rows, fc):
        r["fT"] = f["daily"]["temperature_2m_mean"]
        r["fR"] = [v or 0 for v in f["daily"]["precipitation_sum"]]
        if any(v is None for v in r["fT"]):
            sys.exit("Göt í spá; data.json ekki uppfært.")

    data = {"generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
            "obsDates": obs_dates, "fcDates": fc_dates, "crags": rows}
    (ROOT / "data.json").write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Skrifaði data.json: mælingar {obs_dates[0]}..{obs_dates[-1]}, spá til {fc_dates[-1]}, {len(rows)} svæði")


if __name__ == "__main__":
    main()

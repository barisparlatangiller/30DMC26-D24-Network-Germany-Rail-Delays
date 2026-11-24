"""
Day 24 · IST: what really happened on Monday 23 Nov 2026 — real-time delays from gtfs.de (the day's realtime feed, same timetable
version as PLAN), matched to every PLAN trip by trip_id and to its stations by scheduled time.
Missing stations inside a trip take the last known delay; trips with no realtime record keep 0 and are flagged.
Writes the "ist" case into build/whatif.json (same layout as the WHAT IF cases) and the real line names (e.g. ICE 12).
  python pipeline/ist.py raw/de-gtfsde-2026-11-23-delays.csv build/
"""
import sys, json
import pandas as pd
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from whatif import stats


def mins(s):
    if not isinstance(s, str) or len(s) < 16:
        return None
    return int(s[11:13]) * 60 + int(s[14:16]) + int(s[17:19]) / 60


def main(src, b):
    P = json.load(open(b + "/plan.json")); WI = json.load(open(b + "/whatif.json"))
    ids = {t["id"] for t in P["trips"]}
    d = pd.read_csv(src, dtype=str, usecols=["route", "trip_id", "stop_sequence", "scheduled_arrival", "scheduled_departure",
                                              "arrival_delay_min", "departure_delay_min", "stop_status"])
    d = d[d.trip_id.isin(ids)].copy()
    d["sa"] = d.scheduled_arrival.map(mins); d["sd"] = d.scheduled_departure.map(mins)
    d["ad"] = pd.to_numeric(d.arrival_delay_min, errors="coerce"); d["dd"] = pd.to_numeric(d.departure_delay_min, errors="coerce")
    G = {k: g for k, g in d.groupby("trip_id")}
    dl, dd, skip, names, has = [], [], [], {}, []
    for t in P["trips"]:
        g = G.get(t["id"]); n = len(t["s"])
        a_, d_, sk = [None] * n, [None] * n, []
        if g is not None:
            names[t["id"]] = g.route.dropna().iloc[0] if g.route.notna().any() else t["n"]
            for k in range(n):
                ma = g[(g.sa.sub(t["a"][k]).abs() < 0.6)] if k else g.iloc[0:0]
                md = g[(g.sd.sub(t["d"][k]).abs() < 0.6)]
                r = md if len(md) else ma
                if len(r):
                    rr = r.iloc[0]
                    a_[k] = rr.ad if pd.notna(rr.ad) else rr.dd
                    d_[k] = rr.dd if pd.notna(rr.dd) else rr.ad
                    if rr.stop_status == "skipped":
                        sk.append(k)
        has.append(int(g is not None and any(v is not None and pd.notna(v) for v in a_ + d_)))
        last = 0.0
        for k in range(n):                          # carry the last known delay forward; never earlier than on time
            if a_[k] is None or pd.isna(a_[k]):
                a_[k] = last
            if d_[k] is None or pd.isna(d_[k]):
                d_[k] = a_[k]
            a_[k] = max(0.0, float(a_[k])); d_[k] = max(a_[k] if k else 0.0, float(d_[k])); last = d_[k]
        dl.append([round(v) for v in a_]); dd.append([round(v) for v in d_]); skip.append(sk)
    st = stats(P, dl, dd)
    st["with_realtime"] = sum(has)
    WI["cases"]["ist"] = {"stats": st, "dl": dl, "dd": dd, "skip": skip}
    json.dump(WI, open(b + "/whatif.json", "w"), separators=(",", ":"))
    for t in P["trips"]:
        if t["id"] in names:
            t["n"] = names[t["id"]]
    json.dump(P, open(b + "/plan.json", "w"), ensure_ascii=False, separators=(",", ":"))
    print(json.dumps({k: v for k, v in st.items() if k != "series"}), "peak late", max(st["series"]))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])

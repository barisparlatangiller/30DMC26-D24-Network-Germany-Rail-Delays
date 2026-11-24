"""
Day 24 · 12 Stunden. Ein Land. Ein Schienennetz.
PLAN: long-distance trains (gtfs.de "latest-fv-free", DELFI) running on Monday 23 Nov 2026 between 06:00 and 18:00.
Each trip → its stations (platform stops folded into their parent station, consecutive duplicates dropped) with scheduled
arrival/departure in minutes after midnight, and a smooth path (centripetal Catmull-Rom through the stations, 10 points
per hop) with a scheduled time at every vertex (constant speed between stations, standing still while dwelling).
  python pipeline/plan.py GTFS_DIR build/
"""
import sys, json, math
import numpy as np
import pandas as pd

DATE, DOW = 20261123, "monday"
T0, T1 = 6 * 60, 18 * 60


def mins(s):
    h, m, x = (int(v) for v in s.split(":")); return h * 60 + m + x / 60


def cr(P, n=10, alpha=0.5):
    """centripetal Catmull-Rom through P (list of (lon,lat)); returns points and the index of each original point"""
    if len(P) < 3:
        out = []; idx = []
        for i in range(len(P) - 1):
            for k in range(n):
                f = k / n; out.append((P[i][0] + (P[i + 1][0] - P[i][0]) * f, P[i][1] + (P[i + 1][1] - P[i][1]) * f))
            idx.append(len(out) - n)
        idx.append(len(out)); out.append(P[-1]); return out, idx
    Q = [(2 * P[0][0] - P[1][0], 2 * P[0][1] - P[1][1])] + list(P) + [(2 * P[-1][0] - P[-2][0], 2 * P[-1][1] - P[-2][1])]
    k = math.cos(math.radians(51))
    def tj(ti, a, b):
        return ti + max(1e-6, math.hypot((b[0] - a[0]) * k, b[1] - a[1])) ** alpha
    out, idx = [], []
    for i in range(1, len(Q) - 2):
        p0, p1, p2, p3 = (np.array(Q[j]) for j in (i - 1, i, i + 1, i + 2))
        t0 = 0; t1 = tj(t0, p0, p1); t2 = tj(t1, p1, p2); t3 = tj(t2, p2, p3)
        idx.append(len(out))
        for s in range(n):
            t = t1 + (t2 - t1) * s / n
            A1 = (t1 - t) / (t1 - t0) * p0 + (t - t0) / (t1 - t0) * p1
            A2 = (t2 - t) / (t2 - t1) * p1 + (t - t1) / (t2 - t1) * p2
            A3 = (t3 - t) / (t3 - t2) * p2 + (t - t2) / (t3 - t2) * p3
            B1 = (t2 - t) / (t2 - t0) * A1 + (t - t0) / (t2 - t0) * A2
            B2 = (t3 - t) / (t3 - t1) * A2 + (t - t1) / (t3 - t1) * A3
            C = (t2 - t) / (t2 - t1) * B1 + (t - t1) / (t2 - t1) * B2
            out.append((float(C[0]), float(C[1])))
    idx.append(len(out)); out.append(tuple(P[-1]))
    return out, idx


def main(d, out):
    cal = pd.read_csv(d + "/calendar.txt", dtype={"service_id": str}); cdt = pd.read_csv(d + "/calendar_dates.txt", dtype={"service_id": str})
    on = set(cal[(cal[DOW] == 1) & (cal.start_date <= DATE) & (cal.end_date >= DATE)].service_id)
    on |= set(cdt[(cdt.date == DATE) & (cdt.exception_type == 1)].service_id); on -= set(cdt[(cdt.date == DATE) & (cdt.exception_type == 2)].service_id)
    tr = pd.read_csv(d + "/trips.txt", dtype=str); tr = tr[tr.service_id.isin(on)]
    ro = pd.read_csv(d + "/routes.txt", dtype=str).set_index("route_id")
    ag = pd.read_csv(d + "/agency.txt", dtype=str).set_index("agency_id")
    stp = pd.read_csv(d + "/stops.txt", dtype=str)
    stp["lat"] = stp.stop_lat.astype(float); stp["lon"] = stp.stop_lon.astype(float)
    par = {r.stop_id: (r.parent_station if isinstance(r.parent_station, str) else r.stop_id) for r in stp.itertuples()}
    S = stp.set_index("stop_id")
    st = pd.read_csv(d + "/stop_times.txt", dtype={"trip_id": str, "stop_id": str})
    st = st[st.trip_id.isin(set(tr.trip_id))].sort_values(["trip_id", "stop_sequence"])
    stations, trips = {}, []
    for tid, g in st.groupby("trip_id", sort=False):
        seq = []
        for r in g.itertuples():
            p = par.get(r.stop_id, r.stop_id); a, dep = mins(r.arrival_time), mins(r.departure_time)
            if seq and seq[-1][0] == p:
                seq[-1][2] = dep; continue
            seq.append([p, a, dep])
        if len(seq) < 2 or seq[-1][1] < T0 or seq[0][2] > T1:
            continue
        rt = tr[tr.trip_id == tid].iloc[0]; R = ro.loc[rt.route_id]
        name = (R.route_short_name or "").strip()
        pts = [(round(S.loc[p].lon, 5), round(S.loc[p].lat, 5)) for p, _, _ in seq]
        for (p, _, _), (lo, la) in zip(seq, pts):
            stations.setdefault(p, {"id": p, "name": S.loc[p].stop_name, "lon": lo, "lat": la, "n": 0}); stations[p]["n"] += 1
        path, idx = cr(pts)
        # vertex times: dwell at stations, constant speed along each hop
        ts = [0.0] * len(path)
        for i in range(len(seq) - 1):
            a, b = idx[i], idx[i + 1]; d0, a1 = seq[i][2], seq[i + 1][1]
            L = [0.0]
            for k in range(a, b):
                q = path[k + 1] if k + 1 < len(path) else path[b]
                L.append(L[-1] + math.hypot((q[0] - path[k][0]) * 0.63, q[1] - path[k][1]))
            for j, k in enumerate(range(a, b)):
                ts[k] = d0 + (a1 - d0) * (L[j] / L[-1] if L[-1] else 0)
        ts[-1] = seq[-1][1]
        trips.append({"id": tid, "n": name, "ag": ag.loc[R.agency_id].agency_name if R.agency_id in ag.index else "", "head": S.loc[seq[-1][0]].stop_name,
                      "s": [x[0] for x in seq], "a": [round(x[1], 2) for x in seq], "d": [round(x[2], 2) for x in seq], "vi": idx,
                      "p": [[round(x, 5), round(y, 5)] for x, y in path], "t": [round(v, 2) for v in ts]})
    json.dump({"date": "2026-11-23", "t0": T0, "t1": T1, "stations": list(stations.values()), "trips": trips}, open(out + "/plan.json", "w"), ensure_ascii=False, separators=(",", ":"))
    print(len(trips), "trips;", len(stations), "stations;", sum(len(t["p"]) for t in trips), "vertices")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])

"""
Day 24 · WHAT IF: four closures on Monday 23 Nov 2026, 08:00–09:00, alone or in any combination (16 cases incl. none).
  K  Köln Hbf closed            F  Frankfurt (Main) Hbf closed        H  Hannover Hbf closed
  S  Köln–Rhein/Main high-speed line closed (Siegburg – Montabaur – Limburg Süd – Frankfurt Flughafen): trains on it
     detour via the Rhine valley, +45 min, and skip Montabaur and Limburg Süd
A small event simulation, in time order over all trains:
  · a closed station holds every train that would arrive or leave in the window until 09:00
  · after reopening it lets trains leave one by one, 2 min apart (platforms and switches clear the backlog)
  · on every track section A→B trains keep 3 min apart, so a late train delays the ones behind it
  · a late train runs 4% faster than scheduled between stations and keeps at most 1 min of each stop
    (the timetable's recovery margins), and never leaves before its scheduled time
  · trains turn around: a train ending at a station hands its set to the next train of the same kind starting there
    15–90 min later (first come, first served; the feed has no vehicle data, so these rotations are estimated),
    which cannot leave earlier than 15 min after the late arrival
It is a model of how delays travel, not a forecast; real dispatching (cancellations, reroutes, waiting for connections) is left out.
  python pipeline/whatif.py build/
"""
import sys, json, heapq, itertools

W0, W1 = 8 * 60, 9 * 60
NODE = {"K": "aa8", "F": "bxxg", "H": "5vyl"}
HSL = {"2e9m", "1v6z", "1ngz", "e3i6", "8z0", "bnzf"}      # Siegburg, Montabaur, Limburg Süd, Frankfurt Flughafen, Köln/Bonn Flughafen, Köln Messe/Deutz
HSL_SKIP = {"1v6z", "1ngz"}
DETOUR = 45
HEAD, REL, FAST, DWELL = 3.0, 2.0, 0.04, 1.0
TURN, TURN_MAX = 15.0, 90.0


def rotations(P):
    T = P["trips"]; ends = {}
    for i, t in enumerate(T):
        ends.setdefault((t["s"][-1], t["n"]), []).append((t["a"][-1], i))
    starts = {}
    for j, t in enumerate(T):
        starts.setdefault((t["s"][0], t["n"]), []).append((t["d"][0], j))
    nxt, prv = {}, {}
    for key, E in ends.items():
        S = sorted(starts.get(key, [])); used = set()
        for ta, i in sorted(E):
            for td, j in S:
                if j in used or j == i:
                    continue
                if ta + TURN <= td <= ta + TURN_MAX:
                    nxt[i] = j; prv[j] = i; used.add(j); break
    return nxt, prv


def run(P, combo):
    closed = {NODE[c] for c in combo if c in NODE}
    hsl = "S" in combo
    T = P["trips"]; n = len(T)
    arr = [list(t["a"]) for t in T]; dep = [list(t["d"]) for t in T]; skip = [[0] * len(t["s"]) for t in T]
    last_edge, last_rel = {}, {}
    rot_n, prv = P["_rot"]
    start = [t["d"][0] for t in T]
    heap = [(T[i]["d"][0], i, 0) for i in range(n) if i not in prv]; heapq.heapify(heap)
    while heap:
        _, i, k = heapq.heappop(heap)
        t = T[i]; s = t["s"]
        if k >= len(s) - 1:
            continue
        a = arr[i][k] if k else start[i]
        d = max(t["d"][k], a + min(DWELL, t["d"][k] - t["a"][k])) if k else max(t["d"][0], start[i])
        if s[k] in closed:
            if W0 <= d < W1 or (W0 <= a < W1):
                d = max(d, W1)
            if W1 <= d < W1 + 180:
                d = max(d, last_rel.get(s[k], -1e9) + REL); last_rel[s[k]] = d
        e = (s[k], s[k + 1]); d = max(d, last_edge.get(e, -1e9) + HEAD)
        if d > dep[i][k] + 1e-6 or k == 0 or True:
            pass
        dep[i][k] = d; last_edge[e] = d
        run_t = t["a"][k + 1] - t["d"][k]
        late = d - t["d"][k]
        nxt = d + run_t * (1 - FAST) if late > 0 else d + run_t
        if s[k + 1] in closed and W0 <= nxt < W1:
            nxt = W1                                       # waits outside the station until it reopens
        if hsl and s[k] in HSL and s[k + 1] in HSL and W0 <= d < W1 + 0:
            nxt += DETOUR
            if s[k + 1] in HSL_SKIP:
                skip[i][k + 1] = 1
        arr[i][k + 1] = max(nxt, t["a"][k + 1])
        if k + 1 < len(s) - 1:
            dep[i][k + 1] = max(arr[i][k + 1], t["d"][k + 1])
            heapq.heappush(heap, (dep[i][k + 1], i, k + 1))
        elif i in rot_n:                                   # end of the run: the set turns around
            j = rot_n[i]; start[j] = max(T[j]["d"][0], arr[i][k + 1] + TURN)
            heapq.heappush(heap, (start[j], j, 0))
    dl = [[round(arr[i][k] - T[i]["a"][k]) for k in range(len(T[i]["s"]))] for i in range(n)]
    for i in range(n):
        dep[i][-1] = arr[i][-1]
    dep = [[max(dep[i][k], T[i]["d"][k]) for k in range(len(T[i]["s"]))] for i in range(n)]
    dd = [[round(dep[i][k] - T[i]["d"][k]) for k in range(len(T[i]["s"]))] for i in range(n)]
    dd = [[0 if T[i]["d"][k] == T[i]["a"][k] and k == len(T[i]["s"]) - 1 else v for k, v in enumerate(x)] for i, x in enumerate(dd)]
    return dl, dd, skip


def stats(P, dl, dd):
    T = P["trips"]
    hit = sum(1 for i in range(len(T)) if max(max(dl[i]), max(dd[i])) >= 5)
    final = sum(max(0, dl[i][-1]) for i in range(len(T)))
    late15 = sum(1 for i in range(len(T)) if max(dl[i]) >= 15)
    mx = max(max(x) for x in dl)
    # trains running ≥ 5 min late, every 10 minutes
    ser = []
    for tm in range(P["t0"], P["t1"] + 1, 10):
        c = 0
        for i, t in enumerate(T):
            if not (t["d"][0] <= tm <= t["a"][-1]):
                continue
            k = max(j for j in range(len(t["s"])) if t["d"][j] <= tm or j == 0)
            if max(dd[i][k], dl[i][min(k + 1, len(t["s"]) - 1)]) >= 5:
                c += 1
        ser.append(c)
    return {"trains_hit": hit, "late15": late15, "delay_min": final, "max": mx, "series": ser}


def main(b):
    P = json.load(open(b + "/plan.json"))
    P["_rot"] = rotations(P); print("estimated turnarounds:", len(P["_rot"][0]))
    out = {"window": [W0, W1], "codes": {"K": "Köln Hbf closed", "F": "Frankfurt (Main) Hbf closed", "H": "Hannover Hbf closed", "S": "Köln–Rhein/Main high-speed line closed"}, "cases": {}}
    for r in range(0, 5):
        for combo in itertools.combinations("KFHS", r):
            key = "".join(combo) or "none"
            dl, dd, sk = run(P, combo)
            st = stats(P, dl, dd)
            out["cases"][key] = {"stats": st, "dl": dl, "dd": dd, "skip": [[k for k, v in enumerate(x) if v] for x in sk]}
            print(f"{key:5s} hit {st['trains_hit']:4d}  ≥15 {st['late15']:4d}  final-delay {st['delay_min']:6d} min  max {st['max']} min")
    json.dump(out, open(b + "/whatif.json", "w"), separators=(",", ":"))


if __name__ == "__main__":
    main(sys.argv[1])

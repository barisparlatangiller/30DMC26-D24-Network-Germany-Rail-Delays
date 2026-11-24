/* Day 24 · 12 Stunden. Ein Land. Ein Schienennetz. */
"use strict";
const $ = s => document.querySelector(s), $$ = s => [...document.querySelectorAll(s)];
const NODES = { K: { id: "aa8", name: "Köln Hbf" }, F: { id: "bxxg", name: "Frankfurt (M) Hbf" }, H: { id: "5vyl", name: "Hannover Hbf" }, S: { id: null, name: "Köln–Rhein/Main line" } };
const HSL = ["bnzf", "2e9m", "1v6z", "1ngz", "e3i6"];
const S = { t: 360, play: false, speed: 12, mode: "plan", on: new Set(), case: "none" };
let P, WI, map, overlay, ST = {}, last = performance.now();

function col(d) {                                   // delay (min) → colour
  if (d < 5) return [46, 139, 132]; if (d < 15) return [224, 163, 43]; if (d < 30) return [210, 85, 63]; return [142, 42, 109];
}
const hhmm = m => `${String(Math.floor(m / 60)).padStart(2, "0")}:${String(Math.floor(m % 60)).padStart(2, "0")}`;
const key = () => { const k = ["K", "F", "H", "S"].filter(c => S.on.has(c)).join(""); return k || "none"; };

// per-scenario vertex times and colours: scheduled time + delay interpolated between the stops
function build() {
  S.case = S.mode === "whatif" ? key() : S.mode === "ist" ? "ist" : "none";
  const C = WI.cases[S.case];
  for (let i = 0; i < P.trips.length; i++) {
    const t = P.trips[i], dl = C.dl[i], dd = C.dd[i], n = t.p.length;
    const ts = new Float32Array(n), dv = new Float32Array(n);
    for (let k = 0; k < t.s.length - 1; k++) {
      const a = t.vi[k], b = t.vi[k + 1], t0 = t.t[a], t1 = t.vi[k + 1] < n ? t.t[b] : t.t[n - 1];
      for (let v = a; v < b; v++) { const f = t1 > t0 ? (t.t[v] - t0) / (t1 - t0) : 0; const d = dd[k] + (dl[k + 1] - dd[k]) * f; dv[v] = d; ts[v] = t.t[v] + d; }
    }
    ts[n - 1] = t.t[n - 1] + dl[t.s.length - 1]; dv[n - 1] = dl[t.s.length - 1];
    t._ts = ts; t._dv = dv; t._start = t.d[0] + dd[0]; t._end = ts[n - 1];
    t._col = Array.from(dv, d => col(d));
  }
  S.ver = (S.ver || 0) + 1;
  chaos(); layers();
}
function heads() {
  const out = [];
  for (const t of P.trips) {
    if (S.t < t._start || S.t > t._end) continue;
    const ts = t._ts; let lo = 0, hi = ts.length - 1;
    while (hi - lo > 1) { const m = (lo + hi) >> 1; if (ts[m] <= S.t) lo = m; else hi = m; }
    const f = ts[hi] > ts[lo] ? (S.t - ts[lo]) / (ts[hi] - ts[lo]) : 0, a = t.p[lo], b = t.p[hi];
    const k = t.vi.findIndex((v, j) => j + 1 < t.vi.length && v <= lo && lo < t.vi[j + 1]);
    out.push({ t, pos: [a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f], d: t._dv[lo], next: k >= 0 ? t.s[k + 1] : t.s[t.s.length - 1] });
  }
  return out;
}
function layers() {
  if (!overlay) return;
  const H = heads(), closed = S.mode === "whatif" ? [...S.on].filter(c => c !== "S") : [];
  const inWin = S.t >= WI.window[0] && S.t < WI.window[1];
  overlay.setProps({ layers: [
    new deck.TripsLayer({ id: "trails", data: P.trips, getPath: t => t.p, getTimestamps: t => t._ts, getColor: t => t._col, currentTime: S.t, trailLength: 22,
      widthMinPixels: 3.2, capRounded: true, jointRounded: true, fadeTrail: true, opacity: 0.9, updateTriggers: { getTimestamps: S.ver, getColor: S.ver } }),
    new deck.ScatterplotLayer({ id: "closed", data: closed.map(c => ST[NODES[c].id]), getPosition: s => [s.lon, s.lat], getRadius: 1, radiusUnits: "pixels",
      getLineColor: [210, 85, 63, inWin ? 255 : 90], stroked: true, filled: false, lineWidthMinPixels: 3, radiusMinPixels: inWin ? 16 + 4 * Math.sin(performance.now() / 180) : 12 }),
    new deck.ScatterplotLayer({ id: "heads", data: H, getPosition: h => h.pos, getFillColor: h => col(h.d), getLineColor: [255, 255, 255], stroked: true,
      lineWidthMinPixels: 1.2, radiusMinPixels: 4.2, radiusMaxPixels: 7, getRadius: 3000, pickable: true })
  ] });
  $("#time").textContent = hhmm(S.t); $("#slider").value = S.t;
}
function chaos() {
  const c = WI.cases[S.case].stats, base = WI.cases.none.stats;
  if (!$("#chaos")) return;
  $("#chaos").innerHTML = [[c.trains_hit, "trains ≥ 5 min late"], [c.late15, "≥ 15 min late"], [c.delay_min.toLocaleString("en-US"), "delay minutes at arrival"], [c.max + "'", "worst delay"]]
    .map(([b, s]) => `<div><b>${b}</b><span>${s}</span></div>`).join("");
  const cv = $("#spark"), g = cv.getContext("2d"), W = cv.width, Hh = cv.height, mx = Math.max(6, ...WI.cases.ist.stats.series, ...WI.cases.KFHS.stats.series);
  g.clearRect(0, 0, W, Hh);
  const pl = (ser, color, fill) => { g.beginPath(); ser.forEach((v, i) => { const x = i / (ser.length - 1) * W, y = Hh - 6 - v / mx * (Hh - 16); i ? g.lineTo(x, y) : g.moveTo(x, y); });
    if (fill) { g.lineTo(W, Hh - 6); g.lineTo(0, Hh - 6); g.fillStyle = fill; g.fill(); } else { g.strokeStyle = color; g.lineWidth = 3; g.stroke(); } };
  pl(base.series, "#b9b2a6");
  if (S.case !== "ist") { g.setLineDash([6, 6]); pl(WI.cases.ist.stats.series, "rgba(142,42,109,.6)"); g.setLineDash([]); }
  pl(c.series, null, S.case === "ist" ? "rgba(142,42,109,.22)" : "rgba(210,85,63,.28)"); pl(c.series, S.case === "ist" ? "#8e2a6d" : "#d2553f");
  const x = (S.t - 360) / 720 * W; g.strokeStyle = "#1f2328"; g.lineWidth = 2; g.beginPath(); g.moveTo(x, 0); g.lineTo(x, Hh); g.stroke();
  const w0 = (WI.window[0] - 360) / 720 * W, w1 = (WI.window[1] - 360) / 720 * W; g.fillStyle = "rgba(31,35,40,.06)"; g.fillRect(w0, 0, w1 - w0, Hh);
}
function setMode(m) {
  S.mode = m; $$("#modes button").forEach(b => b.classList.toggle("on", b.dataset.m === m));
  $("#wi").style.display = m === "plan" ? "none" : ""; $("#closures").style.display = $("#cl-h").style.display = m === "whatif" ? "" : "none";
  $("#sparknote").innerHTML = m === "ist" ? "Trains running at least 5 min late on the real Monday (purple) against the timetable (grey)." : "Trains running at least 5 min late in this scenario (red). Dashed purple: the real Monday. Grey: the timetable.";
  $("#mode-l").textContent = m === "whatif" ? `WHAT IF · ${key() === "none" ? "no closure" : [...S.on].map(c => NODES[c].name).join(" + ")}` : m === "ist" ? "IST · real delays, Mon 23 Nov" : "PLAN";
  if (map.getLayer("hsl")) map.setPaintProperty("hsl", "line-opacity", m === "whatif" && S.on.has("S") ? 0.9 : 0);
  build();
}
function tick(now) {
  const dt = Math.min(0.1, (now - last) / 1000); last = now;
  if (S.play) { S.t += dt * S.speed; if (S.t > 1080) S.t = 360; }
  layers(); if (S.mode === "whatif" && S.play) chaos();
  requestAnimationFrame(tick);
}
async function init() {
  [P, WI] = await Promise.all([fetch("data/plan.json").then(r => r.json()), fetch("data/whatif.json").then(r => r.json())]);
  for (const s of P.stations) ST[s.id] = s;
  map = new maplibregl.Map({ container: "map", style: "https://basemaps.cartocdn.com/gl/positron-nolabels-gl-style/style.json", center: [10.3, 51.1], zoom: 5.6, minZoom: 4.5, maxZoom: 11, attributionControl: { compact: true } });
  map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
  await new Promise(r => map.on("load", r));
  map.fitBounds([[5.9, 47.3], [15.0, 55.0]], { padding: 20, duration: 0 });
  // the network: every station-to-station hop any train uses, as a quiet grey line
  const seen = new Set(), feats = [];
  for (const t of P.trips) for (let k = 0; k < t.s.length - 1; k++) {
    const id = t.s[k] < t.s[k + 1] ? t.s[k] + t.s[k + 1] : t.s[k + 1] + t.s[k]; if (seen.has(id)) continue; seen.add(id);
    feats.push({ type: "Feature", geometry: { type: "LineString", coordinates: t.p.slice(t.vi[k], t.vi[k + 1] + 1) }, properties: {} });
  }
  map.addSource("net", { type: "geojson", data: { type: "FeatureCollection", features: feats } });
  map.addLayer({ id: "net", type: "line", source: "net", paint: { "line-color": "#b8b2a8", "line-width": ["interpolate", ["linear"], ["zoom"], 5, 0.8, 9, 2], "line-opacity": 0.7 }, layout: { "line-cap": "round", "line-join": "round" } });
  const hsl = HSL.map(id => ST[id]).filter(Boolean);
  map.addSource("hsl", { type: "geojson", data: { type: "Feature", geometry: { type: "LineString", coordinates: hsl.map(s => [s.lon, s.lat]) } } });
  map.addLayer({ id: "hsl", type: "line", source: "hsl", paint: { "line-color": "#d2553f", "line-width": 5, "line-dasharray": [1.2, 1], "line-opacity": 0 } });
  const big = P.stations.filter(s => s.n >= 60);
  map.addSource("st", { type: "geojson", data: { type: "FeatureCollection", features: big.map(s => ({ type: "Feature", geometry: { type: "Point", coordinates: [s.lon, s.lat] }, properties: { name: s.name.replace(/^S\+U |, Hauptbahnhof| Hauptbahnhof| Hbf$|Hamburg, /g, "").replace(" (Main)", "").replace(" Flughafen Fernbahnhof", " Flughafen"), n: s.n } })) } });
  map.addLayer({ id: "st", type: "circle", source: "st", paint: { "circle-radius": ["interpolate", ["linear"], ["get", "n"], 60, 2.5, 180, 4.5], "circle-color": "#ffffff", "circle-stroke-color": "#5b6470", "circle-stroke-width": 1.2 } });
  const CITIES = [["bm0i", "Berlin"], ["abk", "Hamburg"], ["4mig", "München"], ["aa8", "Köln"], ["bxxg", "Frankfurt"], ["5vyl", "Hannover"], ["31qb", "Mannheim"]];
  for (const n of P.stations) if (/Leipzig Hbf|Stuttgart Hbf|Nürnberg Hbf|Dortmund Hbf|Dresden Hbf|Bremen Hbf|Erfurt Hbf|Kassel-Wilhelmshöhe|Basel Bad|Karlsruhe Hbf/.test(n.name)) CITIES.push([n.id, n.name.replace(/ Hbf| Bad Bf|-Wilhelmshöhe/g, "").replace(/^.*, /, "")]);
  for (const [id, name] of CITIES) { const s = ST[id]; if (!s) continue; const el = document.createElement("div"); el.className = "city"; el.textContent = name;
    new maplibregl.Marker({ element: el, anchor: "left", offset: [7, -9] }).setLngLat([s.lon, s.lat]).addTo(map); }
  overlay = new deck.MapboxOverlay({ interleaved: false, layers: [] }); map.addControl(overlay);
  // closure buttons
  $("#closures").innerHTML = Object.entries(NODES).map(([c, n]) => `<button data-c="${c}"><b>${c === "S" ? "LINE" : "HUB"}</b>${n.name}</button>`).join("");
  $$("#closures button").forEach(b => b.onclick = () => { const c = b.dataset.c; S.on.has(c) ? S.on.delete(c) : S.on.add(c); b.classList.toggle("on"); setMode("whatif"); });
  $("#ist-b").disabled = false; $("#ist-b").title = "";
  $$("#modes button").forEach(b => b.onclick = () => { if (b.dataset.m === "whatif" && S.on.size === 0) { S.on.add("K"); $('#closures [data-c="K"]').classList.add("on"); } setMode(b.dataset.m); });
  $("#pp").onclick = () => { S.play = !S.play; $("#pp").textContent = S.play ? "❚❚" : "▶"; };
  $("#slider").oninput = e => { S.t = +e.target.value; chaos(); };
  $("#speed").onchange = e => { S.speed = +e.target.value; };
  const tip = $("#tip");
  overlay.setProps({ getTooltip: null });
  map.on("mousemove", e => {
    const o = overlay.pickObject({ x: e.point.x, y: e.point.y, radius: 6, layerIds: ["heads"] });
    if (!o?.object) { tip.style.display = "none"; return; }
    const h = o.object, nx = ST[h.next];
    tip.innerHTML = `<b>${h.t.n || "Train"} → ${h.t.head}</b><br>next: ${nx ? nx.name : "–"}<br>${Math.round(h.d) >= 1 ? `<span style="color:#ffb59f">+${Math.round(h.d)} min</span>` : "on time"}${h.t.ag && !/DB Fernverkehr/.test(h.t.ag) ? ` · ${h.t.ag}` : ""}`;
    tip.style.left = e.point.x + 14 + "px"; tip.style.top = e.point.y + 14 + "px"; tip.style.display = "block";
  });
  $("#wi").style.display = "none";
  build();
  const qs = new URLSearchParams(location.search);
  if (qs.get("film")) document.body.classList.add("film");
  window.APP = { S, P, WI, setMode, build, chaos, layers, map: () => map, NODES };
  window.READY = true;
  requestAnimationFrame(tick);
}
init();

# 12 Stunden. Ein Land. Ein Schienennetz.

**#30DayMapChallenge 2026 · Day 24 · Network**

👉 **Live map:** https://barisparlatangiller.github.io/30DMC26-D24-Network-Germany-Rail-Delays/

Germany's long-distance trains on Monday 23 November 2026, 06:00–18:00 (841 trips, 432 stations), animated on a light map.
**PLAN** shows the timetable; **IST (the real delays of that Monday, gtfs.de real-time: 588 of 841 trains ≥5 min late, 10,591 delay minutes) and WHAT IF** lets you close Köln Hbf, Frankfurt (Main) Hbf, Hannover Hbf and/or the Köln–Rhein/Main high-speed line
for one hour (08:00–09:00), alone or in any combination (16 cases), and watch the delay travel through the network.

The WHAT IF layer is a small event simulation (holds at closed stations and a 2-min release queue, 3-min headways per section,
4% recovery, estimated train-set turnarounds, +45 min detour via the Rhine valley). A gentle model, not a forecast.

Data: gtfs.de / DELFI e.V. long-distance feed (CC BY 4.0) · basemap © CARTO © OpenStreetMap contributors.
Pipeline: `pipeline/plan.py` → `pipeline/whatif.py` → `docs/data/`.

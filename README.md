# Campus Cluster: Simulating Stanford Student Traffic to Understand Campus Congestion

**Student:** Dina Hashash | hashash@stanford.edu
**Course:** CS348K - Visual Computing Systems, Spring 2026

**📄 Final writeup → [FINAL_REPORT.md](FINAL_REPORT.md)**

---

## Checkpoint 1 Updates (May 8, 2026)

### General Updates

The data scraping pipeline and barebones simulation pipline are built and run. A simulation of a school day with 6,700 simulated students comletes with 11.3M trajectory samples. Here is where each pipeline code lives: 

1. **`scrapers/scrape_courses.py`** - pulls 2025-2026 course data from the Explore Courses api
2. **`scrapers/get_buildings.py`** - pulls unique building strings
3. **`pipeline/tag_courses.py`** - filters courses_2025_2026.csv to just Spring courses, tags each section with `school` and `level` buckets, identifies "anchor" sections w linked discussion sections
4. **`pipeline/generate_population.py`** - produces 6,700 students with year, school, dorm assignment (by year-eligibility), travel mode, and target unit load
5. **`pipeline/assign_schedules.py`** - senior-priority student-driven matching with school x level affinity weighting, with a bit of slack or current enrollment levels
6. **`sim/load_data.py`** - joins population + schedules + buildings into per-agent trip plans
7. **`sim/runner.py`** - multi-agent state machine (home → moving → in_class → between → done) with edge-progress movement, right now running from 06:00–22:00 at 10s timesteps ... still a bit buggy, need to play with states/go home behavior

The barebones simulation has plausible results: empty class buildings pre-8am, ramps up through morning passing periods, winds down through evening. 

### Project questions

**Q1: Where and when does congestion peak on Stanford's main campus during a simulated Spring 2026 weekday?**

- *Experiment:* Run the 6,700-agent simulation Monday-Friday with real the simulated schedules. Compute Level of Service (m²/person) per edge per minute. Identify edges and times where LoS drops to D or worse (≤2.2 m²/person).
- *Success criterion:* I am able to produce (a) a time series of peak campus congestion, (b) a ranked list of the top 20 most-congested (edge, time) pairs, and (c) a list of the most-affected agents by exposure time to level D or worse congestion. Congestion should be plausible, i.e. peaks during passing periods. If the evaluator runs on a time with no movement, it should report zero congestion.

**Q2: Can a small set of schedule shifts (≤5 large lectures, ±15/30/60 minutes) reduce peak campus congestion by ≥20% without creating a new peak exceeding 80% of the original peak at a different time?**

- *Experiment:* For each of the top 5 largest lectures by enrollment, move the start time by three values (±15, ±30, ±60 min). Compare peak campus congestion vs the baseline.
- *Success criterion:* At least one shift achieves the threshold (≥20% reduction, no new peak above 80% of original).

**Q3 (stretch): Do learned departure-time/routing agents reduce congestion exposure compared to naive shortest-path agents?**

- *Experiment:* Train an RL agent on the same trajectory-generation task. Compare total congestion exposure (sum over agents of time-weighted fraction-on-Level-D) vs the baseline. 
- *Success criterion:* Exposure with RL agents ≤ 90% of baseline.

### Congestion metrics

Congestion as defined in the proposal (edge / agent / campus) is implemented in `eval/congestion.py`:

- **Edge-minute LoS:** for each (edge, minute) bucket, count agents in `moving` state on that edge. Compute m²/person as `edge_area_m² / agent_count` where `edge_area_m² = edge_length * assumed_path_width` (right now putting path width = 3m default, should change later when separating walking/biking paths, etc). LoS thresholds from Highway Capacity Manual: A ≥3.7, B 2.8–3.7, C 2.2–2.8, D 1.5–2.2, E 0.7–1.5, F <0.7.
- **Agent congestion exposure:** for each agent, the fraction of their `moving` time spent on edges at LoS D or worse, weighted by exposure duration.
- **Peak campus congestion:** for each minute of the day, sum of agent-weighted congestion exposures contributing during that minute. Peak = max over the day.

### Baseline evals

1. **Empty trajectory:** zero agents move so peak congestion = 0.
2. **Single-agent trajectory:** one agent walks alone → peak congestion ≈ 0.
3. **Fake crowd:** 250 agents placed on one 50m edge for one minute = LoS F detected, peak congestion is large and at the correct time.

Run command:

```bash
python eval/congestion.py --baselines-only  # baselines only
python eval/congestion.py  # baselines + real trajectory (currently buggy)
```

Baseline results:

| baseline | moving samples | peak congested | peak time | top edge LoS | notes |
|---|---|---|---|---|---|
| empty trajectory | 0 | 0 | — | — | no congested edge-minutes, no exposures |
| single agent (50m edge, 10 min) | 20 | 0 | — | A | 150 m²/p, exposure_frac = 0 |
| fake crowd (250 on 50m edge, 1 min) | 250 | 250 | 00:30 | F | 0.6 m²/p, all 250 fully exposed |

### Where things are 

- **Code:** `pipeline/`, `sim/`, `eval/` - pipeline scripts, simulator, evaluator
- **Data:** `data/raw/courses_2025_2026.csv` (scraped), `data/processed/` (pipeline outputs)
- **Results:** `outputs/trajectory.parquet`, `outputs/congestion_baseline.json`
- **Visualization (kind of boof rn):** `outputs/heatmap_*.png`, `outputs/animation.mp4`

### Next Steps from here

- Schedule optimizer
- Behavioral layers (lunch trips, coffee runs): designed but not implemented
- RL agents
- Improve visualization 

---

## Checkpoint 2 Updates (May 22, 2026)

### General Updates

- **Fixed two simulator bugs**: a shared path-cache list was being changed by `agent.path.pop(0)` during traversal, so each agent drained the cached trip for everyone else on the same route + the "same-OSM-node fast path" was firing from the `home` state, so agents would teleport to their first class if dorm and class building would snap to the same graph node. With these cahnges --> sim stopped shwoing "peak congested = 0" 
- **Implemented behavior layers**: Coffee, lunch, return-home-for-long-gaps, library/study, dinner, gym. Still might need to tune these in the future.
- **Added multimodal routing**: Put Stanford's OSM walk + bike networks into one graph with `walk_ok` / `bike_ok` edge flags and mode-specific routing weights.
- **Better visual**: Now have a `purpose` tag, so you can see each agent's purpose for movement as they go.

### Q1: Where and when does congestion peak?

**Answered.** Top-line numbers from a 6,700-agent Monday at 5s sampling, with the latest sim:

| metric | value |
|---|---|
| moving samples recorded | 2,587,589 |
| unique agents observed moving | 6,528 |
| unique edges seen | 3,482 |
| congested edge-minutes (LoS D or worse, m²/person < 2.2) | 5,158 |
| peak campus congestion | 5,637 agents @ 13:25 |

**Figure A - Per-minute campus congestion across the day.**

![Figure A](outputs/cp2_congestion_timeseries.png)

Lunch (13:15–13:30) first. Secondary peaks at morning passing periods, late-afternoon class transitions (14:45–15:00, 16:45–17:00), and gym/dinner wave (17:00–17:15).

**Table B - Top 10 most congested (edge, time) pairs.** _Full 20 with raw `u, v` node IDs in `outputs/cp2_top20_edges.csv`._

| time | nearest_landmark | landmark_dist_m | n_agents | edge_length_m | m²/person | LoS |
|---|---|---|---|---|---|---|
| 13:22 | Panda Express | 33.9 | 70 | 3.4 | 0.10 | F |
| 13:23 | Panda Express | 33.9 | 69 | 3.4 | 0.10 | F |
| 11:52 | STLC Building | 44.2 | 76 | 3.8 | 0.10 | F |
| 13:24 | Panda Express | 33.9 | 63 | 3.4 | 0.11 | F |
| 13:26 | Main Quad | 25.2 | 84 | 4.7 | 0.11 | F |
| 10:22 | STLC Building | 44.2 | 66 | 3.8 | 0.12 | F |
| 12:22 | STLC Building | 44.2 | 58 | 3.8 | 0.13 | F |
| 13:27 | Main Quad | 25.2 | 69 | 4.7 | 0.14 | F |
| 11:22 | STLC Building | 44.2 | 52 | 3.8 | 0.15 | F |
| 11:50 | Main Quad | 25.2 | 59 | 4.7 | 0.16 | F |

`landmark_dist_m` is the haversine distance from the edge midpoint to the named landmark, so "Panda Express, 33.9m" means the edge is in the Tresidder/food-court area but not exactly at the building. Clusters that emerge: **Tresidder food court** (lunchtime crowd), **STLC / SAPP corridor** (engineering quad, hourly class transitions), and **Main Quad** (passing-period flow through the center).

Caveat: most of list is of sub-5m OSM artifact edges. Qualitative peaks (times of day) are correct; the specific "worst edge" assignment is a bit misleading - need to determine how to handle this.

**Table C - Top 10 most exposed agents by congestion-time exposure.** _Full 20 in `outputs/cp2_top20_exposed_agents.csv`._

| agent_id | dorm | school | mode | year | moving_time_s | congested_time_s | exposure_frac |
|---|---|---|---|---|---|---|---|
| 4187 | Donner | hs_humanities | bike | 1 | 9450 | 6090 | 0.644 |
| 2062 | Larkin | engineering | bike | 1 | 8010 | 5160 | 0.644 |
| 302 | Trancos | engineering | bike | 3 | 4500 | 2880 | 0.64 |
| 5422 | Columbae | hs_humanities | bike | 2 | 4770 | 2880 | 0.604 |
| 99 | Mars | hs_humanities | electric | 4 | 4410 | 2580 | 0.585 |
| 4623 | Larkin | hs_social | bike | 1 | 10950 | 5940 | 0.542 |
| 6368 | Donner | hs_interdisc | bike | 1 | 12210 | 6570 | 0.538 |
| 4028 | EVGR | hs_social | bike | 3 | 6750 | 3630 | 0.538 |
| 6450 | Crothers | hs_social | bike | 1 | 12150 | 6510 | 0.536 |
| 3093 | Rinconada | engineering | bike | 1 | 8580 | 4560 | 0.531 |

All top-exposed agents are bikers -- bikes traverse more edges per minute (so they show up on more (edge, minute) buckets). Dorms cluster around central-campus complexes (Stern: Donner, Larkin; Wilbur: Trancos, Rinconada).

**Figure D - Moving agents over the day, by trip purpose.**

![Figure D](outputs/cp2_moving_by_purpose.png)

### Q2: Can ≤5 schedule shifts reduce peak congestion ≥20%?

**Answered — and the answer is no.** Within the tested lever set (top-5 Wednesday lectures × ±15/30/60 min shifts), peak congestion cannot be reduced by the 20% threshold the CP1 success criterion called for.

**Setup.** I ran the sim on Wednesday because that day's the only one that hits both class cadences (M/W classes meet on Wed AND W/F classes also meet on Wed) so it has the highest baseline traffic of any weekday. The W_baseline peak is **5,908 agents at 13:25** (4.8% higher than Monday's 5,637 — sanity check). Target reduction: 20% → new peak ≤ 4,726.

**Top-5 lectures targeted (by enrollment, Wednesday-meeting):**

| # | section | n | building | original time |
|---|---|---|---|---|
| 1 | CS 224R | 555 | NVIDIA Auditorium | 09:30–10:50 |
| 2 | ECON 43 | 306 | Bishop Auditorium | 10:30–12:20 |
| 3 | CS 106B | 264 | Hewlett 200 | 13:30–14:20 |
| 4 | CS 229 / STATS 229 | 249 | NVIDIA Auditorium | 15:00–16:20 |
| 5 | CS 221 | 246 | Hewlett 200 | 10:30–12:20 |

**Single-shift sweep.** 30 individual (lecture, shift) experiments, plus 3 extra after substituting CS 109 in for CS 229 (see *Infeasibility* below). Full table in `outputs/q2/W_results_table.csv`; here are the best 6 of 23 feasible:

| lecture | shift | new peak | new peak time | delta | success? |
|---|---|---|---|---|---|
| CS 106B | −30 min | 5,353 | 13:25 | **−9.4%** | no |
| CS 106B | −15 min | 5,350 | 13:25 | −9.4% | no |
| CS 106B | −60 min | 5,413 | 13:25 | −8.4% | no |
| CS 109 | −30 min | 5,762 | 13:25 | −2.5% | no |
| CS 109 | −60 min | 5,762 | 13:25 | −2.5% | no |
| CS 109 | −15 min | 5,761 | 13:25 | −2.5% | no |

Across all 23 feasible shifts, the peak **never moves from 13:25** and the best single-shift result is −9.4%.

**Combined-shift experiments.** Since no single shift met the threshold, I stacked the best per-lecture shifts into combined sims:

| experiment | shifts applied | new peak | new peak time | delta |
|---|---|---|---|---|
| W_baseline | (none) | 5,908 | 13:25 | — |
| best single (CS 106B −15) | 1 shift | 5,353 | 13:25 | −9.4% |
| `W_combined_best4` | CS 224R −30, ECON 43 −60, CS 106B −15, CS 221 +30 | 5,272 | 13:25 | −10.8% |
| `W_combined_best5` | + CS 109 −30 (replacing infeasible CS 229) | **5,151** | 13:25 | **−12.8%** |

So even moving five of the top-5 simultaneously gets only to −12.8%. **The 20% threshold is not achievable with this lever set.**

**Marginal value of each lecture's shift** (how much it contributes when added to the combined):

- CS 106B: ~9.4 pp (carries the experiment)
- CS 109: ~2.0 pp
- CS 224R + ECON 43 + CS 221 combined: ~1.4 pp (basically noise)

**Two lectures (CS 106B + CS 109) account for almost all the achievable reduction.** They're the two classes whose original start times sit closest to the 13:25 peak, and they meet in Hewlett 200 + NVIDIA — both near the Tresidder lunch corridor.

**Infeasibility.** 13 of the 36 attempted shifts were marked infeasible due to real-Stanford room conflicts (NOT a sim bug). The interesting case:

- **CS 229 has zero feasible shifts.** Negative shifts collide with CS 109 in NVIDIA Auditorium (1:30–2:50 PM). Positive shifts collide with MS&E 472 also in NVIDIA (4:30 PM start). NVIDIA is fully packed around CS 229's slot within ±60 min.
- **Cross-listing bug caught during this work:** CS 229 / STATS 229 are the same physical meeting registered under two subject codes. The room-conflict check originally flagged STATS 229 as blocking CS 229's positive shifts — a false positive. Fix in `pipeline/q2_optimizer.py:find_cross_listings()`: sections sharing exact `(building, days, start_time, end_time)` are treated as one class.

**Interpretation.** The 13:25 peak is **structurally driven by lunch-time pedestrian flow**, not by the arrival/departure waves of any single lecture. Lectures very close to 13:25 (CS 106B at 13:30, CS 109 at 13:30) contribute most; lectures farther away contribute almost nothing. To meaningfully reduce the lunch peak, you'd need to target the *lunch behavior model* (eat-on-campus rate, dining-hall distribution) rather than shift class times.

**Comparison visualizations.** Two side-by-side animations + time-series overlays were rendered for visual comparison:

- [outputs/q2/W_comparison_W_baseline_vs_W_shift_CS-106B-LEC-01_-15min.png](outputs/q2/W_comparison_W_baseline_vs_W_shift_CS-106B-LEC-01_-15min.png) and [.mp4](outputs/q2/W_comparison_W_baseline_vs_W_shift_CS-106B-LEC-01_-15min.mp4) — best single shift
- [outputs/q2/W_comparison_W_baseline_vs_W_combined_best5.png](outputs/q2/W_comparison_W_baseline_vs_W_combined_best5.png) and [.mp4](outputs/q2/W_comparison_W_baseline_vs_W_combined_best5.mp4) — best 5-shift combined

**Q2 success criterion result:** ❌ NOT met. **Q2 finding result:** ✅ a clean negative result with a defensible mechanistic explanation.

### Q3 (stretch): RL departure / routing agents

Not currently in scope for this quarter.

### Where things are 

**Done:** full simulation pipeline, multi-layered behavior model, multimodal routing, congestion eval at three levels (edge / agent / campus), demo animation, three eval baselines still passing (empty / single agent / fake crowd).

**Not done:**
- Q2
- Nicer interactive visualization (hopefully 3D, this one looks flat and sad)
- Sit outside and get a baseline of an actual passing period :0
- RL agents (Q3)

### Run commands

```bash
python pipeline/tag_courses.py
python pipeline/generate_population.py
python pipeline/assign_schedules.py
python pipeline/assign_behaviors.py 
python sim/runner.py --n 6700 --day Monday
python eval/congestion.py
python scratch/viz_animation.py
```

---

## Summary

I propose buildilng a simulation of ~7,000 Stanford undergraduate students navigating campus throughout a real school day, using real course schedules from Explore Courses and campus geography from OpenStreetMap. The output is a recorded visualization showing agent movement as a density heatmap over the campus path network, alongside graphs showing whne and where congestion peaks. I also plan to run a simple schedule optimizer, shifting large lectures by bracketed maounts and measuuring the effect on peak congestion to produce a concrete result. Time allowing, I plan to expand the students to RL agents that learn to choose departure times and routes to arrive within a comfortable window (10 min early to 5 min late) while avoiding congestion. This will help me observe if congestion drops when everyone navigates intelligently.

---

## Inputs and Outputs

**Inputs:**
- Stanford campus path network (OpenStreetMap or Google Maps)
- Real course schedule data: building, time, enrollment (Explore Courses, onCourse, simpleEnroll)
- Undergraduate housing data (dorm locations, class year breakdown)

**Outputs:**
- Visualization: agent positions, path density heatmap, time scrubber
- Congestion metric curves over the simulation day (9am–7pm)
- Schedule optimization table

**Definition of congestion:**
I'll define congestion at three levels. At the edge level, congestion is measured as space per person on each path segment (m²/person). An edge is congested when it falls below 2.2 m²/person, as defined as the Level of Service metric. At the agent level, congestion exposure is the time-weighted fraction of each agent's trip spent on Level D or worse edges. At the campus level, the optimization target is peak campus congestion: the maximum over all timesteps of the sum of agent-weighted congestion exposure. This measures how many minutes agents are in uncomfortable crowding conditions, and how severe that crowding is.

---

## Task List

### Core task list

**Environment and baseline**
- Pull Stanford campus paths from OpenStreetMap
- Tag key buildings: classrooms, dorms, dining, libraries, gym
- Scrape Explore Courses for Spring 2026 - building, enrollment, times, recording status - save to a CSV
- Assign ~7,000 agents to dorms by class year and dorm capacity
- Give each agent a class schedule (12-20 units, no time conflicts, weighted by real enrollment data), and assign them as a walker, biker, or e-biker with respective travel times
- Get a shortest-path simulation running end-to-end on 10 agents first, then scale up

**Full simulation + visualization**
- Scale to 7,000 agents
- Run full simulated day (7:00am-8:00pm) and save trajectory data
- Build playback visualization with time scrubber and heatmap
- Produce first congestion graphs

**Behavioral layers + optimization**
- Add realistic behaviors (Lunch, return home, morning coffee, skipping lectures)
- Schedule optimizer: shift largest courses ±15, ±30, and ±60 minutes, run simulation for each, compare peak congestion

**Nice to haves**
- Add RL agents that learn to choose departure times and routes to arrive within a comfortable window of class start time
- Compare naive "shortest-path" students with these agents

---

## Expected Deliverables and Evaluation

**Demo:** A playback of the simulation with a time scrubber, where you can see dots flow across Stanford as time goes from 7am to 8pm. The heatmap is red to show high levels of density.

**Graphs:** 
- Congestion over time
- Optimization table and how each changes congestion
- If implemented, how RL agents compare to naive agents

**Success means:**
1. The simulation produces a plausible campus traffic pattern: peak congestion towards passing periods, less towards large class times
2. At least one schedule change that meaningfully reduces peak campus congestion by ≥20% without creating a new peak exceeding 80% of the original peak at another time
3. Behavioral additionals visibly change the congestion in ways that make intutive sense (i.e., if coffee behavior is added, CoDA becomes more busy in the morning, and early afternoon)

---

## Biggest Risks

**Explore Courses API access or format changes**
I need class data in order to build the simulation model. I plan to scrape and save to CSV on day 1. All subsequent work uses the local file.

**Simulation too slow**
The simulation can slow down as I scale up to more agents, hopefully will be ok with vectorized position updates. Worst case will drop number of agents proportionally.

**No ground-truth validation data**
Use qualitative validation (do peaks occur at the same time as I usually experience on campus?) and sensitivity analysis (do results hold under parameter perturbation?) rather than claiming quantitative accuracy against real-world counts.

**RL agents**
If RL agents do not work, I will still have the shortest path agents and their behavior to fall back on.

---

## What I Need Help With

- Is the Level of Service framework (m²/person) the right congestion model for a graph simulation, or is there something better that captures the same thing?
- For the RL component, is a custom Gymnasium environment the right choice?

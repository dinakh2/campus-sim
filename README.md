# Campus Cluster: Simulating Stanford Student Traffic to Understand Campus Congestion

**Student:** Dina Hashash | hashash@stanford.edu  
**Course:** CS348K - Visual Computing Systems, Spring 2026

---

## Checkpoint 1 Updates (May 8, 2026)

### General Updates

The data scraping pipeline and barebones simulation pipline are built and run. A simulation of a school day with 6,700 simulated students comletes with 11.3M trajectory samples. Here is where each pipeline stage code lives: 

1. **`scrapers/scrape_courses.py`** - pulls 2025-2026 course data from the Explore Courses api
2. **`scrapers/get_buildings.py`** - pulls unique building strings
3. **`pipeline/tag_courses.py`** - filters courses_2025_2026.csv to just Spring courses, tags each section with `school` and `level` buckets, identifies "anchor" sections w linked discussion sections
4. **`pipeline/generate_population.py`** - produces 6,700 students with year, school, dorm assignment (by year-eligibility), travel mode, and target unit load
5. **`pipeline/assign_schedules.py`** - senior-priority student-driven matching with school x level affinity weighting, with a bit of slack or current enrollment levels
6. **`sim/load_data.py`** - joins population + schedules + buildings into per-agent trip plans
7. **`sim/runner.py`** - multi-agent state machine (home → moving → in_class → between → done) with edge-progress movement, right now running from 06:00–22:00 at 10s timesteps ... still a bit buggy, need to play with states/go home behavior

The barebones simulation currently has plausible results: empty class buildings pre-8am, ramps up through morning passing periods, winds down through evening. 

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
python eval/congestion.py  # baselines + real trajectory (currently bugged)
```

Baseline results:

| baseline | moving samples | peak congested | peak time | top edge LoS | notes |
|---|---|---|---|---|---|
| empty trajectory | 0 | 0 | — | — | no congested edge-minutes, no exposures |
| single agent (50m edge, 10 min) | 20 | 0 | — | A | 150 m²/p, exposure_frac = 0 |
| fake crowd (250 on 50m edge, 1 min) | 250 | 250 | 00:30 | F | 0.6 m²/p, all 250 fully exposed |

Real eval on the current 6,700-agent Monday trajectory: **31,672 edge-minutes observed, peak congested = 0**. The tightest m²/person seen anywhere all day was 2.27 (just above the 2.2 D threshold), and the 9 nearest-misses were all on sub-3m graph edges that are basically zero-length OSM artifacts. Median agents per (edge, minute) = 1, max = 33. So the eval pipeline runs end-to-end on real data, but the sim is producing a quiet campus — likely a mix of the home→in_class teleport bug (still being chased), 6,700 UG only (vs ~17k total students), and 3m path width being generous. Sim-side problem, not eval-side. Full per-edge-minute table written to `outputs/edge_minute_los.parquet` and summary to `outputs/congestion_baseline.json`.

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
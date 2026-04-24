# Campus Cluster: Simulating Stanford Student Traffic to Understand Campus Congestion

**Student:** Dina Hashash | hashash@stanford.edu  
**Course:** CS348K - Visual Computing Systems, Spring 2026

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
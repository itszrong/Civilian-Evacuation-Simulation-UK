# Technical next features Q&A — A*, Biased Random Walks, and Mesa for Civilian Evacuation Simulations

> **Purpose:** Dense, technical-only Q&A bank for reviewers and engineers.  
> **Scope:** Algorithms, limitations, edge cases, performance, data, and implementation details for an evacuation simulator using **A\***, **biased random walks (BRW)**, and **Mesa**.  
> **Cross-links:** Update the placeholders to point at your repo modules (e.g., `./sim/route/a_star.py`, `./sim/agents/brw_policy.py`, `./sim/model/mesa_model.py`).

---

## A) A* Pathfinding in Evacuation

**Q1. Why A\* instead of Dijkstra for evacuations?**  
**A.** A\* with an admissible/consistent heuristic (e.g., Euclidean/Manhattan lower bound on travel time) explores far fewer nodes than Dijkstra on large urban graphs. With dynamic weights, prefer incremental A\* (LPA\*/D\* Lite) over full recomputation.

**Q2. What’s the admissible heuristic if edge costs are time-varying due to congestion?**  
**A.** Use a **static lower bound** on time (e.g., distance / max speed limit) that ignores congestion; it remains admissible because congestion only increases cost.

**Q3. How do you make A\* handle **turn penalties** and **one-way** restrictions?**  
**A.** Encode state as `(node, inbound_edge)` or run on an **edge-based graph**; augment costs with a turn penalty table. One-ways are directed edges; A\* runs over the directed multigraph.

**Q4. How to avoid “herding” where many agents pick the same A\* shortest path?**  
**A.** Add **stochastic tie-breaking** + **edge cost inflation** proportional to predicted load (e.g., `cost = base + α·expected_density`). Alternatively, compute **k-shortest paths** (Yen/ESX) and sample for diversity.

**Q5. What’s the complexity and how to bound it in city-scale graphs?**  
**A.** Worst-case `O(E log V)`. Bound expansions via **search windows** (radius/time budget), **hierarchical routing** (contraction hierarchies), or **bidirectional A\*** for point-to-point queries.

**Q6. How to replan efficiently when congestion updates every tick?**  
**A.** Use **incremental planners** (LPA\*, D\* Lite) or **anytime replanning** with partial open lists. Cache **landmarks/potentials** for the heuristic; update only affected subgraphs.

**Q7. Can A\* handle **capacity constraints** (edge saturation) natively?**  
**A.** Not directly; integrate via (1) **time-expanded networks**; (2) **penalization** as edges approach capacity; (3) **reservation tables** modeling discrete edge occupancy over time.

**Q8. How to model **pedestrian** vs **vehicle** flows in A\*?**  
**A.** Maintain distinct **layers** with mode-specific edges, speeds, and capacities; enforce constraints (stairs, sidewalks). Multi-modal routing uses **supernodes** to connect layers with transfer penalties.

**Q9. How to ensure **heuristic consistency** with turn costs?**  
**A.** Precompute minimal turn penalties and include them in the lower bound; or use edge-based heuristics derived from **transition lower-bounds**.

**Q10. Failure mode: A\* oscillation under rapidly changing costs?**  
**A.** Caused by aggressive cost updates. Mitigate with **EMA smoothing**, **minimum update intervals**, and **hysteresis**/hold windows before rerouting.

---

## B) Biased Random Walks (BRW)

**Q11. What is a biased random walk here?**  
**A.** A Markov movement model where step probabilities are biased by potentials (goal attraction, congestion aversion, risk fields):  
`P(next_edge) ∝ exp(β_goal·U_goal + β_crowd·U_density + β_risk·U_risk + noise)`.

**Q12. How do you calibrate the bias parameters (β)?**  
**A.** Fit to observed flows (ANPR, loop detectors, bus headways) via **MLE** or **Bayesian** inference; cross-validate; regularize to avoid overfitting.

**Q13. How does BRW reduce herding vs deterministic shortest paths?**  
**A.** Injects **entropy** and **congestion aversion**, spreading agents across alternatives to match empirical dispersion.

**Q14. Model information asymmetry (informed vs uninformed)?**  
**A.** Use different β vectors and potentials access. Informed agents have stronger goal potentials and lower perceived risk/uncertainty.

**Q15. Prevent BRW cul-de-sacs?**  
**A.** Add **reflecting boundaries**, **backtracking penalties**, and small A\*-based **lookahead** to veto dead-ends.

**Q16. Computational cost vs A\*?**  
**A.** BRW is cheaper per step (local), but scales with `agents × degree` per step; A\* is costlier per reroute but fewer decisions.

**Q17. Incorporating capacity into BRW?**  
**A.** Use **Metropolis-like acceptance** scaled by residual capacity or **queueing** at nodes with FCFS/priority rules; zero probability when full.

**Q18. Limitation: BRW is memoryless—path commitment?**  
**A.** Extend state with **heading persistence** or **semi-Markov** dwell times; add **stickiness** term to discourage frequent direction changes.

**Q19. Group behavior (families, teams)?**  
**A.** Couple walkers via cohesion potentials (distance penalties), shared info state, leader-follower dynamics.

**Q20. Hybrid A\* + BRW?**  
**A.** Use A\* for coarse waypoints; BRW for local micro-choices under congestion/noise; switch when deviation exceeds threshold.

---

## C) Mesa (ABM) Implementation

**Q21. Agent and scheduler structure?**  
**A.** Prefer **SimultaneousActivation** or **StagedActivation** (move → interact → update). Agents carry `(mode, route_state, info_state)`; model holds graph, capacities, feeds.

**Q22. Time resolution trade-off?**  
**A.** Smaller ticks capture queues better but cost more. Typical: **1s sim tick**, **200ms render tick**; **adaptive substepping** only at congested nodes.

**Q23. Capacity and queues?**  
**A.** Implement **per-edge ring buffers**/**token buckets** with occupancy timestamps. On saturation, queue at nodes with **FCFS** or priority dequeues.

**Q24. Determinism & reproducibility?**  
**A.** Seed RNGs (Python/NumPy); separate streams; store **scenario hash** and **agent seeds**; snapshot state for replay/forks.

**Q25. Parallelization?**  
**A.** Partition graph into **tiles**; run disjoint subgraphs on workers; exchange boundary messages each tick. Use **Ray/Dask/multiprocessing**; ensure idempotent tick updates.

**Q26. UI vs headless?**  
**A.** Keep Mesa UI for dev; production runs as **headless workers** behind a queue; stream deltas via SSE/WebSocket.

**Q27. Profiling hotspots and fixes?**  
**A.** Route updates, neighbor queries, Python loops → use **Numba/Cython**, **vectorized NumPy**, and pre-simplified graphs (**osmnx→igraph** when heavy).

**Q28. Memory bounds?**  
**A.** Store **delta frames**, compress trajectories (polyline encoding), purge agent histories after safe arrival; retain aggregates.

**Q29. Testing?**  
**A.** Unit tests for step logic; **contract tests** for capacity invariants; property tests for conservation (inflow = outflow + queued + exited).

**Q30. Metrics?**  
**A.** Per tick: edge loads, queue sizes, P50/P95 clearance, stall/reroute counts. Export to time-series (Prometheus/Influx).

---

## D) Integration: A*, BRW, Congestion

**Q31. Coupling A\* costs to real-time congestion?**  
**A.** `edge_cost = base_time · f(density)` using convex `f` near capacity (e.g., BPR/Greenshields). Update per tick; throttle replans.

**Q32. Prevent route thrash under noisy signals?**  
**A.** **Hysteresis** (switch if Δcost > ε for τ ticks), **EMA smoothing**, and **cooldowns** between replans.

**Q33. Handling gridlocks/deadlocks?**  
**A.** Detect zero-progress; enforce **priority rules**, **hold-and-release** at junctions, or trigger **global spillback reduction** via detours.

**Q34. Multi-objective routing (time, risk, fairness)?**  
**A.** Scalarize with weights or sample **Pareto-efficient** routes; fairness enters as penalties in edge costs.

**Q35. Vehicle–pedestrian interaction?**  
**A.** Shared edges add **mode conflict penalties**; mutual exclusion on tight corridors; lower pedestrian speed beyond vehicle-density thresholds.

---

## E) Data & Map Handling

**Q36. OSM simplification & correctness checks?**  
**A.** Topology-preserving simplification; collapse degree-2 chains; keep lanes/maxspeed. Validate with **connectivity** and sample OD shortest paths.

**Q37. Time-dependent closures?**  
**A.** Use **temporal masks** or time-indexed penalties; maintain a schedule and recompute reachability incrementally.

**Q38. Elevation/stairs & mobility constraints?**  
**A.** Encode `grade` and `stairs` edge attributes; agents filter infeasible edges; add energy cost to routing.

**Q39. Sensor dropouts / stale feeds?**  
**A.** **Freeze last-known-good** with decay, widen uncertainty, flip **degraded mode**, suppress auto-escalations until recovery.

---

## F) Metrics, Calibration & Uncertainty

**Q40. Core metrics?**  
**A.** **Clearance time (P50/P95)**, **link throughput**, **distance/time to safety**, **max-min fairness**, **route diversity (Gini/Theil)**, **reroute frequency**, **stall rate**.

**Q41. Calibrating hybrid BRW/A\* to observations?**  
**A.** Fit β weights and congestion parameters to minimize **MAE** on link loads/timing; validate on held-out events (e.g., marathons, planned closures).

**Q42. Representing uncertainty?**  
**A.** Run multiple seeds/scenarios; report **credible intervals**; attach **confidence tags** to recommendations; show **edge load error bars**.

---

## G) Performance & Systems

**Q43. Streaming 50k+ agents to UI?**  
**A.** Send **edge-load deltas** rather than raw positions; render **1–5% stratified samples**; decouple sim and render ticks; drop frames under load.

**Q44. Parallel A\*?**  
**A.** Batch source-destination queries, reuse **landmarks**, exploit **multi-source** A\* when many agents share goals.

**Q45. Checkpoint & resume?**  
**A.** Snapshot agent + queue state + RNG seeds + cost fields; resume deterministically; useful for what-if forks.

---

## H) Known Limitations & Failure Modes

**Q46. A\* assumes perfect costs.**  
**A.** Treat costs as estimates; smooth and limit replans; expose confidence.

**Q47. BRW under-uses optimal corridors.**  
**A.** Add **soft guidance** (signage potentials) or hybridize with waypoint A\*.

**Q48. Mesa’s Python loops can be slow.**  
**A.** Vectorize; JIT with **Numba**; offload heavy kernels to C++/Rust microservices via RPC.

**Q49. Capacity modeling is approximate.**  
**A.** Consider **time-expanded networks** or explicit queueing; validate against empirical saturation curves.

**Q50. Reproducibility vs stochastic realism.**  
**A.** Log deterministic seeds; present variance bands to convey spread.

---

### Replace these placeholders with repo links
- A\* implementation: `./sim/route/a_star.py`
- BRW policy: `./sim/agents/brw_policy.py`
- Mesa model & schedulers: `./sim/model/mesa_model.py`
- Capacity/queues: `./sim/flow/capacity.py`
- Metrics & evals: `./sim/metrics/evac_metrics.py`

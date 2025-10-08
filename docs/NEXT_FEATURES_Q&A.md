# London Evacuation Planning System — Q&A for next features

> **Purpose:** A comprehensive q&a to figure out what to ship next in the codebase.  
> **Scope:** Architecture, scale, validation, security, reliability, product/roles, testing, versioning, ethics, and lightning checks.  
> **Style:** Concise, operational, and auditable.

---

## 0) One‑line Product Frame
**Q:** In one sentence, what problem does this uniquely solve beyond plans and exercises?  
**A:** **It turns live feeds and plans into an always‑on simulation that highlights the next bottlenecks and recommends specific actions—who should do what, where, and when—backed by confidence bands and audit trails.**

**Q:** What’s the actionable output at **T+15 minutes** in an incident?  
**A:** The system publishes:
- **P50/P95 clearance time** by borough / zone
- **Top‑10 choke segments** (agents per segment; capacity vs load)
- **Ranked actions** with owners, e.g. “TfL: contra‑flow on X; Borough Control: pre‑position crews at Y; Police: cordon Z”
- Each item includes **rationale** and **confidence**; emitted to an **Action Board** with **Apply/Defer** controls and audit logging.

**Q:** Define **“live evacuation readiness model.”** When is it unsafe to run live?  
**A:** **Live** = an **always‑on**, city‑wide model that **ingests current feeds**, **simulates 5–15‑minute horizons**, and **emits ranked, auditable recommendations** to named owners.  
**Unsafe** if: **calibration drifts** (uncalibrated outputs), **latency SLOs** are breached (stale advice), or **guardrails** are absent (no human‑in‑the‑loop, no P50/P95 bands, no audit/provenance).

**Q:** Single hardest technical constraint solved; and first refactor if given another week?  
**A:** **Solved:** building a **unified, memory‑bounded, capacity‑annotated street graph** (OSM → pruned, directed) that sustains **50k agents at 1‑sec ticks** without GC thrash via **edge compression, tiling, and lazy attribute fetch**.  
**Refactor next:** **Isolate the simulation engine** behind a **queue/job API** with **deterministic seeds** and **snapshot/restore**, enabling **horizontal autoscale** and **reproducible runs**.

---

## 1) Architecture & Design

**Q:** Why microservices rather than a monolith?  
**A:** Split into **control plane (API/UI)** and **sim workers**. This prevents burst compute from back‑pressuring the API, enables **isolation**, **autoscale**, and **scale‑to‑zero** when idle.

**Q:** Multiple graph‑loading implementations exist—why, and what’s the consolidation plan?  
**A:** Legacy from refactors. Consolidate in **3 steps**:  
1) Extract a single **GraphStore** lib (loader + cache interface).  
2) Migrate callers using **dependency injection**.  
3) Delete legacy paths guarded by **contract tests**.

**Q:** Should the Mesa simulation run as a separate service?  
**A:** **Yes.** Place behind a **work queue + stateless workers** for isolation, autoscale, per‑run audit, and to stop compute spikes starving request handling.

**Q:** How does **dependency injection (DI)** help failure testing?  
**A:** DI enables injecting failures (e.g., OSM provider down) to assert **retry/backoff**, **circuit breaker**, **cache fallback**, and metrics like `graph.load.failure` in tests—without touching live providers.

---

## 2) Scale & Performance

**Q:** 500k agents across 10 scenarios—what breaks first and why?  
**A:** **CPU** first. With local‑neighborhood updates, per‑tick cost is ~**O(E)**; hotspots are **turn costs + contention** on dense edges. Strategy: **tile/partition**, **batch/SIMD inner loops**, and **lock‑free per‑tile queues**. **Memory** grows ~linearly; cap via **delta frames** and compact state. **I/O** is fine—stream **down‑sampled deltas** to UI.

**Q:** Keep the UI responsive without bias when rendering many agents?  
**A:** Render a **1–5% stratified sample** proportional to edge load to preserve the **edge occupancy distribution** (verify with a **KS test ≤ 0.02** per tick). Decouple **sim tick = 1s** from **render tick ≈ 200ms**; drop frames under load.

**Q:** 100 concurrent simulations—what isolation and back‑pressure exist?  
**A:** **Work queue (Redis/RabbitMQ)** with **per‑job CPU/mem limits**, **tenant‑level concurrency caps**, and **queue‑depth thresholds** that trigger **429 Retry‑After** and **priority shedding**. **Idempotent job keys** prevent duplicates; **audited per‑run**.

---

## 3) Data, Validation & Accuracy

**Q:** How is the model validated against reality given scarce evacuation data?  
**A:** **Three‑track validation:**  
1) **Backtests** on proxy events (roadworks, marathons, large events) using observed signals (**UTMC loop detectors, ANPR counts, bus headways**); targets: **MAE ≤ 10%** on edge load; **timing ±5 min**.  
2) **Ablations** (remove a feed/behavior) to ensure sensitivity matches expectations.  
3) **Tabletop adjudication** with planners—score **actionability**, **plausibility**, and ensure recommendations have **confidence + rationale**.

**Q:** Where can A* + behavioral tweaks mislead commanders, and how is uncertainty surfaced?  
**A:** Risks: **herding** on shortest paths, **capacity misestimation**, **info‑gap bias** under feed loss. Mitigations: **stochastic routing mixes** (shortest, congestion‑aware, biased random walk) tuned to dispersion; UI shows **edge load with error bars**, **P50/P95**, a **‘degraded data’ banner** on input loss, and **alternatives (Plan A/B)** with tradeoffs.

**Q:** Provide a concrete P50/P95 and the degraded‑mode policy when a key feed fails.  
**A:** Example: Westminster cordon → **P50 42 min; P95 68 min** with live feeds. If **TfL GTFS‑RT drops**, **freeze last‑known‑good** with **time decay**, widen to **P50 50; P95 82**, flip UI to **degraded mode**, **suppress auto‑escalations**, and prioritize **human reports** until feeds resume and estimates are recomputed.

---

## 4) Security & Governance

**Q:** Why no auth yet; what is the minimal day‑one authN/Z?  
**A:** Day‑1: **OIDC (SSO) + MFA**, **RBAC** for **Borough / TfL / Police / COBR** roles, **short‑lived JWTs** for service calls, and **signed audit logs** capturing **who ran what, when, with which inputs**.

**Q:** Secrets, rotation, CORS, rate limits, retention?  
**A:** Store secrets in **cloud secret manager**, KMS‑encrypted, **rotation ≤ 90 days**, access logged. **Prod CORS** locked to authorized domains. **Rate limit**: 100 rps/user (burst 200), return **429 Retry‑After**; per‑tenant **job quotas**. **Retention:** audit logs **1 year**; sim artifacts **90 days** (longer if required by casefile).

---

## 5) Reliability & Ops

**Q:** SSE drops mid‑incident—how is it handled; where is idempotency enforced?  
**A:** SSE uses **heartbeat + Last‑Event‑ID resume** with **exponential backoff (≤30s)**. **Idempotency keys** (`run_id`, `step_id`) ensure replays don’t duplicate actions. Clients auto‑reconnect; server is stateless across events.

**Q:** First three checks in the on‑call runbook when sims stall?  
**A:** (1) **Data freshness SLI** (feed staleness > 60s?) (2) **Queue depth / worker health** (stalled jobs, CPU throttling) (3) **API p95 latency/error budget** burn rate.

**Q:** SLOs and the single paging metric during incidents?  
**A:** **SLOs:** API **p95 < 250 ms**; **data freshness ≤ 60 s**; **sim start latency < 10 s**; **successful job rate ≥ 99.5%**; availability **99.9%**.  
**Page on:** **Decision latency** (incident ingest → recommendations) **> 120 s** or **feed freshness** breach—these most endanger operations.

---

## 6) Product, Roles & Fairness

**Q:** Who owns a **contra‑flow** decision and what do they see?  
**A:** **Owner:** **Transport network control** (roads). Police **Gold/Silver** coordinate cordons; **borough control rooms** execute local actions.  
**View:** **Action Board** listing **Top‑N bottlenecks** with **location, load, P50/P95 impact, recommended action, owner, Apply/Defer**, and full **audit**. Chat is supplemental; the board is the **primary control surface**.

**Q:** Training needed and likely week‑1 mistakes?  
**A:** **60‑minute tabletop** to cover action board, confidence bands, and approvals. Week‑1 risks: **over‑trust low‑confidence items**, **context gaps**, **alert fatigue**. Mitigations: **confidence gating**, **scenario templates**, **role‑scoped rate‑limited notifications**.

**Q:** Preventing inequitable outcomes—what metric?  
**A:** Monitor **max‑min fairness** of clearance times across boroughs and an **exposure‑weighted Gini** for time‑to‑safe‑zone (weighted by population & deprivation). The optimizer penalizes actions that improve averages while **worsening the tail** beyond threshold (e.g., **P95 − P50 > 30 min**). Also track **route diversity** (Theil index).

---

## 7) Testing & Quality

**Q:** What integration tests are needed; first end‑to‑end (E2E) to write?  
**A:** Add **contract tests** across **ingest → queue → sim → action board**, plus **failure‑path tests** (feed stale, queue full, worker crash). **E2E #1:** *RSS incident → risk score ≥ threshold → queued job → approved → sim → Action Board emits Top‑N with P50/P95 + audit*. Assert **idempotency** and **decision latency < 120 s**.

**Q:** Detecting DSPy agent drift; acceptance thresholds?  
**A:** Maintain **frozen eval suites** (scenario prompts + gold rationales). Gate **safety‑critical** prompts at **accuracy ≥ 95%** and **ECE ≤ 0.05**; for creative synthesis, cap **hallucinations ≤ 2%** and require **human approval** for novel patterns.

**Q:** Chaos tests and rollback triggers?  
**A:** Chaos: **kill key feed + 10× agent spike**; also **partition the queue** mid‑run. **Rollback** when **decision latency > 120 s** or **false‑positive action rate > 5% (rolling 10 min)** → **disable recs**, **revert to prior model snapshot**, **advisory‑only mode** until the error budget recovers.

---

## 8) Interfaces & Versioning

**Q:** API versioning and deprecation policy?  
**A:** Use **/v1** paths + **X‑API‑Version** header. **Sunset** and **Deprecation** headers with a **90‑day window**, weekly owner notices, **compat shims**, and a **changelog**.

**Q:** Schema changes without downtime; rollout strategy?  
**A:** **Expand → Shadow‑write → Verify → Flip reads → Contract**. Use **canary** (5%→25%→100%) guarded by **SLI/error‑budget** monitors; **auto‑rollback** on breach.

---

## 9) Ethics, Comms & Failure Modes

**Q:** Post‑incident communication when a recommendation worsened congestion?  
**A:** Publish an **After‑Action Report**: feeds & freshness, **assumptions**, **recommendations vs outcomes**, confidence bands, **timeline**, **provenance logs**, and the **model snapshot** used. Feed learnings into the **eval suite**.

**Q:** Policy for *safe‑to‑ignore* vs not?  
**A:** Impact × Confidence matrix:  
- **Safe to ignore:** **Low impact & Low confidence**.  
- **Require human review:** High impact and/or Low confidence.  
- **Auto‑page (never auto‑execute):** **High impact & High confidence** with **dual approval**.

**Q:** If one capability must be removed to reduce risk, which?  
**A:** Remove the **global chat agent** and rely on the **Action Board** with structured, auditable recommendations. Increases training slightly; improves safety and consistency.

---

## 10) Lightning Round (Crisp)

- **Single point of failure today?** The **simulation worker pool**. Mitigations: **N≥3 workers**, **queue retries**, and **graceful degradation** to advisory rules.  
- **Biggest non‑obvious cost driver?** **Evaluations at scale** (human adjudication + data labeling) and **geospatial data egress**.  
- **Kill the project if…** After **two quarters**, we don’t beat baseline playbooks on **decision latency** and **precision/recall**, or adoption remains **< 30%** of incidents.  
- **Weekly value metric?** **Decision latency**, **action acceptance rate**, and **incident precision/recall** vs ground truth; watch **feed freshness** and **P95 clearance tail** improvements.

---

## Appendix — Definitions & SLOs (for reference in code/docs)

- **Decision latency:** time from incident ingest → first ranked recommendations. **SLO:** ≤ **120 s** during incidents.  
- **Data freshness:** age of latest successful feed ingest. **SLO:** ≤ **60 s**.  
- **Sim start latency:** time from job enqueue → sim tick 0. **SLO:** < **10 s**.  
- **Successful job rate:** % sims completing without error. **SLO:** ≥ **99.5%**.  
- **API latency (p95):** **< 250 ms**. Availability **99.9%**.  
- **Idempotency keys:** (`run_id`, `step_id`) across API, queue, workers.  
- **Degraded mode:** triggered on feed loss; **freeze LKG**, widen bands, suppress auto‑escalations, banner warning.


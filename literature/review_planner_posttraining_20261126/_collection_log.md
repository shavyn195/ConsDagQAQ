# Collection log — 2026-11-26

Official arXiv query XML and parsed metadata are retained in this directory. Retrieval was exploratory and bounded, prioritizing late-2026 work. No claim of exhaustive absence is supported. PDF extraction used PyMuPDF unsorted page text to avoid two-column interleaving; originals and page arrays are retained locally.

| Paper | Version | PDF pages | Reading coverage |
|---|---|---:|---|
| Learning What to Change: State-Verified Reinforcement Learning for Educational Agents | 2611.30559v1 | 13 | All pages, including technical appendices |
| AnchorCredit: Output-Anchored Credit Assignment for Structured Generation with Multiple Verifiable Rewards | 2611.30881v1 | 31 | All pages, including technical appendices |
| Safety as a Budget: Calibrating the Control Channel of Constrained GRPO for Vision-Language Models | 2611.16628v1 | 10 | All pages, including technical appendices |
| Policy Optimization With Multiple Verifiers via Pareto Rankings | 2611.19064v1 | 46 | All 46 pages, including proofs, implementation and experimental appendices |
| Are We Rewarding the Wrong Module? Module-Specific Policy Optimization for Multimodal Reinforcement Learning | 2611.32687v1 | 25 | All pages, including technical appendices |
| CO-GRAFT: Attributing Reinforcement Learning Gains in Search Agents via Role-Level Policy Grafting | 2611.31185v1 | 14 | All pages, including technical appendices; completed in follow-up |
| When Fine-Grained Credit Assignment Helps and Hurts: Multimodal Agentic Reinforcement Learning through Video Editing | 2610.35497v1 | 48 | All 48 pages; source curves 46–48 visually inspected |
| VERA: Verifiable Feasibility Representations with Counterfactual Credit for Constrained Multi-Agent Control | 2609.38889v1 | 23 | All pages, including technical appendices |

Full-text comparison notes: deep_reading.md. Research proposal: ../../reports/planner_posttraining_direction_20261126.md.

Additional metadata-only candidates: Constrained GRPO 2602.05863v4 (updated 2026-09-02), ContractRL 2610.00328v2 (updated 2026-10-16). Do not treat metadata screening as a full reading or paper replication.

Web search tool returned empty output earlier in this turn; usable evidence came from archived official API responses and downloaded PDFs. No invented web citations.

2026-11-26 follow-up: CO-GRAFT full reading completed; total six fully read papers/116 pages. Abstract/main-text Query share bound (15%) conflicts with two Table 1 entries (16%); retained in notes. Cross-module attribution is proposed as an inherited analysis, not a new learning method.

2026-11-26 continued: POLPO full reading completed and key pages rechecked; total seven fully read papers/162 pages. Fine-Grained Credit remains abstract-only. This is reading coverage, not official-code replication. POLPO no-dominance regime and isolated-loss versus full-update overhead are recorded without claiming our invalid-output pilot establishes that regime.

2026-11-26 continuation: Fine-Grained Credit read in full (48 pages; curves checked). Total eight fully read papers/210 pages. See fine_grained_reading.md for stagewise oracle initialization, recipe/compute differences, process-reward failures and the limited transfer to single-output constrained planning. No official implementation reproduction; this turn’s web open returned no usable page, so version claims refer to the archived v1.

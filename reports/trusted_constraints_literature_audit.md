# Trusted-Constraint Literature and Definition Audit

Date: 2026-11-21

## Scope

The trusted-constraint definition was checked against the extracted midterm report (`docs/midterm_extract.txt`, Section 2.1) and the source papers cited there. The report defines five constraint families:

| ID | Midterm definition | Structural type |
|---|---|---|
| C1 | `trust(s) >= tau` for every selected service | node admission / scalar |
| C2 | output sensitivity propagated along the DAG must not exceed the downstream input limit | topological propagation |
| C3 | number of selected services outside the owner department is at most `K` | global cumulative |
| C4 | downstream sandbox tier is at least `ceil(max_upstream_sensitivity / 2)` | topological cascade |
| C5 | sum of response times on the critical path is at most `T_SLA` | path cumulative |

The report also maps these constraints to `trust_score`, `sensitivity_out`, `max_input_sens`, `sandbox_tier`, and `dept_id` candidate fields.

## Search protocol

This is a targeted exploratory search, not an exhaustive systematic review. On 2026-11-21, arXiv search pages were queried for `trust-aware service composition`, `privacy-aware service composition`, `service composition QoS path selection`, `trusted data spaces access control data sovereignty`, `sandbox privacy data workflow`, `department quota data space`, `cross organizational quota access control data sharing`, `sensitivity propagation DAG service composition privacy`, and `critical path latency workflow service composition`. Crossref was queried for `service composition critical path QoS latency DAG`, `cross department quota service composition data space`, `data sovereignty constraints service composition data spaces`, and `sandbox tier privacy aware workflow data spaces`.

Searches surfaced strong adjacent work for C1, C2, C4, and C5, but no arXiv paper with the exact C3 cardinality rule or C4 tier equation. That is a bounded search result, not proof that no such work exists.

## Source-paper verification

The following arXiv manuscripts were downloaded and text-extracted under `literature/trusted_constraints/`.

| Paper | URL | What it supports | Boundary |
|---|---|---|---|
| Cavalcante et al., *Privacy in Data Service Composition -- k-Protection* | https://arxiv.org/abs/2001.00975 | Local enforcement of privacy constraints in a service-composition/data-integration plan; k-protection limits information leakage without a trusted mediator. | It does not define the report's exact `sens_out <= max_in` field pair or the five-constraint CMDP. Cite the report's C2 as a DAG-aware adaptation/generalization inspired by k-Protection. |
| Sagar et al., *Trust-SIoT: Towards Trustworthy Object Classification in the Social Internet of Things* | https://arxiv.org/abs/2205.03226 | Multi-dimensional trust measurement and trust-based selection of credible objects/services. | It motivates a trust score, but does not establish the exact service-composition threshold `trust(s) >= tau` used in the report. |
| Mistry and Bouguettaya, *Reputation Bootstrapping for Composite Services using CP-nets* | https://arxiv.org/abs/2105.15135 | Composition topology and reputation interdependence are used to bootstrap composite-service reputation; includes a Q-learning selection method. | Directly relevant to trust/reputation in compositions, but it bootstraps reputation and does not impose the report's hard per-service threshold. This paper was already downloaded but omitted from the previous comparison table. |
| Abusafia et al., *Context-Aware Trustworthy IoT Energy Services Provisioning* | https://arxiv.org/abs/2401.01029 | Context-aware provider trust scoring is combined with trust-adaptive service composition; provider trust depends on consumer requirements. | A closer C1/service-composition precedent than Trust-SIoT alone. It does not define the TDS threshold value or C2-C5. |
| Fotiou et al., *Access control for Data Spaces* | https://arxiv.org/abs/2504.13767 | Fine-grained, continuously evaluated access-control policies for data spaces, including owner-managed policy administration. | Relevant governance context for C3, but it does not define a per-plan cap on the number of selected services from outside the owner department. Published DOI listed by arXiv: 10.1109/ICIN64016.2025.10943024. |
| Zhao et al., *Styx: Collaborative and Private Data Processing With TEE-Enforced Sticky Policy* | https://arxiv.org/abs/2604.04082 | TEE-backed sandboxed execution and sticky policy checks across input, processing, and derived output. | Strong operational precedent for isolation and data-policy enforcement around C4/C2. It does not define numeric sandbox tiers or `tier(v) >= ceil(max_upstream/2)`. |
| Alsaryrah et al., *Bi-Objective Optimization for Energy Aware Internet of Things Service Composition* | https://arxiv.org/abs/1811.11272 | Models QoS attributes including execution time and network latency as path-aggregated service-composition objectives. | Relevant precedent for path-based C5/QoS aggregation, but not the report's exact deadline rule over a branching DAG's critical path. Published DOI listed by arXiv: 10.1109/ACCESS.2018.2836334. |
| *Safe Multi-Agent Deep Reinforcement Learning for Privacy-Aware Edge-Device Collaborative DNN Inference* (HC-MAPPO-L) | https://arxiv.org/abs/2603.00129 | Constrained multi-agent optimization with privacy, delay, energy, and reliability concerns; hierarchical policy and Lagrangian-style constraint handling. | Its edge-inference setting and privacy cost are different from a TDS sandbox-tier propagation rule. The report's C4 should be described as a domain adaptation/mapping, not as a rule taken verbatim from HC-MAPPO-L. |
| Schulman et al., *Proximal Policy Optimization Algorithms* | https://arxiv.org/abs/1707.06347 | PPO optimization baseline. | Algorithmic baseline only; not evidence for TDS semantics. |
| Achiam et al., *Constrained Policy Optimization* | https://arxiv.org/abs/1705.10545 | CMDP/constrained policy-optimization formulation. | General safe-RL theory; it does not provide the TDS constraint taxonomy. |

The midterm bibliography also lists CP-nets, PCPO, PLO, RLHGNN, DRL-CBF, FCPO, and SafeMPO. They are useful algorithmic comparisons, but they do not replace a source for the TDS-specific semantics. The first three TDS-related manuscripts above are now locally available for re-reading.

## C1-C5 Evidence Map

| Constraint | Literature support found | What remains specific to the midterm model |
|---|---|---|
| C1 trust threshold | Trust-SIoT; CP-nets; Context-Aware Trustworthy IoT Energy Services Provisioning | The hard threshold `trust(s) >= tau` is a reasonable operationalization, but its threshold and score aggregation must be defined and justified by this project. |
| C2 sensitivity compatibility/propagation | k-Protection; Styx sticky-policy enforcement | The exact numeric `sens_out(u) <= max_in(v)` relation and DAG propagation semantics are an adaptation; k-Protection is about limiting inference/leakage, while Styx enforces policies through execution. |
| C3 cross-department quota | Access control for Data Spaces supports owner sovereignty and policy enforcement at a general level | No directly matching paper was found for `count(selected services with dept != owner) <= K`. Treat this as a project-defined governance constraint motivated by data-space federation, not as an established literature formula. |
| C4 sandbox matching | Styx provides TEE-backed sandboxing and policy enforcement; HC-MAPPO-L is a constrained edge-inference optimizer | Neither source gives the tier scale or `tier(v) >= ceil(max_upstream_sensitivity/2)`. The midterm report's HC-MAPPO-L citation supports constrained privacy-aware execution only, not the sandbox-tier formula. |
| C5 critical-path SLA | QoS-aware service-composition/path-optimization literature aggregates execution-time and latency attributes along composition paths | The exact maximum-over-parallel-paths calculation and the chosen `T_SLA` are project-specific; state the DAG critical-path operator explicitly and test it with branched workflows. |

## Alignment with the current ConsDag experiment

The current v2 dataset and E1 compiler contract use five query-level constraint types:

`budget`, `deadline`, `privacy`, `tool_auth`, and `order`.

This is a valid trusted-data-space *case instantiation*, but it is not a literal implementation of the midterm C1--C5 taxonomy:

- `privacy` is a useful operational proxy for data-residency/PII restrictions, but it is not the k-Protection mechanism and does not model privacy leakage on DAG edges.
- `budget` is not C3's cross-department service-count quota.
- `deadline` currently checks generated duration semantics and binds to a terminal role; it is not C5's critical-path response-time aggregation.
- `tool_auth` and `order` are workflow governance constraints and have no one-to-one C1--C5 counterpart.
- The compiler dataset does not expose `trust_score`, `sensitivity_out`, `max_input_sens`, `sandbox_tier`, or `dept_id` as constraint parameters.

Therefore the safe claim is: “we instantiate the compiler in a trusted-data-space-inspired tool-planning domain.” The unsafe claim is: “E1 evaluates the five midterm TDS constraints C1--C5.” That stronger claim requires a matched TDS subset and an independent verifier.

## Required experiment wording and follow-up

1. Keep the current E1 results under the generic constraint/compiler claim and report the five operational types explicitly.
2. Add a small matched TDS evaluation slice before claiming continuity with the midterm work. Each record should carry the five fields above, a DAG with real parent edges, a feasible witness, and independent checks for C1--C5.
3. For C2/C4, pass the actual DAG parent relation to the verifier and reward code. A fallback that omits `parents` is backward-compatible only and must not be used for the headline TDS result.
4. For C3, count distinct selected departments against `K`; for C5, compute the longest/critical path rather than summing all node durations.
5. Report k-Protection, Trust-SIoT, and HC-MAPPO-L as motivation/adaptation sources, with the boundaries above, rather than claiming direct reproduction.

## Local artifacts

- `literature/trusted_constraints/2001.00975.pdf` and `.txt`
- `literature/trusted_constraints/1811.11272.pdf` and `.txt`
- `literature/trusted_constraints/2105.15135.pdf` and `.txt`
- `literature/trusted_constraints/2205.03226.pdf` and `.txt`
- `literature/trusted_constraints/2401.01029.pdf` and `.txt`
- `literature/trusted_constraints/2504.13767.pdf` and `.txt`
- `literature/trusted_constraints/2603.00129.pdf` and `.txt`
- `literature/trusted_constraints/2604.04082.pdf` and `.txt`

The repository test suite currently reports `24 passed, 2 skipped`.

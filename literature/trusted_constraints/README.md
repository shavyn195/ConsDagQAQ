# Trusted Constraints Corpus

This directory contains the papers and extracted text used to audit the trusted-constraint definitions in `docs/midterm_extract.txt` (Section 2.1). The midterm report defines a five-dimensional trusted-data-space constraint model:

| ID | Midterm definition | Required fields / computation |
|---|---|---|
| C1 | `forall s: trust(s) >= tau` | `trust_score`, threshold `tau`; check every selected service |
| C2 | sensitivity compatibility along the workflow DAG | `sensitivity_out`, `max_input_sens`; propagate along real parent edges |
| C3 | `count({s: dept(s) != owner}) <= K` | `dept_id`, owner department, cross-department quota `K` |
| C4 | `tier(v) >= ceil(max_upstream_sensitivity / 2)` | `sandbox_tier`, upstream sensitivity, topological cascade |
| C5 | `sum(response_time(s) for s in critical_path) <= T_SLA` | response time, DAG critical-path operator, SLA threshold |

The formulas above are the **midterm project definitions**. They are not claimed to be copied verbatim from any one external paper.

## Corpus

| arXiv | Paper | Main use in the audit |
|---|---|---|
| [1811.11272](https://arxiv.org/abs/1811.11272) | Bi-Objective Optimization for Energy Aware Internet of Things Service Composition | Path-aggregated QoS, execution time, and latency precedent for C5 |
| [2001.00975](https://arxiv.org/abs/2001.00975) | Privacy in Data Service Composition -- k-Protection | Privacy-preserving service composition and leakage-control motivation for C2 |
| [2105.15135](https://arxiv.org/abs/2105.15135) | Reputation Bootstrapping for Composite Services using CP-nets | Reputation propagation and composition topology for C1 |
| [2205.03226](https://arxiv.org/abs/2205.03226) | Trust-SIoT: Towards Trustworthy Object Classification in the Social Internet of Things | Multi-dimensional trust measurement and trust-based selection for C1 |
| [2401.01029](https://arxiv.org/abs/2401.01029) | Context-Aware Trustworthy IoT Energy Services Provisioning | Context-dependent trust assessment combined with service composition for C1 |
| [2504.13767](https://arxiv.org/abs/2504.13767) | Access control for Data Spaces | Owner sovereignty and continuous policy enforcement; general context for C3 |
| [2603.00129](https://arxiv.org/abs/2603.00129) | Safe Multi-Agent Deep Reinforcement Learning for Privacy-Aware Edge-Device Collaborative DNN Inference | CMDP, privacy/delay constraints, and constrained RL; contextual support for C2/C4 |
| [2604.04082](https://arxiv.org/abs/2604.04082) | Styx: Collaborative and Private Data Processing With TEE-Enforced Sticky Policy | Sandboxed execution and policy checks over derived data; operational context for C2/C4 |

Each item has a PDF and a `pdftotext -layout` extraction in this directory. The detailed boundary analysis is in [`reports/trusted_constraints_literature_audit.md`](../../reports/trusted_constraints_literature_audit.md).

## Claim boundary

The corpus supports the motivation for trust-aware selection, privacy/data-policy enforcement, constrained optimization, sandboxed execution, and path-based QoS. It does **not** establish that the literature already contains the exact combined C1-C5 model. In particular:

- no directly matching source was found for the C3 cross-department cardinality rule;
- no directly matching source was found for the C4 tier equation;
- C5 must use a real longest/critical path on a branching DAG, rather than a sum over all selected nodes;
- k-Protection, Trust-SIoT, HC-MAPPO-L, and Styx are motivation/adaptation sources, not exact reproductions of the midterm model.

The current ConsDag v2 compiler dataset uses `budget`, `deadline`, `privacy`, `tool_auth`, and `order`. It should therefore be described as a **trusted-data-space-inspired tool-planning instantiation** until a matched C1-C5 subset with an independent verifier is added.

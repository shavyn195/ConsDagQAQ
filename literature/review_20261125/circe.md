# CIRCE: Constraint Intermediate Representation for Complexity Estimation

Source: [arXiv:2610.41089](https://arxiv.org/abs/2610.41089), v1, 2026-10-30. The arXiv title, authors, date, and PDF URL were checked on 2026-11-25. Local extraction hash is recorded in `source_verification.json`.

## Main idea

CIRCE asks an LLM to extract variables, constraints, domains, and a query into a constraint intermediate representation (CIR), then deterministically compiles that representation into a graph. It uses the graph to estimate whether a target LLM will answer correctly; it is a complexity-prediction system, not an execution planner or a per-request safety guard.

## Experimental design

The paper studies seven reasoning benchmarks and four target LLMs, with 200 evaluation problems per benchmark. It reports NLL and AUROC. Results are averaged over three random split seeds and, for graph models, four encoder seeds. Evaluation tasks include explicit and implicit constraints.

It separately audits the representation. Parsability is checked on all evaluation problems. Where rule checkers cover the full structure, semantic correctness is checked over all examples; for the other four benchmarks, 20 source/CIR pairs per benchmark are manually reviewed. The authors report that direct graph generation can be substantially less correct than CIR followed by a deterministic graph builder on a benchmark where full checking is possible. The paper also states that some CIRs are produced by one LLM and that correctness remains incompletely verified on benchmarks without full checkers.

## Relevance and boundary

CIRCE is a direct precedent for semantic extraction separated from deterministic compilation, and for measuring representation correctness independently of downstream task success. Its target, representation, and downstream use differ from ConsDAG, so it does not settle the present system comparison. It does show why a valid witness and an executable checker do not alone establish that generated request language carries the intended semantics. Our corpus currently has no independent human semantic audit; that limitation must remain explicit.


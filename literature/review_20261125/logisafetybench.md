# LogiSafetyBench / LogiSafetyGen review

Source: [arXiv:2601.08196](https://arxiv.org/abs/2601.08196), *Evaluating Implicit Regulatory Compliance in LLM Tool Invocation via Logic-Guided Synthesis* (2026 preprint). Full text was read from the local extracted PDF; arXiv API metadata was checked on 2026-11-25. Venue status was not independently verified.

## Method and evaluation

LogiSafetyGen translates regulations into LTL safety oracles, synthesizes executable traces with a logic-guided fuzzer, masks safety-critical steps from the user instruction, and checks both functional state and execution-trace compliance. The benchmark contains 240 human-verified tasks (120 paired samples) in financial services, tele-healthcare, and smart-home IoT. The paper reports a 73.9% aggregate acceptance rate for oracle candidates after three independent author-review rounds and a 70.6% acceptance rate for instruction/masking candidates. It evaluates 13 LLMs, with eight representative systems in the main text.

The human-verification protocol reviews both the regulatory formulas and the concrete instruction/trace pairs. This is materially stronger evidence for the intended semantics of implicit requirements than executable witnesses alone provide. The task is still a different one from ConsDAG: hidden regulatory steps are inferred and inserted into Python/tool traces; it does not evaluate a trained compiler's typed per-request record, scope/evidence fields, or the E/I/N record-versus-execution matrix used here.

## Consequence for ConsDAG

- Do not claim ConsDAG is the first executable benchmark for implicit constraints, latent compliance, or safety constraints in tool use.
- The remaining benchmark distinction is the controlled same-task E/I/N rendering and its joint record/execution evaluation with template/tool/structure holdouts. That is a narrower design choice, not proof of semantic novelty or broader realism.
- The paper's human verification makes ConsDAG's lack of independent semantic review a central validity limitation. A witness proves that the generated world has a feasible plan; it does not show that a reader would recover the intended implicit constraint from the request.
- If independent review remains out of scope, describe labels as generator-defined construction conditions and avoid claims that implicit constraints were human-interpretable or pragmatically validated.

## Source integrity

arXiv API returned the title, seven authors, abstract, identifier, and publication date. The downloaded local PDF and extracted full-text SHA-256 values are recorded in `source_verification.json`. The paper is cited as an arXiv preprint only.

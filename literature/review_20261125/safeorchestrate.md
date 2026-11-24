# SafeOrchestrate review

Source: [arXiv:2611.09364](https://arxiv.org/abs/2611.09364), *SafeOrchestrate: Runtime-Checked Intent-Driven Orchestration for Cyber-Physical Systems*, v2 metadata verified by the arXiv API on 2026-11-24. The local full text was reviewed against Sections 3–5 and the limitations.

SafeOrchestrate decomposes natural-language intent into atomic goals, generates LTL-style runtime-checkable specifications, grounds symbols to role-aware MCP affordances, and checks candidate actions with SMT-backed guardrails before execution. It compares against direct LLM-to-MCP calls on simulated smart-home, greenhouse, and industrial tasks, using required-action accuracy and MCP execution similarity.

This is a clear architecture-level neighbor to compiler/plan/execution separation. Its own paper states that most evaluated tasks are single-rule with an empty constraint set; cross-rule and safety-constraint enforcement is illustrated with a worked example rather than quantified in the main task results. It does not train a compact request compiler or evaluate typed record fidelity, E/I/N renderings, or field/seed error propagation. Therefore it rules out novelty claims for the broad architecture and runtime checking, while leaving a narrower empirical comparison possible.

The source is cited as an arXiv preprint. Local PDF and extracted-text hashes are in `source_verification.json`.

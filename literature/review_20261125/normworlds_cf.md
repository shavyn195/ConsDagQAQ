# NormWorlds-CF review

Source: [arXiv:2607.03957](https://arxiv.org/abs/2607.03957), *NormWorlds-CF: Solver-Verified Counterfactual Normative Reasoning with Metamorphic-Relation GRPO*, v2 metadata verified by the arXiv API on 2026-11-24. The local full text was reviewed for task construction, paired splits, structured outputs, and post-training experiments.

NormWorlds-CF separates an executable symbolic world, its text rendering, and deterministic solver labels. It provides proof/falsification certificates and compact paired-world change records. The benchmark has 270 root families and 1,080 canonical-to-variant pairs; variants from a root remain in one split. Its Qwen3-4B GRPO validation averages three seeds and compares reward geometries.

This precludes broad novelty claims for solver-verified paired worlds, structured change records, family-level splitting, and multi-seed structural post-training diagnostics. The task differs from ConsDAG: it predicts normative counterfactual changes from a structured world, rather than compiling language-rendered E/I/N constraints into records consumed by a fixed planner. Any distinction must be stated at that task/interface level.

The source is cited as an arXiv preprint. Local PDF and extracted-text hashes are in `source_verification.json`.

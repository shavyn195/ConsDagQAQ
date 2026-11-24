# CARL: Constraint-Aware Reinforcement Learning for Planning with LLMs

Source: [arXiv:2607.04854](https://arxiv.org/abs/2607.04854), v1, 2026-07-06. The arXiv title, author list, date, and PDF URL were checked against the abstract page on 2026-11-25; publication venue was not verified. Local extraction hash is recorded in `source_verification.json`.

## Main idea

CARL changes the planner's training objective. It compares output log-probabilities under constrained and constraint-ablated inputs and adds a constraint-awareness signal to the task reward. Its main implementation uses GRPO; the paper also studies PPO and a constraint-aware DPO variant.

## Experimental design

The evaluation covers BlocksWorld, TravelPlanner, and T-Eval: symbolic planning, realistic travel planning, and tool-use planning. T-Eval is treated as containing implicit constraints; GPT-4o with a lightweight prompt extracts them. The T-Eval split uses 128 of the 553 evaluation items for training and the remaining 425 for testing. The two other benchmarks use their published train/test partitions.

The reported metrics differ by task: accuracy for BlocksWorld; hard-constraint micro/macro pass rate and final pass rate for TravelPlanner; per-example-averaged precision, recall, and F1 for T-Eval. The default model is Qwen3-8B with GRPO, on one node with 8 A100 GPUs, query batch 64, and 8 rollouts per query. The paper includes reward ablations, size comparisons, prompt baselines, and constraint-extraction masking sensitivity.

## Relevance and boundary

This is a direct prior for constraint-aware rewards, planning under implicit constraints, and using a strong model to extract them. It rules out presenting those ideas, or our failed GRPO credit-allocation variant, as novel in isolation. CARL trains a planning policy end to end; it does not establish that an independently trained small compiler improves a planner under a fully information-matched comparison. That narrower system claim still needs the queued public-input E2 result and must survive cost and seed scrutiny.

The T-Eval labels are model-assisted extraction from a small split, not independent human validation. This provides a methodological precedent for reporting the provenance of implicit labels, but it does not validate our generator-defined semantics.


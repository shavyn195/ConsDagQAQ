# AdaPlanBench review

Source: [arXiv:2606.05622](https://arxiv.org/abs/2606.05622), *AdaPlanBench: Evaluating Adaptive Planning in Large Language Model Agents under World and User Constraints*, v2 metadata verified by the arXiv API on 2026-11-24. The local full text and limitations were reviewed.

AdaPlanBench builds on 307 household tasks augmented with world and user constraints. Its multi-turn runtime reveals hidden constraints after a proposed plan violates them, then evaluates iterative replanning across ten models. The paper reports a best accuracy of 67.75% and says constraint checking and rubric scoring rely on LLM judges.

It is a direct neighbor for implicit/progressively disclosed constraints under planning, but tests interactive adaptation rather than one-shot language-to-record compilation. Its judge dependence also differs from ConsDAG's deterministic executor, without solving ConsDAG's separate problem that generator-defined labels are not independently validated against human interpretations.

The source is cited as an arXiv preprint; the API comment lists COLM 2026, but this review does not treat that comment as independent proceedings verification. Local PDF and extracted-text hashes are in `source_verification.json`.

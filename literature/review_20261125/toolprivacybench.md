# ToolPrivacyBench review

Source: [arXiv:2606.28061](https://arxiv.org/abs/2606.28061), *ToolPrivacyBench: Benchmarking Purpose-Bound Privacy in Tool-Using LLM Agents* (2026 preprint). Full text was read from the local extracted PDF; arXiv API metadata was checked on 2026-11-25. Venue status was not independently verified.

## Method and evaluation

ToolPrivacyBench evaluates whether private facts are routed only to tools and information sinks authorized by their purpose. It contains 2,150 cases: 1,150 synthetic business workflows and 1,000 cases adapted from tau-bench, API-Bank, BFCL, and AppWorld. The public-derived portion reuses multi-step task structure, then adds private atoms, tool-purpose policies, free-text sinks, mock backends, and audit rules. Execution logs and backend records are checked against a policy knowledge base.

The authors inspect representative cases and independently re-annotate a stratified sample of authorization pairs. Across 215 sampled cases and 21,994 private-atom/tool pairs, they report 93.1% raw agreement and Cohen's kappa 0.86 before adjudication; 499 changes were made during adjudication. This is sampled reliability evidence, not a claim that every label was independently re-annotated.

## Consequence for ConsDAG

- This is not the same compiler task: its policy knowledge base is provided to the evaluator and governs purpose-bound disclosure during multi-tool execution; it does not train a language-to-typed-constraint compiler or evaluate E/I/N records.
- Its construction is a useful standard for the dataset argument: combining synthetic control with public-derived workflow structures, executable auditing, sampled independent re-annotation, agreement statistics, and adjudication.
- ConsDAG currently has none of the independent label-reliability evidence. Its single synthetic tool world and generator-defined semantics are consequently a larger external-validity limitation than the benchmark's size or number of model runs.
- Do not use ToolPrivacyBench as evidence that privacy constraint semantics in ConsDAG are validated. Use it to state the gap and to motivate future public-task adaptation and annotation reliability work.

## Source integrity

arXiv API returned the title, four authors, abstract, identifier, and publication date. The downloaded local PDF and extracted full-text SHA-256 values are recorded in `source_verification.json`. The paper is cited as an arXiv preprint only.

# ConsDAG v6 Experimental Design

Date: 2026-11-24

## Decision

V6 is a controlled benchmark and evaluator audit, not a new compiler architecture. It retains the v5 E/I/N task construction and adds a held-out `privacy + tool_auth` type-pair split. Every combination containing both types, including supersets, is rejected from train, dev, and every other test split; the pair's exact two-type set is sampled into `test_composition_ho`. The other v5 splits remain available so template, tool-name, compound-structure, and type-pair results are not conflated.

Each E/I/N triplet now carries machine-checkable hidden witnesses. E/I records contain the cited query span, a feasible gold-plan witness, and a counterfactual plan that violates the constraint after that constraint is removed. N records contain empty gold, an unchanged default-plan witness, and typed synthetic near-miss metadata. An independent verifier replays plan completion and constraint predicates without calling the planner/checker used by generation. This verifies the generated artifact; it does not establish that a person would recover every implicit label.

The v5 files, saved predictions, metrics, and original evaluator path remain the historical comparison. V6 records are generated into `data/processed_v6/`, model outputs go under `outputs/e1_v6/`, and the original seed set (42/43/44), LoRA recipe, and strict/core field metric definitions are retained. The trainer selects a v6 fail-closed execution evaluator only when records declare `spec_version: v6`.

## Research Questions

1. Does supervised compilation improve fail-closed executable fidelity over the same checkpoint's zero-shot predictions on paired task groups?
2. Does performance survive an unseen pair of constraint types when tool roles, task structure, and wording remain in the training world?
3. How much of executable success coincides with strict record correctness, core correctness, and exact evidence recovery?
4. Are N errors caused by malformed output, a nonempty constraint set, or a wrong top-level query state?

No claim of human recoverability, ambiguity handling, or CCF-B readiness follows from synthetic verification alone.

## Data and Freeze

The deterministic generator uses seed `20261124` and 5,700 groups (17,100 records): train 4,000; dev 300; and 350 each for `test_tpl_ho`, `test_tool_ho`, `test_struct_ho`, and `test_composition_ho`. Every group has exactly one explicit, implicit, and none record over the same task and goal. E/I labels encode the generator's surface conditions only. N denotes the generated no-constraint / waiver condition, not ambiguity or insufficient information.

`test_composition_ho` uses the train tool world and train wording. Its sole positive type set is `privacy + tool_auth`; no other split contains both types together, even with a third type. The established v5 `test_struct_ho` remains a compound shift and is not described as an isolated structure intervention. The type-pair filter changes feasible-task selection and constraint cardinality, so this is a held-out pair benchmark slice, not a causal composition intervention. All JSONL byte hashes, split counts, group triplets, witness checks, and cross-split query/goal/group overlap counts are recorded before model inference.

The human recoverability and N-control audit is pending. The frozen sampling, visible input package, rubric, and agreement denominators are specified in `v6_human_review_protocol.md`; two blinded reviewers label the same held sample. The gate requires at least 90% raw reviewer agreement and at least 90% adjudicated compatibility with the frozen gold on recoverability, with every disagreement adjudicated. If the gate is unmet, affected results remain synthetic benchmark measurements and the semantic claim is killed.

## Metrics

- `constraint_micro.f1`: strict typed fields (type, state, severity, scope, params), not full-record exactness.
- `constraint_core_micro.f1`: type + params only; scope/state/severity/evidence are not checked.
- `record_exact_match`: strict fields plus top-level query state.
- `evidence_exact_rate`: exact evidence span on matched strict constraints; report separately from full-record exactness.
- `safe_success_v6`: a strictly parsed output induces a plan that completes and violates no gold constraint. Malformed output cannot pass.
- `faithful_success_v6`: `safe_success_v6` plus the gold minimum-edit plan criterion; for N, the output must be a valid empty/no-op compilation.
- N false alarms are split into parse failure, nonempty constraints, and wrong query state; `none_any_contract_alarm` is their union. The predeclared N gate is below 5% broad alarm per subtype and split.

Report per seed and per split, plus three-seed mean and sample SD. Differences use paired task-group bootstrap with the three observed seeds fixed; intervals do not estimate seed-population uncertainty. Do not use strict/core F1 or safe success as substitutes for faithful behavior.

## Hypotheses and Stop Rules

- H1: trained 1.7B and 4B each improve over their same-base zero-shot arm on the predeclared constrained-record faithful metric. Require a positive paired 95% task-group interval in all three seeds on dev and `test_composition_ho`; otherwise reject the broad H1 claim and report split-level effects.
- H2: any non-inferiority claim against a frontier PE baseline keeps the v5 margin: the lower paired 95% bound must exceed -3 percentage points on every named split. The v5 evidence already fails this on tool-name holdout; no cross-split competitiveness claim is presumed.
- H3: transfer is called only per named shift. Compare `test_tool_ho` minus `test_struct_ho` constrained faithful rates, resampling task groups independently within each split, conditional on the three observed seeds. For this compound structure shift, keep the frozen v5 limits: interval upper bound at most a 5-point drop for transfer; interval lower bound at least a 10-point drop for non-transfer; otherwise inconclusive. This comparison is descriptive and does not isolate a causal structural effect.
- H4: the fixed DeepSeek-v4-pro ten-example arm's broad N alarm at or above 5% for any subtype/split fails that subtype's model-diagnostic threshold. It does not invalidate the gold labels; only the blinded human review can establish label validity. No examples are removed after observing model errors.
- Data/evaluator stop: any nonzero cross-split query/goal/group leakage, invalid witness, non-deterministic hash, unparseable reference prediction, incomplete data/source/model provenance, or failing fail-closed test blocks a model queue.
- Annotation stop: absent blind review, semantic claims remain exploratory even if model metrics pass.
- Resource stop: the single-GPU queue has a 30 GPU-hour wall-time cap. A run that would exceed the remaining budget is terminated and marked incomplete; no partial run enters aggregate metrics.

## Compute Protocol

Use the RTX 4080 SUPER 32 GB, **bf16**, frozen v5 LoRA settings (rank 16, alpha 32, dropout 0.05, learning rate 2e-4, three epochs, gradient accumulation 4, max sequence 1,280, max generation 384) and seeds 42/43/44 for 0.6B, 1.7B, and 4B. Do not run smoke or partial training jobs. Before any model job, validate the frozen data hashes and use that model's tokenizer to prove that every training example and gold answer fits the registered length budgets; fail before training if any example would be silently dropped or truncated. Seed 42 writes one zero-shot evaluation per size because decoding is deterministic; later seeds skip duplicate zero-shot inference. The queue writes logs, a source/data/model/environment provenance record, an append-only JSONL manifest, completion fingerprints, metrics, predictions, and v6 CPU rescoring under `outputs/e1_v6/`.

The six available v5 1.7B/4B runs consumed 20.8 GPU-hours in aggregate. The expanded v6 evaluation and three 0.6B jobs make 30 GPU-hours a hard cap rather than a guarantee that the full matrix will finish. The queue reserves and records each v6 model job, records budget-truncated runs as incomplete, refuses incomplete outputs, and only computes confirmatory trained aggregates from complete seed triplets. Preserve enough budget to finish the confirmatory 1.7B and 4B seed triplets before spending remaining time on 0.6B; if the cap prevents a complete triplet, report that arm as incomplete.

## External Baselines and Claims

The PE runner uses only `DASHSCOPE_API_KEY`; it never writes the key to config, logs, or results. PE outputs are cached by request fingerprint, and a failed request does not contribute a partial score. If no key is configured, the PE comparison remains pending.

Prior-art checks use the extracted full texts: CGAP ([2610.41040](../literature/extracted/library/01_constraint_compiler/2610.41040_CGAP/2610.41040_CGAP_fulltext.txt), especially evidence and conditional planner guarantees, lines 424-437 and 652-675), LogiSafetyBench ([2601.08196](../literature/extracted/library/06_web_supplement_20261121/2601.08196_LogiSafetyBench/2601.08196_LogiSafetyBench_fulltext.txt), lines 741-745 and 1297-1300), AM-Bench ([2610.18090](../literature/extracted/library/03_paired_benchmark/2610.18090_AM-Bench/2610.18090_AM-Bench_fulltext.txt), paired information conditions, lines 210-244), EffectWorld ([2610.35981](../literature/extracted/library/03_paired_benchmark/2610.35981_EffectWorld/2610.35981_EffectWorld_fulltext.txt), lines 450-457), and LIFT ([2610.28819](../literature/extracted/library/03_paired_benchmark/2610.28819_LIFT/2610.28819_LIFT_fulltext.txt), matched conditions, line 302). These works preclude claiming novelty for typed compilation, evidence spans, implicit compliance, paired conditions, execution checks, or clarification as general ideas.

The requested identifier `2610.41089` resolves in the local extracted corpus to CIRCE; the extracted SCA paper is `2610.25552`. The v6 rationale uses the SCA caveats about omitted calls and false alarms only under the corrected identifier. See [the v5 evidence review](v5_evidence_review_20261124.md) and [the literature audit](_audit_work_20261124/literature_notes.md) for the claim ceiling and detailed sourcing.

## Implementation and Verification Status

The local freeze contains 17,100 records. `verification_report.json` is PASS, with all 45 pairwise query/goal/group overlap counts zero and no invalid witness. Rebuilding with the same seed in a separate temporary directory produced identical bytes for all six JSONL files; the check is recorded in `outputs/v6_analysis/determinism_check.json`. All 17,100 gold compilations parsed and passed the v6 faithful reference-consistency check. These are data/evaluator checks, not model results or independent semantic validation.

The local full suite passed 116 tests with two torch-dependent skips. Git Bash syntax and Python compilation passed. The blind-review packets contain 250 unique requests and remain `exported_not_reviewed`.

No v6 GPU training or PE inference has run. In this turn, do not train, connect to the server, or call the PE API; the local implementation and tests are prepared for the owner to synchronize after credentials are configured. Before launch, stage the v6 sources, tests, scripts, and data into `/root/ConsDagV5`, preserve historical v5 artifacts, verify the pre-recorded hashes, and start the idle-GPU relay. The relay waits for the existing v5 training process to finish, then runs the queue. `bash scripts/run_pe_v6.sh` starts the separately cached PE arms when `DASHSCOPE_API_KEY` is available in the environment.

V6 can produce a reproducible synthetic benchmark finding within the resource cap. The current evidence does not establish a CCF-B contribution: novelty must remain the measured held-out-pair/evaluator audit, human recoverability is unverified, and the v5 cross-heldout non-inferiority claim has already failed. If the preregistered gates fail, report the negative result or stop that claim instead of extending the experiment until it passes.

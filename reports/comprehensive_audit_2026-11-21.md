# ConsDAG comprehensive audit (2026-11-21)

## Decision

The project is suitable for continued development, but the current protocol is **not yet a valid CCF-B main-experiment package**. E1 can continue as a labelled compiler feasibility/diagnostic study. E2/GRPO must remain blocked until its information permissions, independent task-success checker, and exploit tests are implemented.

This report separates evidence that can be reused from claims that must not be made. It supersedes any older statement that the three innovations have already been confirmed.

## Evidence currently reusable

| Item | Result | Permitted interpretation |
| --- | --- | --- |
| v2 dataset structural checks | 15,000 rows; witness recheck, schema, pair integrity and current leakage checks pass | Synthetic E1 contract-fitting benchmark; not evidence of real implicit pragmatics |
| 0.6B seed 42 | v3 strict F1 `0.729/0.630/0.303` (dev/template-HO/tool-combination-HO) | Single-seed feasibility result |
| 0.6B scope-free diagnostic | `0.979/0.834/0.838`; oracle scope replacement gives the same values | Diagnostic upper bound / relaxed metric; not full compiler F1 |
| 4B seed 42 | v3 strict F1 `0.452/0.321/0.067` | Completed single-seed run; does not support monotonic scaling |
| 1.7B seed 42 | NaN from step 4400 | Failed run; excluded from trained scaling |
| qwen-max original prompt | strict F1 `0/0/0`, parse about `0.987/0.983/0.968` | Closed-model prompt baseline on this synthetic contract; not GPT-4o and not a verbatim ATLAS reproduction |
| code tests | `26 passed` | Regression suite currently passes after finite-value guards and scope-context prompt changes |

## P0/P1 blockers

1. **Scope measurement is under-specified in the old run.** Gold scope is derived from graph node properties, while the old prompt exposed only a role vocabulary. The compiler therefore lacked the information needed to justify a scope prediction. The E1 runner now exposes compact task-space node metadata (cost, duration, recipient, data classes and terminal flag) in a separate prompt version. Results from that version must not overwrite old outputs.
2. **Implicit construct validity is not established.** The text-quality scan flags 728/12,000 training rows (6.07%), plus 52/900 dev, 55/1,050 template-HO and 35/1,050 tool-combination-HO rows. A single-person review found only 8/90 candidate implicit templates, with no accepted candidates for `tool_auth` or `order`. Current I scores must be called synthetic I-template scores until templates are repaired and independently reviewed.
3. **Calibration and abstention have no target distribution.** Gold confidence is always `1.0` and abstain is always `false`; selective risk and abstention claims are unsupported.
4. **E2 reward information is not closed.** The proposed false-negative penalty needs a declared source for the true constraint set `C*`, and every baseline needs the same information permission. The current external anchor checks plan structure, which can reward empty or incomplete plans. Add independent success and legality checks plus exploit cases: empty plan, legal-but-incomplete plan, complete-but-violating plan, and complete-and-satisfying plan.
5. **Literature novelty language must be narrowed.** Recent local corpus checks identify NOMOS, CGAP, CIRCE, PRefine, SCA, CASEL, PolicyGuide and Implicit Intelligence as occupying typed IR, evidence/provenance, UNKNOWN/abstention, deterministic compilation, implicit preference extraction, selective execution, or symbolic constraint mining subspaces. ATLAS already formalizes explicit/implicit constraints with scope. The paper may claim the narrower end-to-end combination and the constraint-to-node-to-trace RL interface only after direct comparison; it must not claim that trained compilers, evidence spans, implicit constraints, or abstention have zero prior coverage.
6. **Corpus identity needs repair.** Use `literature/library/manifest.json` and `literature/extracted/library` as the canonical 57-paper inventory. Several legacy `literature/extracted/papers` directory labels are wrong (for example, folders labelled CARL, LANG-NCO, or TAG contain unrelated papers), so those paths must not be cited as evidence.

## Dataset audit

The current verifier proves witness satisfaction and E/I/N pairing, but it replays the constructed witness and does not independently test goal completion, violating trajectories, or trace-level anti-avoidance. The tool-held-out split should be named `tool-combination-held-out`; it is not a claim of unseen role vocabulary. Before the formal rerun:

- repair or filter the flagged templates at the **group** level so all E/I/N members stay aligned;
- obtain two blind reviewers for every implicit template family and report filtering counts and Krippendorff alpha;
- add ambiguity/abstention examples with non-constant confidence targets;
- add independent success/violation trajectories and a checker that is separate from the witness generator;
- freeze a new dataset/scorer hash and keep all old outputs under a legacy tag.

## E1 execution decision

The server RTX 4080 SUPER 32GB has BF16 support. The old queue script was unsafe because it pointed at a stale local path and old automatic sequencing. The active run is therefore a **diagnostic E1 scope-context run** with:

- BF16, finite-loss checks, gradient clipping and post-step finite-parameter checks;
- an independent output directory and manifest;
- smoke validation before full training;
- the same v2 data hash and v3 scorer, explicitly labelled legacy/synthetic;
- 0.6B first, then 1.7B and 4B only after the preceding run has a complete manifest. The queue is currently alive on 0.6B; its output is isolated from the legacy table.

The 1.7B NaN result is not reused. If the repaired dataset and independent checker pass, a second formal sequence will be launched from a new frozen data version.

## Claims currently prohibited

Do not write that innovation 1 is verified, that implicit constraints have been shown to be pragmatic reasoning, that the three sizes establish scaling, that confidence/abstention are calibrated, that tool-held-out proves unseen-tool generalization, or that E2/GRPO has downstream gains.


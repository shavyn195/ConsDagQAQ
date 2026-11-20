# Constraint Compiler Experiments

This is a clean experiment workspace for the Evidence-Bound Constraint Compiler pilot and the
follow-up v2 evidence campaign (per `docs/执行手册` S1-S8).
No dataset, trainer, or result from `agentl1_trusteddataspace` is used as experimental evidence.

## Current campaign (v2, trusted-data-space background)

- `data/processed_v2/`: 5,000 groups x 3 variants (E/I/N) = 15,000 records; five constraint
  families (budget/deadline/privacy/tool_auth/order) grounded in trusted-data-space rules;
  dual group-held-out splits (tool-pair 2-subset + template pools), S5 witness recheck and
  S7 leak checks all PASS (`verification_report.json`).
- `src/build_dataset_v2.py`, `src/dataset_v2_spec.py`, `src/verify_dataset_v2.py`:
  generator, frozen role/template spec, independent verifier.
- `src/run_e1.py`: E1 T/Z arms (0.6B/1.7B trained vs zero-shot) on the local RTX 4060.
- Pending: S6 oracle recoverability (needs a strong-model API), E1 P arms (PE baselines),
  E2/E3 gated-reward + ablations with the corrected miss penalty.

## Directory contract

- `data/raw/`: source or hand-authored pilot examples.
- `data/processed/`: frozen pilot v1 train/dev/test JSONL and schema validation reports.
- `data/processed_v2/`: v2 full corpus (pre-registered configs in `configs/dataset_v2.yaml`).
- `configs/`: run configs and pre-registered pilot decisions.
- `src/`: data generation, schema/verifier, training, and evaluation code.
- `models/`: freshly downloaded base weights (ModelScope), never reuse possibly fine-tuned caches.
- `outputs/`: adapters, predictions, logs, and machine-readable metrics.
- `reports/`: human-readable run and audit reports (`experiment_log.md` is the running ledger).
- `literature/`: downloaded papers and literature-check notes for this experiment.

## Start gates

Do not launch GPU training until the schema, E/I/N pair integrity, train/test split,
constructive-feasibility checks, prompt baselines, and evaluation script pass a CPU
preflight. The first GPU run is a bounded 0.6B pilot on a hosted GPU, with two frozen prompt
conditions and a 75-optimizer-step LoRA run. It is only a pipeline/learning-signal pilot:
this 201-record hand-authored dataset has no independent oracle or human review, no
abstention examples, and no group-held-out tool/template pools, so it cannot establish
calibration, abstention, or broad generalization claims.

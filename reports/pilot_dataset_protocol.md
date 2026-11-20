# Pilot dataset protocol

The pilot generator in `src/generate_pilot.py` creates controlled synthetic tasks
for the compiler only. Each task group contains one explicit (E), one implicit (I),
and one no-constraint (N) query. The graph, witness, task goal, and role vocabulary
are held fixed within a group; only the query rendering and gold constraint state
change. The E/I pair shares the same typed constraint set, while N is a contrast arm
with an empty set.

The five constraint families are budget, deadline, privacy, tool authorization, and
ordering. Each constrained record stores type, description, exact evidence span,
state, confidence, severity, role scope, and verifier parameters. The witness is a
topological execution of the graph. `src/pilot_schema.py` checks graph validity,
witness feasibility, exact span containment, scope vocabulary, and E/I/N integrity.

The default output is 50 train groups and 17 test groups (150 and 51 records).
Splitting is at group level, so no E/I/N siblings are separated across train and
test. The examples are deliberately transparent and synthetic. This pilot reuses a
small set of role graphs and wording templates across splits, so it is not a
group-held-out generalization test. It does not claim natural-language oracle
recoverability, human agreement, calibration quality, or abstention performance;
those are required before scaling this pilot into the full benchmark.

Run:

```text
python src/generate_pilot.py
python src/validate_pilot.py
python -m pytest -q tests/test_pilot_dataset.py
```

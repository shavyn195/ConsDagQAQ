# v6 Blind Recoverability Review Protocol

Status: frozen protocol; 250 unique items exported to `data/review_v6_seed20261125_n5/`. Human review remains pending. The export does not establish that review has occurred.

## Purpose and Scope

The audit checks whether independent readers can recover the generated implicit constraints and recognize generated no-constraint near-misses from the exact information shown to the compiler. It tests this synthetic prompt contract. It does not validate real-world policy truth, establish general ambiguity handling, or replace execution verification.

## Sample Design

The default packet selects five records without replacement for each available implicit type-by-split cell and each none subtype-by-split cell. The splits are `train`, `dev`, `test_tpl_ho`, `test_tool_ho`, `test_struct_ho`, and `test_composition_ho`. Implicit types are `budget`, `deadline`, `order`, `privacy`, and `tool_auth`; none subtypes are `waiver`, `revoked`, `other_party`, and `permission`. Cells with no implicit examples of a type are absent by construction; the selection manifest records candidate and selected counts for every cell.

Selection is deterministic. The exporter ranks each candidate by SHA-256 of the fixed seed, stratum key, and source sample ID, then takes the first five. A source record selected for more than one cell appears once in each reviewer packet; the private manifest records every stratum membership and pairwise overlap. Report cell results and the overlap counts. Do not treat overlapping selections as independent observations or use the small sample to estimate population prevalence.

## Blinding and Materials

Run `python src/build_v6_review_packet.py --confirm-ready` only after regeneration is complete and the v6 generation and verification reports both match every split hash and show verification `PASS`. The exporter refuses to overwrite an existing packet directory. Store the output under `data/review_v6_*`, outside `data/processed_v6/`.

Give `reviewer_a.jsonl` and `reviewer_b.jsonl` to separate reviewers. Each contains the exact messages produced by `run_e1.chat_messages_v4(row)`, including the policy card, output schema, tool catalog, and query. The packet does not reveal source IDs, split, variant, selected type/subtype stratum, gold, witnesses, default plan, or model predictions. Do not give reviewers `selection_manifest.json` or access to the source gold files. Reviewers must work independently and submit before discussing items.

The source environment shown to reviewers is the compiler-visible tool catalog in those messages. Do not add the hidden task graph, planner state, witness plans, or default plan: those are not in the model input. Reviewers may use only the packet contents and this protocol.

## Annotation

For each item, reviewers record the predicted top-level `query_state`; every supported constraint's type, state, severity, scope, and parameters; the full supporting query sentence or clause copied exactly as its evidence span; and uncertainty at both constraint and item level. They also answer whether the query supports an empty constraint set and leaving the default plan unchanged (`yes`, `no`, or `unsure`). Constraint order does not matter. Do not infer hidden requirements from the source split or assume each packet item contains a positive constraint.

Use `unsure` when the visible input supports multiple materially different compilations or does not support the required parameter. Explain the uncertainty briefly. Do not force an implicit constraint into the annotation merely because it appears in training or because the tool catalog makes it executable.

## Adjudication and Gates

After both reviewers submit, match items by `packet_item_id` using the private selection manifest. Compute raw, pre-adjudication exact agreement before resolving any differences. Canonicalize JSON key order, normalize scope as a set, and sort constraints as a multiset; preserve exact evidence-span strings and parameter values. An item agrees only when both annotations match on query state, constraints, uncertainty flags, and the no-op decision. Free-text uncertainty notes and reviewer notes are retained for adjudication but excluded from exact agreement.

An adjudicator reviews every disagreement using the same blinded packet and this rubric. The adjudicator records a resolved annotation and whether the visible input is sufficient for one materially supported gold-compatible compilation. If multiple compilations remain plausible or a parameter cannot be recovered, mark the item ambiguous; do not resolve ambiguity by consulting the hidden gold. Then unblind against the frozen source row and score compatibility.

For an implicit item, gold-compatible means the adjudicated annotation contains exactly the gold constraints and no extras, with matching type, state, severity, scope, parameters, top-level query state, and exact evidence spans. For a none item, it means an empty constraint list, `query_state=none`, and a `yes` no-op response. Uncertainty notes do not themselves make a response incompatible, but unresolved material uncertainty does.

The semantic gate passes only if both raw exact reviewer agreement and adjudicated gold compatibility are at least 90% separately for implicit items and none items. Compute these category rates over selected stratum observations, so a record selected in two cells contributes once to each; disclose overlap and unique-record totals alongside the rates. Also report every type/split and subtype/split cell, uncertainty rate, and ambiguous rate. A cell below 90% is not removed; narrow or kill claims for that cell. With five items per cell, cell percentages are diagnostic and must not be presented as precise population estimates.

## Artifacts and Status

The exporter writes two randomized reviewer JSONL files and `selection_manifest.json`. The manifest stores source hashes, selection seed and quotas, per-cell candidate/selected counts, overlap, source-to-packet linkage, selection digest, packet hashes, and status `exported_not_reviewed`. It contains no model predictions. Keep reviewer responses and adjudication in a separate audit artifact; never append them to the frozen training or evaluation JSONL files.

After review, record each reviewer's completed packet hash, adjudication file hash, date, reviewer-independent IDs, raw agreement, adjudicated compatibility, per-cell results, and any deviations from this protocol. Update the status only in the separate audit artifact. Until that evidence exists, `human_validation_status` remains pending and all semantic recoverability claims remain exploratory.

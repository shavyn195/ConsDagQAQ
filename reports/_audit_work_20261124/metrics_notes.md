# v5 metrics audit (2026-11-24)

Read-only audit; original files unchanged; no training, remote access or push. E/I/N mean explicit/implicit/none data variants. Fact/Inference/Unverified are evidence labels.

## Inventory/provenance

【事实】 Local complete metrics/four trained prediction files exist for 1.7B seeds42/43/44 and4B seeds42/43. Local4B44 and0.6B v5 metrics/predictions absent. Root reports gpu_status_latest.json checked_at2026-11-24T08:29:32.334286+08:00 lists remote4B44 metrics/adapter/four predictions. This is a remote-completion snapshot, not a locally verified third seed.

【事实】 main.json/current_recheck.json are stale; v5_main_0530_20261124.json contains latest existing local3seed1.7B/2seed4B analysis.
【事实】 All5runs match localv5 data hashes and historical run_e1.py hash14979c5ddc74ae6ca83f0ad44191360b4731e7fce359f8083c3aee54011dd473. Current run_e1.py hash7c94359e35e047a501a9658216f0efa7690a2152695f5999214e193a91c44169; PE configs use current hash. Do not assume source equivalence.
【事实】 All5configs epochs3/lr2e-4/LoRA r16 alpha32/grad accumulation4/max_seq1280/max_new384/BF16. Eval batch32(1.7B)/16(4B). Differences seed/output/skip_zeroshot(false42,true43/44). Code uses dropout.05/q,k,v,o_proj/AdamW; seeds affect initialization, dropout and shuffle, not only ordering (run_e1.py:547-579,655-657).
【事实】 PE temperature0/max_tokens384, DS enable_thinking=false; few arms same demo hash; allPE prediction/data hashes match. scripts/run_e1_seed43_followup.sh targets v4; run_e1_queue_v5.sh targets v5. Progress snapshots are historical, not live status.

## Faithful constrained E/I (%; dev600,tests700)

|Arm|dev|tpl|tool|struct|
|---|---:|---:|---:|---:|
|1.7B42|98.50|96.71|91.71|95.86|
|1.7B43|98.00|95.57|75.71|75.29|
|1.7B44|99.67|97.86|71.86|77.57|
|1.7B mean +/- sampleSD|98.72+/-.86|96.71+/-1.14|79.76+/-10.53|82.90+/-11.28|
|4B42|100.00|97.43|91.00|99.71|
|4B43|99.83|92.86|95.86|97.00|
|4B two-seed mean +/-SD|99.92+/-.12|95.14+/-3.23|93.43+/-3.43|98.36+/-1.92|
|DS ten-shot|99.33|99.29|99.71|99.86|
|qwen-max zero|83.83|86.00|81.86|79.29|
|qwen-max ten-shot|88.33|84.14|87.86|86.57|

【事实】 1.7B42vs44 tool gap19.857pp/dev1.167pp;42vs43 tool16pp/dev.5pp;struct42vs43 gap20.571pp. Existing paired42vs43 CIs tool[+11.71,+20.29],struct[+16.86,+24.43]pp (seed_disagreement_1.7b_42_vs_43.json).
【推断】 Training randomization materially affects held-out behavior, not all splits uniformly. 【待验证】 \u539f\u56e0: coverage/binding/optimization/truncation or interaction. Dev/loss cannot distinguish these. No present evidence attributes this to newNaN/hardware. Best-seed1.7B is not stability.

## H1/H2 conditional uncertainty

Registered3seeds42/43/44, H2CI lower>-3pp (design_v5_ccfb.md:152,175,284-297). Existing10000-draw random20261124 paired task-group bootstrap keepsE/I together and averages fixed observed seeds within each draw. These are task-sampling intervals conditional on weights, not seed-population intervals.

|Arm/split|DiffvsDS(pp)|CI95(pp)|Interpretation|
|---|---:|---:|---|
|1.7B dev|-.61|[-1.50,+.33]|H2met only here|
|1.7B tpl|-2.57|[-3.71,-1.43]|NI not established; not proof truegap>3pp|
|1.7B tool|-19.95|[-22.62,-17.43]|H2fails|
|1.7B struct|-16.95|[-19.19,-14.76]|H2fails|
|4Bdev2seeds|+.58|[-.08,+1.50]|provisional|
|4Btpl2seeds|-4.14|[-5.71,-2.71]|provisional; margin notmet|
|4Btool2seeds|-6.29|[-8.00,-4.71]|provisional; margin notmet|
|4Bstruct2seeds|-1.50|[-2.21,-.79]|provisional|

【事实】 Even perfect4B44tool yields(637+671+700)/2100=95.619% vsDS698/70099.714%, difference-4.095pp. Original3seed toolH2 cannot be rescued under frozen data/scoring.
【事实】 1.7BH1 gains vs same-basezero+81.56,+77.57,+66.33,+57.05pp;CIs[78.39,84.61],[74.62,80.52],[63.05,69.57],[53.81,60.38]. Eachseed beatszero on eachsplit. Supports training over weakbase, not parity withstrongPE.4B3seedH1 pendinglocally. Jointall-splits claims require preregisteredHolm; per-splitCIs alone are notthat.

## Measurement

【事实】 eval_exec.py:33-52 malformed->emptyconstraints/defaultplan (operationalfail-open). Planner seespredictions;checker seesgold. Safe=completion+zerogoldviolations;faithful addsminimumgoldplanchangecount(N:no defaultdeviation). Notexactcompilation.
【事实】 run_e1.py:239-270 strictF1 type/state/severity/scope/params;coreF1 type+params. Recordexact addsquery_state andstrictmultiset;evidenceexact separate. F1,recordaccuracy,safe,faithful are distinct.
【事实】 execution ignores scope/state/severity/evidence; existinggoldmetadata corruptions retain72/72faithful each (measurement_audit_20261123.json). Faithful cannotcertifythosefields.
【事实】4B42struct faithful698/70099.71%,coreexact688/70098.29%,constrainedstrictexact390/70055.71%;overallrecordexact740/105070.48% includes350N. StrictF1.72031 isnotrecordaccuracy.1.7B42toolstrict/coreF1=.59855/.94369;struct=.63108/.94102.
【事实】 trust_env.py:17 normalizesauth/orderprecedence. Existing audit: all10 4B42struct core-differentfaithful successes and104of105DS are executionequivalent. Coremismatch alone isnotexecution-semanticerror.
【事实】 conservativeref safe67.33/63.43/61.43/55.43%,faithful0throughout. Closes thisparticularconservativeplanloophole,notallrewardhacking.
【事实】 existingDS H4N-subtypealarms all<=5%,largeststructpermission4.82%;passesregisteredcontrol,notindependenthumansemanticvalidation.

## Struct/OOD

【事实】 build_dataset_v5.py:214-215,382-385 simultaneously changesnames,stages3-5to6,alternatives3to4,finish2to3,approvalanchors,duration,whilereusingtrainwording. Constraint-count1/2/3 train2156/1451/393,tool183/133/34,struct165/139/46. Types tool order145/privacy125/auth107/deadline102/budget72 vsstructauth144/order141/deadline105/privacy98/budget93. No unseentypecombinations ineval;trainonly9directedauth/orderrolepairs.
【事实】 H3code(analyze_v5_main.py:173-196) uses2000draws notmain10000 andlabels bothzerobases transfers. Independenttask-samplecomparison,notcontrolledsametaskintervention. tool-struct1.7B-3.14ppCI[-6.43,+.19];4B2seed-4.93ppCI[-6.64,-3.21].
【推断】 Canreport no registeredH3drop onthiscompositeslice,notisolatedstructuralgeneralization/broadOODrobustness/deepergraphcausality. CPUprobe: freezesemantics/wording,crossname*structure,observed/unseenrolepairs;posthocdiagnosticcannotreplacev5test.

## Cost/next

【事实】 train_seconds startsbeforeload/optionalzeroandendsaftertrainedeval(run_e1.py:646,670,705-706),notpuretrainingtime.Seed42v43costsrequireseparation.UseactualtimingorpilotforGPUrequests.
Next: verifylocallyremote4B44withoutseedselection;freezeintegrity/truncation;stratifyexistingE/I/Nbybinding/rolepair/combination;controlledCPUname*structureprobe;independentinformation-sufficiency/clarificationpilot.MoreSFTseeds/GRPOalonedonotfixmeasurementvalidity.

## Independent raw recheck complete
metrics_recomputed.json and metrics_per_record.json are independently re-scored from local JSONL gold and raw predictions. All 10 locally available runs x 4 splits are present. Faithful numerators match saved run metrics; strict/coreF1 and record exact match saved scores. Reconciliation:160/160 comparisons pass at 5e-5 tolerance (needed because saved faithful rates are rounded to4 decimals). PE joint exact-with-evidence constrained rate also matches side_v1. Independent raw task-group bootstrap H2 is in metrics_recomputed.json and metrics_summary_20261124.json; it reproduces the existing H2 intervals. No local 4B44/0.6B result was included.

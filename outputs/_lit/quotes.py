"""逐篇引文核验：每条 (key, 相对路径, 原文) 必须能在 fulltext 中找到，输出真实行号。
找不到的条目以 MISSING 标出，不得进入审计报告。"""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2] / "literature" / "extracted"
L = "library/"
Q = [
    # ---- 00/01 compiler ----
    ("BeyondReAct", L + "00_base/2511.10037_BeyondReAct/2511.10037_BeyondReAct_fulltext.txt", "we pair our Planner with GPT-4o as the executor."),
    ("BeyondReAct", L + "00_base/2511.10037_BeyondReAct/2511.10037_BeyondReAct_fulltext.txt", "The Qwen3-0.6B(SFT+RL) variant is excluded due to training instability."),
    ("ATLAS", L + "01_constraint_compiler/2509.25586_ATLAS/2509.25586_ATLAS_fulltext.txt", "constraints (𝐶𝐼) are not explicitly given but stem from commonsense domain rules and physical realities"),
    ("ATLAS", L + "01_constraint_compiler/2509.25586_ATLAS/2509.25586_ATLAS_fulltext.txt", "explicitly stated or implied by 𝑄, such as budget limits"),
    ("ConstraintsOfThought", L + "01_constraint_compiler/2510.08992_ConstraintsOfThought/2510.08992_ConstraintsOfThought_fulltext.txt", "Const-o-T depends on accurate constraint extraction; when LLMs misinterpret user input or produce incomplete symbolic constraints, the search may be guided toward suboptimal solutions."),
    ("ImplicitIntelligence", L + "01_constraint_compiler/2602.20424_ImplicitIntelligence/2602.20424_ImplicitIntelligence_fulltext.txt", "the capacity to identify, reason about, and satisfy requirements users expect but never explicitly state"),
    ("ImplicitIntelligence", L + "01_constraint_compiler/2602.20424_ImplicitIntelligence/2602.20424_ImplicitIntelligence_fulltext.txt", "Evaluating 16 frontier and open-weight models across 205 scenarios"),
    ("PRefine", L + "01_constraint_compiler/2604.17886_PRefine/2604.17886_PRefine_fulltext.txt", "Human validation of the cost and party-size preferences yielded 89.7% and 97.4% agreement (Fleiss’ κ = 0.701 and 0.880; 19 annotators)"),
    ("AdaPlanBench", L + "01_constraint_compiler/2606.05622_AdaPlanBench/2606.05622_AdaPlanBench_fulltext.txt", "Our evaluation relies on LLM judges for constraint checking and rubric scoring, which may introduce model-specific preferences or systematic bias."),
    ("AdaPlanBench", L + "01_constraint_compiler/2606.05622_AdaPlanBench/2606.05622_AdaPlanBench_fulltext.txt", "AdaPlanBench is built on 307 household tasks"),
    ("CARL", L + "01_constraint_compiler/2607.04854_CARL/2607.04854_CARL_fulltext.txt", "CARL introduces a constraint-aware reward by comparing the model’s output distributions under constrained and unconstrained inputs"),
    ("PolicyGuide", L + "01_constraint_compiler/2608.19861_PolicyGuide/2608.19861_PolicyGuide_fulltext.txt", "POLICYGUIDE instead compiles each domain policy into a workflow graph and invokes a proactive verifier at user-turn boundaries."),
    ("PolicyGuide", L + "01_constraint_compiler/2608.19861_PolicyGuide/2608.19861_PolicyGuide_fulltext.txt", "domain-specific fine-tuning is often unavailable or impractical"),
    ("Sapien", L + "01_constraint_compiler/2610.00797_Sapien/2610.00797_Sapien_fulltext.txt", "an automaton-based engine that synthesizes policies from trusted user prompts and enforces them over tool calls"),
    ("NOMOS", L + "01_constraint_compiler/2610.11030_NOMOS/2610.11030_NOMOS_fulltext.txt", "NOMOS, a four-pass compiler, turns a natural-language policy into a deterministic tool-call gate"),
    ("NOMOS", L + "01_constraint_compiler/2610.11030_NOMOS/2610.11030_NOMOS_fulltext.txt", "The system also presupposes that a written policy exists"),
    ("NOMOS", L + "01_constraint_compiler/2610.11030_NOMOS/2610.11030_NOMOS_fulltext.txt", "a 26B on-premise compilation is not significantly worse than hand-written or frontier-compiled rules."),
    ("LangNCO", L + "01_constraint_compiler/2610.23190_LangNCO/2610.23190_LangNCO_fulltext.txt", "selecting its targets so that the original high-quality solution violates the new requirement."),
    ("LangNCO", L + "01_constraint_compiler/2610.23190_LangNCO/2610.23190_LangNCO_fulltext.txt", "Our evaluation focuses on constraint-type and compositional breadth rather than systematic robustness to paraphrasing."),
    ("SCA", L + "01_constraint_compiler/2610.25552_SCA/2610.25552_SCA_fulltext.txt", "they cannot detect omissions, where the agent never makes a necessary call."),
    ("CASEL", L + "01_constraint_compiler/2610.36570_CASEL/2610.36570_CASEL_fulltext.txt", "In a controlled simulation over 20 seeds"),
    ("CGAP", L + "01_constraint_compiler/2610.41040_CGAP/2610.41040_CGAP_fulltext.txt", "uses an LLM to turn the request into goals,"),
    ("CGAP", L + "01_constraint_compiler/2610.41040_CGAP/2610.41040_CGAP_fulltext.txt", "evidence spans ϵi in the user’s messages"),
    ("CGAP", L + "01_constraint_compiler/2610.41040_CGAP/2610.41040_CGAP_fulltext.txt", "Confidence intervals use 10,000 task-level bootstrap resamples, paired by task for differences between methods"),
    ("CGAP", L + "01_constraint_compiler/2610.41040_CGAP/2610.41040_CGAP_fulltext.txt", "authorization, privacy, and the decision whether an action is appropriate remain the application’s job"),
    ("CIRCE", L + "01_constraint_compiler/2610.41089_CIRCE/2610.41089_CIRCE_fulltext.txt", "It does not cover the problems where inferring constraints is part of the reasoning process."),
    ("SafeOrchestrate", L + "01_constraint_compiler/2611.09364_SafeOrchestrate/2611.09364_SafeOrchestrate_fulltext.txt", "because its tasks are largely single-rule with an empty constraint set C, the SMT layer’s cross-rule and safety-constraint enforcement is shown only on the worked example"),
    # ---- 02 objective ----
    ("ConstrainedGRPO", L + "02_objective_factorization/2602.05863_ConstrainedGRPO/2602.05863_ConstrainedGRPO_fulltext.txt", "scalarizing rewards before normalization introduces shared-denominator coupling, so that changing one multiplier alters not only the emphasis on its corresponding constraint"),
    ("ConstrainedGRPO", L + "02_objective_factorization/2602.05863_ConstrainedGRPO/2602.05863_ConstrainedGRPO_fulltext.txt", "directly optimizing a multiplicative hard-gated objective can lead to sparse learning signals and unstable optimization"),
    ("ToolRLA", L + "02_objective_factorization/2603.01620_ToolRLA/2603.01620_ToolRLA_fulltext.txt", "Ablation studies show the multiplicative reward design accounts for 7 percentage points of improvement over additive alternatives."),
    ("SEVerA", L + "02_objective_factorization/2603.25111_SEVerA/2603.25111_SEVerA_fulltext.txt", "SEVerA achieves provably zero constraint violations while outperforming state-of-the-art agents in task performance"),
    ("InteractiveCritiqueRevision", L + "02_objective_factorization/2605.08327_InteractiveCritiqueRevision/2605.08327_InteractiveCritiqueRevision_fulltext.txt", "TaxCalcBench TY24 provides synthetic U.S. federal tax-form instances with ground-truth Form 1040 outputs produced by a deterministic tax engine."),
    ("PARPO", L + "02_objective_factorization/2605.23382_PARPO/2605.23382_PARPO_fulltext.txt", "Ours significantly outperforms the strongest baseline, SkillRL, under the paired t-test (p < 0.005)"),
    ("AgentLTL", L + "02_objective_factorization/2607.02599_AgentLTL/2607.02599_AgentLTL_fulltext.txt", "a single specification drives two usages."),
    ("RLVP", L + "02_objective_factorization/2607.07435_RLVP/2607.07435_RLVP_fulltext.txt", "Therefore: penalize commission, never omission."),
    ("RLVP", L + "02_objective_factorization/2607.07435_RLVP/2607.07435_RLVP_fulltext.txt", "our penalties were manually identified based on domain rules. Automating the discovery of penalizable constraints directly from an environment’s affordances remains an open challenge."),
    ("RLVP", L + "02_objective_factorization/2607.07435_RLVP/2607.07435_RLVP_fulltext.txt", "chain 0.6B/1.7B (too weak)"),
    ("RLVP", L + "02_objective_factorization/2607.07435_RLVP/2607.07435_RLVP_fulltext.txt", "Benefit appears only past a reachability threshold"),
    ("RLVP", L + "02_objective_factorization/2607.07435_RLVP/2607.07435_RLVP_fulltext.txt", "This holds across five seeds at 4B and generalizes from 1.7B to 8B models"),
    ("RLVP", L + "02_objective_factorization/2607.07435_RLVP/2607.07435_RLVP_fulltext.txt", "folding the same rule rewards into the scalar return doubles the episodes to threshold."),
    ("STAIF", L + "02_objective_factorization/2607.22649_STAIF/2607.22649_STAIF_fulltext.txt", "Testing results in Section 6 are based on single-run."),
    ("PRISM", L + "02_objective_factorization/2607.29246_DontMixRewards/2607.29246_DontMixRewards_fulltext.txt", "do not mix rewards, mix policies."),
    ("AMRP", L + "02_objective_factorization/2609.00213_AggregationRewardHacking/2609.00213_AggregationRewardHacking_fulltext.txt", "static projection aliases qualitatively different reward profiles into a single scalar"),
    ("CC-OPD", L + "02_objective_factorization/2609.27421_CounterfactualConstraintDistill/2609.27421_CounterfactualConstraintDistill_fulltext.txt", "non-inline constraint formats such as structured fields or programmatic templates may require a different counterfactual prompt construction."),
    ("DAGent", L + "02_objective_factorization/2609.39154_DAGent/2609.39154_DAGent_fulltext.txt", "The closure is a structural proxy for contribution rather than a causal attribution"),
    ("DAGent", L + "02_objective_factorization/2609.39154_DAGent/2609.39154_DAGent_fulltext.txt", "the RL rows are means across three independent training seeds."),
    ("CM-DPO", L + "02_objective_factorization/2610.09219_CM-DPO/2610.09219_CM-DPO_fulltext.txt", "Budget violations account for the largest share of TravelPlanner errors (36.8%), suggesting that implicit arithmetic remains a bottleneck for longer plans."),
    ("CALIF", L + "02_objective_factorization/2610.19525_RewardHackingVerifiableIF/2610.19525_RewardHackingVerifiableIF_fulltext.txt", "frontier models can receive full credit for responses with little substantive answer content."),
    ("TAG", L + "02_objective_factorization/2610.21404_TAG/2610.21404_TAG_fulltext.txt", "then gates auxiliary credit on anchor satisfaction."),
    ("TAG", L + "02_objective_factorization/2610.21404_TAG/2610.21404_TAG_fulltext.txt", "Under GRPO no single weight is safe across a prompt population that contains hard prompts (small ρ)"),
    ("TAG", L + "02_objective_factorization/2610.21404_TAG/2610.21404_TAG_fulltext.txt", "low policy drift does not guarantee alignment with the unknown true reward."),
    ("TAG", L + "02_objective_factorization/2610.21404_TAG/2610.21404_TAG_fulltext.txt", "Held-out noise is about ±0.02."),
    ("ShortcutsBoundaries", L + "02_objective_factorization/2611.12865_ShortcutsBoundaries/2611.12865_ShortcutsBoundaries_fulltext.txt", "The same contextual checks supply a simple binary penalty that supports joint capability and compliance gains and partially mitigates acquired violations."),
    ("StateAlign", L + "02_objective_factorization/2611.16304_StateAlign/2611.16304_StateAlign_fulltext.txt", "StateAlign is trained on five types of constructed task states through short interactions with recorded feedback."),
    ("SOTERIA", L + "02_objective_factorization/2611.17880_SOTERIA/2611.17880_SOTERIA_fulltext.txt", "SOTERIA requires a set of formalized specifications as inputs, which are currently obtained through a semi-automated workflow that combines LLM-based auto-formalization with manual validation."),
    # ---- 03 benchmark ----
    ("RECAST", L + "03_paired_benchmark/2505.19030_RECAST/2505.19030_RECAST_fulltext.txt", "we use the Hard Constraint Satisfaction Rate (HSR) as the primary metric, quantifying the model’s ability to satisfy all specified constraints in an instruction simultaneously."),
    ("MOSAIC", L + "03_paired_benchmark/2603.03205_MOSAIC/2603.03205_MOSAIC_fulltext.txt", "MOSAIC structures inference as a plan, check, then act or refuse loop"),
    ("Firefly", L + "03_paired_benchmark/2605.17558_Firefly/2605.17558_Firefly_fulltext.txt", "tasks that passed the judge satisfy all three binary criteria 78.0% of the time, compared with 38.0% for rejected candidates"),
    ("MatchingMatters", L + "03_paired_benchmark/2606.21140_MatchingMatters/2606.21140_MatchingMatters_fulltext.txt", "The preservation gate rejects explicit changes to public task semantics but cannot formally prove natural-language equivalence."),
    ("NormWorldsCF", L + "03_paired_benchmark/2607.03957_NormWorldsCF/2607.03957_NormWorldsCF_fulltext.txt", "the Qwen3-4B GRPO study averages three independent seeds"),
    ("NormWorldsCF", L + "03_paired_benchmark/2607.03957_NormWorldsCF/2607.03957_NormWorldsCF_fulltext.txt", "Splits are by root family"),
    ("ExecutionFirst", L + "03_paired_benchmark/2607.29175_ExecutionFirst/2607.29175_ExecutionFirst_fulltext.txt", "The Basic task explicitly specifies the operational intent and required entities, the Intermediate task omits some execution details that must be inferred from context"),
    ("ExecutionFirst", L + "03_paired_benchmark/2607.29175_ExecutionFirst/2607.29175_ExecutionFirst_fulltext.txt", "This validation is performed using the same LLM used to generate the trace."),
    ("ToolLoop", L + "03_paired_benchmark/2609.09072_ToolLoop/2609.09072_ToolLoop_fulltext.txt", "the verifier achieves 94% agreement with human annotations on a random sample of 100 instances"),
    ("ANCHOR", L + "03_paired_benchmark/2610.16859_ANCHOR/2610.16859_ANCHOR_fulltext.txt", "A five-engineer audit of constraints from 50 instances reports 94% feasibility, 94% repository consistency, and 96% realism."),
    ("ANCHOR", L + "03_paired_benchmark/2610.16859_ANCHOR/2610.16859_ANCHOR_fulltext.txt", "Gwet’s AC1 ranges from 0.91 to 0.97."),
    ("AM-Bench", L + "03_paired_benchmark/2610.18090_AM-Bench/2610.18090_AM-Bench_fulltext.txt", "Each task includes a fully specified reference and six variants spanning ambiguous or missing goals, context, and constraints."),
    ("AM-Bench", L + "03_paired_benchmark/2610.18090_AM-Bench/2610.18090_AM-Bench_fulltext.txt", "KM: Relevant restrictions or authorization requirements are unstated."),
    ("AM-Bench", L + "03_paired_benchmark/2610.18090_AM-Bench/2610.18090_AM-Bench_fulltext.txt", "S checks the same fully specified task constraints across conditions, including undisclosed requirements."),
    ("AM-Bench", L + "03_paired_benchmark/2610.18090_AM-Bench/2610.18090_AM-Bench_fulltext.txt", "GPT-5.6-Sol assisted in drafting the variants using a construction skill, and the authors reviewed them."),
    ("DPG-HiddenCoop", L + "03_paired_benchmark/2610.26359_DiscoveryProbabilityGraph/2610.26359_DiscoveryProbabilityGraph_fulltext.txt", "Cooperative tasks can only be completed by two agents, a requirement that remains unknown to the agents until they attempt them."),
    ("LIFT", L + "03_paired_benchmark/2610.28819_LIFT/2610.28819_LIFT_fulltext.txt", "holding topic, outline, and constraint content fixed"),
    ("LIFT", L + "03_paired_benchmark/2610.28819_LIFT/2610.28819_LIFT_fulltext.txt", "We evaluate 17 models on the 10 released splits."),
    ("LIFT", L + "03_paired_benchmark/2610.28819_LIFT/2610.28819_LIFT_fulltext.txt", "the rewriting model occasionally treated the task’s constraints as instructions addressed to itself and complied with them"),
    ("AgentProofBench", L + "03_paired_benchmark/2610.34634_AgentProofBench/2610.34634_AgentProofBench_fulltext.txt", "connects paired tests of a frozen acceptance rule to execution from identical saved openings"),
    ("EffectWorld", L + "03_paired_benchmark/2610.35981_EffectWorld/2610.35981_EffectWorld_fulltext.txt", "template utterances (paraphrases generated by a larger language model are not yet used)"),
    ("EffectWorld", L + "03_paired_benchmark/2610.35981_EffectWorld/2610.35981_EffectWorld_fulltext.txt", "The intervals in Tables 12 and 13 measure task sampling only."),
    ("ToolTurns", L + "03_paired_benchmark/2611.14925_ToolTurns/2611.14925_ToolTurns_fulltext.txt", "blind human annotation prefers the revised message in 63.3% of 120 sampled pairs"),
    # ---- 04/05 ----
    ("TIDE", L + "04_credit_assignment/2605.03327_TIDE/2605.03327_TIDE_fulltext.txt", "a critic-free RL framework that reinterprets distribution deviation as a guiding signal rather than a rigid penalty."),
    ("GACA", L + "04_credit_assignment/2609.12424_GranularityAdaptiveCredit/2609.12424_GranularityAdaptiveCredit_fulltext.txt", "each selected checkpoint receives three stochastic evaluations, summarized by their mean and population SD."),
    ("SHARPO", L + "04_credit_assignment/2610.00838_SHARPO/2610.00838_SHARPO_fulltext.txt", "We report the mean and sample standard deviation over three independent runs."),
    ("CATS", L + "04_credit_assignment/2610.29292_ContrastiveAttributionTopology/2610.29292_ContrastiveAttributionTopology_fulltext.txt", "Attribution credits have not been validated against human judgments."),
    ("HyperAgent-SE", L + "05_review_queue/2409.16299_HyperAgent-SE/2409.16299_HyperAgent-SE_fulltext.txt", "HYPERAGENT is the first system designed to work off-the-shelf across diverse SE tasks in multiple programming languages without task-specific adaptations."),
    ("HyperAgent-Hypergraph", L + "05_review_queue/2510.10611_HyperAgent-Hypergraph/2510.10611_HyperAgent-Hypergraph_fulltext.txt", "on GSM8K, HyperAgent achieves 95.07% accuracy while reducing token consumption by 25.33%"),
    ("OrchDAG", L + "05_review_queue/2510.24663_OrchDAG/2510.24663_OrchDAG_fulltext.txt", "our method remains limited in that it does not yet address multi-turn scenarios involving implicit dependencies"),
    ("HyperAgents(DGM-H)", L + "05_review_queue/2603.19461_HyperAgentsSurvey/2603.19461_HyperAgentsSurvey_fulltext.txt", "For each experiment, we run each method 5 times. We report medians with 95% bootstrap confidence intervals computed from 1,000 resamples"),
    # ---- papers/ (relevant unique) ----
    ("AgentGym-RL", "papers/AgentGym-RL_2509.08755/AgentGym-RL_2509.08755_fulltext.txt", "We leverage Qwen-2.5-3B and Qwen-2.5-7B [83] as our primary backbone models."),
    ("ReAct", "papers/ReAct_2210.03629/ReAct_2210.03629_fulltext.txt", "ReAct outperforms imitation and reinforcement learning methods by an absolute success rate of 34% and 10% respectively"),
    ("rStar2-Agent", "papers/rStar2-Agent_2508.20722/rStar2-Agent_2508.20722_fulltext.txt", "We then run large-scale agentic reinforcement learning using GRPO-RoC, with a learning rate of 1e-6 and a batch size of 512 prompts."),
    ("ToolRL", "papers/ToolRL_2504.13958/ToolRL_2504.13958_fulltext.txt", "we sample a batch of 512, and generate 4 responses per query, training for 15 epochs in total"),
    # ---- papers/ mislabeled (title lines) ----
    ("papers/ATLAS_2605.16668 (错装)", "papers/ATLAS_2605.16668/ATLAS_2605.16668_fulltext.txt", "GraViti: Graph-Level Variational Autoencoders with Relaxed Permutation Invariance"),
    ("papers/CARL_2505.23300 (错装)", "papers/CARL_2505.23300/CARL_2505.23300_fulltext.txt", "FACTORIZATIONS FOR VARIABLE EXPONENT MUCKENHOUPT WEIGHTS"),
    ("papers/Hermes-Agents_2605.10477 (错装)", "papers/Hermes-Agents_2605.10477/Hermes-Agents_2605.10477_fulltext.txt", "Kaonic Copper and Fluorine Absolute Yields Measurement"),
    ("papers/Instructed-Use-Tools_2605.13596 (错装)", "papers/Instructed-Use-Tools_2605.13596/Instructed-Use-Tools_2605.13596_fulltext.txt", "Creativity Bias: How Machine Evaluation Struggles with Creativity in Literary Translations"),
    ("papers/LANG-NCO_2603.07613 (错装)", "papers/LANG-NCO_2603.07613/LANG-NCO_2603.07613_fulltext.txt", "Inverse Robin Spectral Problem for the p-Laplace Operator"),
    ("papers/NCP-Benchmark_2605.04826 (错装)", "papers/NCP-Benchmark_2605.04826/NCP-Benchmark_2605.04826_fulltext.txt", "Faster Algorithms for Shortest Unique or Absent Substrings"),
    ("papers/RLVP_2510.07896 (错装)", "papers/RLVP_2510.07896/RLVP_2510.07896_fulltext.txt", "ATTRIBUTION-CONTROLLED KNOWLEDGE EDIT"),
    ("papers/TAG_2508.09112 (错装)", "papers/TAG_2508.09112/TAG_2508.09112_fulltext.txt", "Tracing large-scale structure morphology with multiwavelength line intensity maps"),
    ("papers/ARMA_2502.06849 (错装)", "papers/ARMA_2502.06849/ARMA_2502.06849_fulltext.txt", "Model Fusion via Neuron Transplantation"),
    # ---- 06 supplement ----
    ("LogiSafetyBench", L + "06_web_supplement_20261121/2601.08196_LogiSafetyBench/2601.08196_LogiSafetyBench_fulltext.txt", "Safety Masking, which converts these traces into natural language instructions that omit mandatory safety steps, forcing LLMs to infer implicit constraints from context"),
    ("LogiSafetyBench", L + "06_web_supplement_20261121/2601.08196_LogiSafetyBench/2601.08196_LogiSafetyBench_fulltext.txt", "the LLM is initialized with a system prompt containing the Tool Schema (Dapi), the Raw Regulatory Document (Ptxt), and the User Instruction (I) where explicit safety requirements are removed."),
    ("LogiSafetyBench", L + "06_web_supplement_20261121/2601.08196_LogiSafetyBench/2601.08196_LogiSafetyBench_fulltext.txt", "limiting our ability to analyze the safety of specific function arguments (e.g., verifying that a transfer amount is within a safe limit"),
    ("LogiSafetyBench", L + "06_web_supplement_20261121/2601.08196_LogiSafetyBench/2601.08196_LogiSafetyBench_fulltext.txt", "the first evaluation suite designed to rigorously measure implicit regulatory compliance in LLM tool calling."),
    ("LogiSafetyBench", L + "06_web_supplement_20261121/2601.08196_LogiSafetyBench/2601.08196_LogiSafetyBench_fulltext.txt", "comprising 240 human-verified tasks"),
    ("ToolPrivacyBench", L + "06_web_supplement_20261121/2606.28061_ToolPrivacyBench/2606.28061_ToolPrivacyBench_fulltext.txt", "The benchmark contains 2,150 cases, including 1,150 fully synthetic privacy-sensitive business workflows and 1,000 cases adapted from existing multi-tool and function-calling benchmarks."),
    ("ToolPrivacyBench", L + "06_web_supplement_20261121/2606.28061_ToolPrivacyBench/2606.28061_ToolPrivacyBench_fulltext.txt", "The policy knowledge base is not supplied to the baseline agent as an execution-time defense. It is used only for post-execution audit."),
    ("ToolPrivacyBench", L + "06_web_supplement_20261121/2606.28061_ToolPrivacyBench/2606.28061_ToolPrivacyBench_fulltext.txt", "This is a sampled reliability study and does not imply that the full benchmark was independently re-annotated."),
    ("SiLR", L + "06_web_supplement_20261121/2609.04629_SiLR/2609.04629_SiLR_fulltext.txt", "With B concurrent violation branches, a count-based reward takes at most B+1 distinct values."),
    ("LowerPrivileges", L + "06_web_supplement_20261121/2606.20023_LowerPrivileges/2606.20023_LowerPrivileges_fulltext.txt", "Starting from the SFT-initialized model, we then optimize the policy with GRPO (Shao et al., 2024) in the simulated multi-turn tool-use environment."),
    ("LowerPrivileges", L + "06_web_supplement_20261121/2606.20023_LowerPrivileges/2606.20023_LowerPrivileges_fulltext.txt", "premature risk-tool use is penalized most strongly when it occurs without prior standard-tool attempts."),
    ("PlanBench-XL", L + "06_web_supplement_20261121/2606.22388_PlanBenchXL/2606.22388_PlanBenchXL_fulltext.txt", "inferring implicit subgoals"),
    ("PeakBench", L + "06_web_supplement_20261121/2608.24509_PeakBench/2608.24509_PeakBench_fulltext.txt", "execution-order perturbation recovers prerequisite and concurrency structure used by both benchmark dimensions."),
    ("LangNCO", L + "01_constraint_compiler/2610.23190_LangNCO/2610.23190_LangNCO_fulltext.txt", "do not verify semantic agreement with the natural-language requirement."),
    ("CGAP", L + "01_constraint_compiler/2610.41040_CGAP/2610.41040_CGAP_fulltext.txt", "CGAP takes these rules as application-supplied modeling inputs; automatically inducing them from natural-language descriptions is outside our scope."),
    ("RLVP", L + "02_objective_factorization/2607.07435_RLVP/2607.07435_RLVP_fulltext.txt", "to zero success on every seed) is isolated separately in the ungamability sweep"),
    ("NOMOS", L + "01_constraint_compiler/2610.11030_NOMOS/2610.11030_NOMOS_fulltext.txt", "majority vote at the (type, predicate, tool) granularity."),
]


def norm(s):
    s = s.replace("\x00", "")
    s = re.sub(r"-\n", "", s)          # 断行连字符
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def locate(text, quote, keep_hyphen=False):
    lines = text.split("\n")
    # 构造 "规范化串 -> 原行号" 映射
    buf, owners = [], []
    for i, line in enumerate(lines):
        piece = line + "\n"
        buf.append(piece)
        owners.extend([i + 1] * len(piece))
    raw = "".join(buf)
    # 逐字符规范化并保留映射
    out, idx = [], []
    j = 0
    while j < len(raw):
        c = raw[j]
        if c == "-" and j + 1 < len(raw) and raw[j + 1] == "\n":
            j += 2
            continue
        if c.isspace():
            if out and out[-1] == " ":
                j += 1
                continue
            out.append(" ")
            idx.append(owners[j])
        elif c != "\x00":
            out.append(c)
            idx.append(owners[j])
        j += 1
    hay = "".join(out)
    q = norm(quote)
    k = hay.find(q)
    if k < 0:
        k = hay.lower().find(q.lower())
    if k < 0:
        return None
    return idx[k], idx[k + len(q) - 1]


rows, missing = [], []
for key, rel, quote in Q:
    path = ROOT / rel
    text = path.read_text(encoding="utf-8", errors="replace")
    loc = locate(text, quote) or locate(text, quote, keep_hyphen=True)
    if loc is None:  # 混合情形：行尾连字符既有断词也有复合词——两边都把连字符视作空格
        t2 = text.replace(chr(13), '').replace('-', ' ')
        loc = locate(t2, quote.replace('-', ' '), keep_hyphen=False)
    words = len(quote.split())
    if loc is None:
        missing.append((key, rel, quote))
    rows.append({"key": key, "path": "literature/extracted/" + rel, "quote": quote,
                 "lines": None if loc is None else f"L{loc[0]}" + ("" if loc[0] == loc[1] else f"-{loc[1]}"),
                 "words": words})
json.dump(rows, open(pathlib.Path(__file__).with_name("quotes_verified.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("total", len(rows), "missing", len(missing), "over40", sum(r["words"] > 40 for r in rows))
for m in missing:
    print("MISSING", m)

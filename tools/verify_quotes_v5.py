"""design_v5_ccfb.md 引文核验：每条 (ID, 论文, 相对 literature/ 的路径, 原文) 必须能在全文中定位，输出真实行号。

用法：python tools/verify_quotes_v5.py   → 写 reports/design_v5_quotes.json，缺失任何一条即非零退出。
定位规则与 literature_audit_v4 相同：忽略换行与多余空白、行末断词连字符；再找不到时把连字符视作空格。
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIT = ROOT / "literature"
L = "extracted/library/"
S = "supplement_execution_semantics/"

QUOTES = [
    # ---- ① 编译器：邻近工作 ----
    ("C1", "CGAP", L + "01_constraint_compiler/2610.41040_CGAP/2610.41040_CGAP_fulltext.txt",
     "uses an LLM to turn the request into goals,"),
    ("C2", "CGAP", L + "01_constraint_compiler/2610.41040_CGAP/2610.41040_CGAP_fulltext.txt",
     "evidence spans ϵi in the user’s messages"),
    ("C3", "CGAP", L + "01_constraint_compiler/2610.41040_CGAP/2610.41040_CGAP_fulltext.txt",
     "authorization, privacy, and the decision whether an action is appropriate remain the application’s job"),
    ("C4", "CGAP", L + "01_constraint_compiler/2610.41040_CGAP/2610.41040_CGAP_fulltext.txt",
     "CGAP uses 1.3–1.6 times the plain agent’s tokens per task with gpt-oss-20b"),
    ("C5", "Sapien", L + "01_constraint_compiler/2610.00797_Sapien/2610.00797_Sapien_fulltext.txt",
     "an automaton-based engine that synthesizes policies from trusted user prompts and enforces them over tool calls"),
    ("C6", "NOMOS", L + "01_constraint_compiler/2610.11030_NOMOS/2610.11030_NOMOS_fulltext.txt",
     "a 26B on-premise compilation is not significantly worse than hand-written or frontier-compiled rules."),
    ("C7", "NOMOS", L + "01_constraint_compiler/2610.11030_NOMOS/2610.11030_NOMOS_fulltext.txt",
     "The system also presupposes that a written policy exists"),
    ("C8", "PolicyGuide", L + "01_constraint_compiler/2608.19861_PolicyGuide/2608.19861_PolicyGuide_fulltext.txt",
     "domain-specific fine-tuning is often unavailable or impractical"),
    ("C9", "ATLAS", L + "01_constraint_compiler/2509.25586_ATLAS/2509.25586_ATLAS_fulltext.txt",
     "explicitly stated or implied by 𝑄, such as budget limits"),
    ("C10", "BeyondReAct", L + "00_base/2511.10037_BeyondReAct/2511.10037_BeyondReAct_fulltext.txt",
     "we pair our Planner with GPT-4o as the executor."),
    ("C11", "LangNCO", L + "01_constraint_compiler/2610.23190_LangNCO/2610.23190_LangNCO_fulltext.txt",
     "do not verify semantic agreement with the natural-language requirement."),
    ("C12", "ConstraintsOfThought", L + "01_constraint_compiler/2510.08992_ConstraintsOfThought/2510.08992_ConstraintsOfThought_fulltext.txt",
     "Const-o-T depends on accurate constraint extraction; when LLMs misinterpret user input or produce incomplete symbolic constraints, the search may be guided toward suboptimal solutions."),
    # ---- ② 训练式信用分配：被占据 ----
    ("R1", "TAG", L + "02_objective_factorization/2610.21404_TAG/2610.21404_TAG_fulltext.txt",
     "then gates auxiliary credit on anchor satisfaction."),
    ("R2", "TAG", L + "02_objective_factorization/2610.21404_TAG/2610.21404_TAG_fulltext.txt",
     "Under GRPO no single weight is safe across a prompt population that contains hard prompts (small ρ)"),
    ("R3", "RLVP", L + "02_objective_factorization/2607.07435_RLVP/2607.07435_RLVP_fulltext.txt",
     "Therefore: penalize commission, never omission."),
    ("R4", "RLVP", L + "02_objective_factorization/2607.07435_RLVP/2607.07435_RLVP_fulltext.txt",
     "our penalties were manually identified based on domain rules. Automating the discovery of penalizable constraints directly from an environment’s affordances remains an open challenge."),
    ("R5", "RLVP", L + "02_objective_factorization/2607.07435_RLVP/2607.07435_RLVP_fulltext.txt",
     "This holds across five seeds at 4B and generalizes from 1.7B to 8B models"),
    ("R6", "ConstrainedGRPO", L + "02_objective_factorization/2602.05863_ConstrainedGRPO/2602.05863_ConstrainedGRPO_fulltext.txt",
     "scalarizing rewards before normalization introduces shared-denominator coupling, so that changing one multiplier alters not only the emphasis on its corresponding constraint"),
    ("R7", "DAGent", L + "02_objective_factorization/2609.39154_DAGent/2609.39154_DAGent_fulltext.txt",
     "The closure is a structural proxy for contribution rather than a causal attribution"),
    ("R8", "SiLR", L + "06_web_supplement_20261121/2609.04629_SiLR/2609.04629_SiLR_fulltext.txt",
     "With B concurrent violation branches, a count-based reward takes at most B+1 distinct values."),
    ("R9", "SOTERIA", L + "02_objective_factorization/2611.17880_SOTERIA/2611.17880_SOTERIA_fulltext.txt",
     "SOTERIA requires a set of formalized specifications as inputs, which are currently obtained through a semi-automated workflow that combines LLM-based auto-formalization with manual validation."),
    # ---- ② 交叉干预：相关的执行验证 / 修复 / 上限 ----
    ("X1", "LEVER", S + "LEVER/LEVER.txt",
     "we train verifiers to determine whether a program sampled from the LLMs is correct or not based on the natural language input, the program itself and its execution results."),
    ("X2", "DistilledTestSuites", S + "Distilled-test-suites/Distilled-test-suites.txt",
     "neighbor queries (Section 3.1), which are generated by modifying one aspect of the gold query."),
    ("X3", "SCA", L + "01_constraint_compiler/2610.25552_SCA/2610.25552_SCA_fulltext.txt",
     "they cannot detect omissions, where the agent never makes a necessary call."),
    ("X4", "SCA", L + "01_constraint_compiler/2610.25552_SCA/2610.25552_SCA_fulltext.txt",
     "since a false alarm makes an agent retry a valid call."),
    ("X5", "CGAP", L + "01_constraint_compiler/2610.41040_CGAP/2610.41040_CGAP_fulltext.txt",
     "Confidence intervals use 10,000 task-level bootstrap resamples, paired by task for differences between methods"),
    ("X6", "PolicyGuide", L + "01_constraint_compiler/2608.19861_PolicyGuide/2608.19861_PolicyGuide_fulltext.txt",
     "POLICYGUIDE instead compiles each domain policy into a workflow graph and invokes a proactive verifier at user-turn boundaries."),
    # ---- ③ 基准：被占据与可守差异 ----
    ("B1", "LogiSafetyBench", L + "06_web_supplement_20261121/2601.08196_LogiSafetyBench/2601.08196_LogiSafetyBench_fulltext.txt",
     "the first evaluation suite designed to rigorously measure implicit regulatory compliance in LLM tool calling."),
    ("B2", "LogiSafetyBench", L + "06_web_supplement_20261121/2601.08196_LogiSafetyBench/2601.08196_LogiSafetyBench_fulltext.txt",
     "limiting our ability to analyze the safety of specific function arguments (e.g., verifying that a transfer amount is within a safe limit"),
    ("B3", "LogiSafetyBench", L + "06_web_supplement_20261121/2601.08196_LogiSafetyBench/2601.08196_LogiSafetyBench_fulltext.txt",
     "the LLM is initialized with a system prompt containing the Tool Schema (Dapi), the Raw Regulatory Document (Ptxt), and the User Instruction (I) where explicit safety requirements are removed."),
    ("B4", "AM-Bench", L + "03_paired_benchmark/2610.18090_AM-Bench/2610.18090_AM-Bench_fulltext.txt",
     "KM: Relevant restrictions or authorization requirements are unstated."),
    ("B5", "AM-Bench", L + "03_paired_benchmark/2610.18090_AM-Bench/2610.18090_AM-Bench_fulltext.txt",
     "S checks the same fully specified task constraints across conditions, including undisclosed requirements."),
    ("B6", "ExecutionFirst", L + "03_paired_benchmark/2607.29175_ExecutionFirst/2607.29175_ExecutionFirst_fulltext.txt",
     "The Basic task explicitly specifies the operational intent and required entities, the Intermediate task omits some execution details that must be inferred from context"),
    ("B7", "LIFT", L + "03_paired_benchmark/2610.28819_LIFT/2610.28819_LIFT_fulltext.txt",
     "holding topic, outline, and constraint content fixed"),
    ("B8", "LangNCO", L + "01_constraint_compiler/2610.23190_LangNCO/2610.23190_LangNCO_fulltext.txt",
     "selecting its targets so that the original high-quality solution violates the new requirement."),
    ("B9", "ImplicitIntelligence", L + "01_constraint_compiler/2602.20424_ImplicitIntelligence/2602.20424_ImplicitIntelligence_fulltext.txt",
     "the capacity to identify, reason about, and satisfy requirements users expect but never explicitly state"),
    # ---- 结构 OOD 的范式 ----
    ("O1", "NormWorldsCF", L + "03_paired_benchmark/2607.03957_NormWorldsCF/2607.03957_NormWorldsCF_fulltext.txt",
     "OOD uses held-out structural family types (e.g., priority chains and distractor-conflict variants), not merely new roots of the same type mix."),
    ("O2", "AgentLTL", L + "02_objective_factorization/2607.02599_AgentLTL/2607.02599_AgentLTL_fulltext.txt",
     "no-coverage (no structural counterpart in training)."),
    ("O3", "EffectWorld", L + "03_paired_benchmark/2610.35981_EffectWorld/2610.35981_EffectWorld_fulltext.txt",
     "None of them shares a name, an argument or an entity type with the workspace tools, and no commerce trajectory is used in training."),
    ("O4", "EffectWorld", L + "03_paired_benchmark/2610.35981_EffectWorld/2610.35981_EffectWorld_fulltext.txt",
     "Efficiency transfers to unseen tools out of the box; effect discipline does so only partly"),
    # ---- N 近似干扰 / 误拦 ----
    ("N1", "EffectWorld", L + "03_paired_benchmark/2610.35981_EffectWorld/2610.35981_EffectWorld_fulltext.txt",
     "Positives transfer along their cue rather than their label"),
    ("N2", "ANCHOR", L + "03_paired_benchmark/2610.16859_ANCHOR/2610.16859_ANCHOR_fulltext.txt",
     "Negation or conditional logic error -- misread \"do not X\" or \"only if Y then X\" type instructions"),
    ("N3", "MOSAIC", L + "03_paired_benchmark/2603.03205_MOSAIC/2603.03205_MOSAIC_fulltext.txt",
     "over-refuse benign requests when safety is treated implicitly."),
    ("N4", "ToolRLA", L + "02_objective_factorization/2603.01620_ToolRLA/2603.01620_ToolRLA_fulltext.txt",
     "Initial DPO produced 8% over-refusal"),
    # ---- 统计与人工核验范式 ----
    ("S1", "DAGent", L + "02_objective_factorization/2609.39154_DAGent/2609.39154_DAGent_fulltext.txt",
     "the RL rows are means across three independent training seeds."),
    ("S2", "EffectWorld", L + "03_paired_benchmark/2610.35981_EffectWorld/2610.35981_EffectWorld_fulltext.txt",
     "The intervals in Tables 12 and 13 measure task sampling only."),
    ("S3", "LIFT", L + "03_paired_benchmark/2610.28819_LIFT/2610.28819_LIFT_fulltext.txt",
     "We evaluate 17 models on the 10 released splits."),
    ("S4", "ToolPrivacyBench", L + "06_web_supplement_20261121/2606.28061_ToolPrivacyBench/2606.28061_ToolPrivacyBench_fulltext.txt",
     "This is a sampled reliability study and does not imply that the full benchmark was independently re-annotated."),
    ("S5", "PRefine", L + "01_constraint_compiler/2604.17886_PRefine/2604.17886_PRefine_fulltext.txt",
     "Human validation of the cost and party-size preferences yielded 89.7% and 97.4% agreement (Fleiss’ κ = 0.701 and 0.880; 19 annotators)"),
    ("S6", "ANCHOR", L + "03_paired_benchmark/2610.16859_ANCHOR/2610.16859_ANCHOR_fulltext.txt",
     "Gwet’s AC1 ranges from 0.91 to 0.97."),
    ("S7", "STAIF", L + "02_objective_factorization/2607.22649_STAIF/2607.22649_STAIF_fulltext.txt",
     "Testing results in Section 6 are based on single-run."),
]


def _normalise(text: str, keep_hyphen: bool) -> tuple[str, list[int]]:
    lines = text.replace("\r", "").replace("\x00", "").split("\n")
    out, owner = [], []
    for no, line in enumerate(lines, 1):
        piece = line + "\n"
        joined = not keep_hyphen and line.endswith("-")
        for j, ch in enumerate(piece):
            if joined and j >= len(line) - 1:
                break  # 行末断词连字符：丢掉 "-" 与换行，与下一行直接拼接
            if ch.isspace():
                if out and out[-1] == " ":
                    continue
                out.append(" ")
            else:
                out.append(ch)
            owner.append(no)
    return "".join(out), owner


def locate(text: str, quote: str) -> tuple[int, int] | None:
    for keep in (False, True):
        hay, owner = _normalise(text, keep)
        q = re.sub(r"\s+", " ", quote).strip()
        k = hay.find(q)
        if k < 0:
            k = hay.lower().find(q.lower())
        if k >= 0:
            return owner[k], owner[k + len(q) - 1]
    hay, owner = _normalise(text.replace("-", " "), True)
    q = re.sub(r"\s+", " ", quote.replace("-", " ")).strip()
    k = hay.lower().find(q.lower())
    return (owner[k], owner[k + len(q) - 1]) if k >= 0 else None


def main() -> None:
    rows, missing = [], []
    for qid, paper, rel, quote in QUOTES:
        loc = locate((LIT / rel).read_text(encoding="utf-8", errors="replace"), quote)
        if loc is None:
            missing.append(qid)
        rows.append({"id": qid, "paper": paper, "path": "literature/" + rel, "quote": quote,
                     "words": len(quote.split()),
                     "lines": None if loc is None else (f"L{loc[0]}" if loc[0] == loc[1] else f"L{loc[0]}-{loc[1]}")})
    out = ROOT / "reports" / "design_v5_quotes.json"
    out.write_text(json.dumps(rows, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(f"total {len(rows)} missing {missing} over40 {[r['id'] for r in rows if r['words'] > 40]}")
    for r in rows:
        print(r["id"], r["paper"], r["lines"])
    if missing:
        sys.exit(1)


if __name__ == "__main__":
    main()

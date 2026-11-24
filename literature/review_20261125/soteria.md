# SOTERIA: Formally Verified Planning with Runtime Enforcement

Source: [arXiv:2611.17880](https://arxiv.org/abs/2611.17880), v1, 2026-11-13. The arXiv title, authors, date, and PDF URL were checked on 2026-11-25. The manuscript identifies itself as NeurIPS 2026; the venue record was not independently checked. Local extraction hash is recorded in `source_verification.json`.

## Main idea

SOTERIA combines hierarchical plans, static verification against tool contracts and domain-policy specifications, and a runtime monitor that blocks calls that would violate those specifications. The monitor and verified plan also provide a recovery path. Its correctness target covers call sequence, data flow, and policy conformance.

The setup starts from natural-language policy documents and tool definitions. An LLM proposes formal specifications; authors manually inspect them, add missing rules, and perform clause-by-clause coverage checks. The resulting domain specifications are reused across tasks. Thus, SOTERIA assumes a validated formal specification set at task time; its central contribution is verification and enforcement, not learning to compile each request's constraints into a standalone record.

## Experimental design

The paper evaluates 207 tasks: 50 tau-squared Airline, 114 tau-squared Retail, and 43 Toolathlon tasks, across four LLM backbones. It compares against unguarded use, NeMo Guardrails, AgentSpec, and Agent Behavioral Contracts. Reported measures include raw utility, conformance-gated task success, violation count, and per-task API cost. The headline result is zero specification violations for SOTERIA across the evaluated model/benchmark combinations, with task success and cost reported separately. The paper also ablates plan verification and sub-plans and reports multiple-run statistics in the appendix.

## Relevance and boundary

This is a strong and recent tool-agent safety baseline; it prevents any claim that programmatic constraint checking or safe plan execution is itself new. Its manually validated, domain-level specifications differ from our target of compiling request-specific natural-language constraints. That difference can motivate our research question, but does not establish novelty or semantic validity. Unlike SOTERIA, our synthetic evaluator does not execute a real agent against an external service and does not manually validate the request-level gold labels.


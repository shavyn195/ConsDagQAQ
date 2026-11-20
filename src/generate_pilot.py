"""Generate a small, deterministic, hand-authored E/I/N compiler pilot."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

from pilot_schema import validate_rows  # noqa: E402


FAMILIES: dict[str, dict[str, Any]] = {
    "budget": {
        "roles": ["search_flight", "book_flight", "search_hotel", "book_hotel", "compare_options"],
        "train_goals": [
            "Plan a two-leg business trip from Nanjing to Chengdu with a flight and hotel.",
            "Arrange a short work trip from Suzhou to Xiamen, including air travel and lodging.",
        ],
        "test_goals": [
            "Organize a client visit to Qingdao with transport and an overnight stay.",
            "Prepare a work itinerary between Hefei and Wuhan with flights and accommodation.",
        ],
        "train_explicit": [
            "Keep the combined flight and hotel cost at or below CNY {limit}.",
            "Set the maximum combined fare and room spend to CNY {limit}.",
        ],
        "test_explicit": [
            "The trip's airfare plus accommodation bill may total no more than CNY {limit}.",
            "Cap all transport and lodging charges at CNY {limit}.",
        ],
        "train_implicit": [
            "Finance rejects any itinerary whose flight and hotel charges exceed CNY {limit}.",
            "The company will reimburse this trip only up to a combined CNY {limit}.",
        ],
        "test_implicit": [
            "An itinerary above CNY {limit} cannot receive the required finance sign-off.",
            "The travel office will approve reimbursement only if the flight and hotel together stay within CNY {limit}.",
        ],
        "params": {"max_total_cost_cny": 4500},
        "description": "The combined trip cost must not exceed CNY 4,500.",
        "severity": "high",
        "scope": ["book_flight", "book_hotel"],
    },
    "deadline": {
        "roles": ["collect_data", "analyze_data", "prepare_report", "submit_report", "check_status"],
        "train_goals": [
            "Prepare and submit a short market report using the supplied sales data.",
            "Analyze the supplied delivery records and send a summary to the operations team.",
        ],
        "test_goals": [
            "Review the supplied inventory data and deliver a concise stock report.",
            "Summarize the supplied support metrics and submit the findings to the team.",
        ],
        "train_explicit": [
            "Complete and submit the report within {hours} hours.",
            "Finish the report submission in at most {hours} hours.",
        ],
        "test_explicit": [
            "The report has to reach the team before {hours} hours have elapsed.",
            "Allow no more than {hours} hours for completing and sending the report.",
        ],
        "train_implicit": [
            "The team meeting starts in {hours} hours, and the report is needed before it begins.",
            "The next handoff is in {hours} hours, so the completed report must be ready by then.",
        ],
        "test_implicit": [
            "The team will use the report at the meeting that begins in {hours} hours.",
            "A handoff scheduled {hours} hours from now depends on this report being finished beforehand.",
        ],
        "params": {"max_duration_min": 300},
        "description": "The report must be submitted within five hours.",
        "severity": "high",
        "scope": ["submit_report"],
    },
    "privacy": {
        "roles": ["read_customer_records", "local_anonymize", "aggregate_metrics", "send_report", "external_send_customer_data"],
        "train_goals": [
            "Create an aggregate retention summary from the supplied customer records.",
            "Prepare a weekly customer activity report using the supplied account data.",
        ],
        "test_goals": [
            "Produce a high-level support trend report from the supplied customer cases.",
            "Summarize account engagement patterns from the supplied customer records.",
        ],
        "train_explicit": [
            "Do not send customer PII to any external service.",
            "Keep all customer-identifying records within the local environment.",
        ],
        "test_explicit": [
            "External services must never receive customer-identifying information.",
            "Customer PII is restricted to local processing and storage.",
        ],
        "train_implicit": [
            "Customer PII is covered by the local-only policy; external services are not approved for these records.",
            "The data agreement allows local handling of identifiable customer records but forbids sending them outside.",
        ],
        "test_implicit": [
            "The privacy review permits this information to stay on the local system only.",
            "The customer-data agreement disallows disclosure to any outside service.",
        ],
        "params": {
            "protected_data_classes": ["customer_pii"],
            "forbidden_recipients": ["external"],
        },
        "description": "Customer PII must not be sent to external services.",
        "severity": "high",
        "scope": ["external_send_customer_data"],
    },
    "tool_auth": {
        "roles": ["prepare_payroll", "record_approval", "payroll_export", "email_summary"],
        "train_goals": [
            "Prepare the payroll batch and export it for the finance team.",
            "Review the monthly payroll figures and create the finance export.",
        ],
        "test_goals": [
            "Prepare the contractor payment file and deliver the payroll export.",
            "Compile the monthly wage batch and produce the finance-system export.",
        ],
        "train_explicit": [
            "Run payroll export only after an approval record exists.",
            "Wait for a recorded approval before running the payroll export.",
        ],
        "test_explicit": [
            "The payroll file may be exported only once the approval entry is present.",
            "An approval record must precede execution of the payroll export.",
        ],
        "train_implicit": [
            "Payroll exports are audited against an approval record; without one the workflow cannot proceed.",
            "The finance control blocks a payroll file unless its approval has been recorded.",
        ],
        "test_implicit": [
            "The audit trail will reject a payroll export that lacks the approval entry.",
            "Finance releases the export only after the approval checkpoint has been completed.",
        ],
        "params": {"approval_role": "record_approval", "required_role": "payroll_export"},
        "description": "Payroll export requires a recorded approval first.",
        "severity": "medium",
        "scope": ["payroll_export"],
    },
    "order": {
        "roles": ["load_data", "validate_data", "publish_report", "archive_report"],
        "train_goals": [
            "Turn the supplied sensor readings into a validated report and publish it.",
            "Prepare a quality-checked report from the supplied product data and release it.",
        ],
        "test_goals": [
            "Create a release report from the supplied inspection data and make it available.",
            "Prepare a checked operations summary from the supplied records and publish it.",
        ],
        "train_explicit": [
            "Validate the data before publishing the report.",
            "Run data validation first, then publish the report.",
        ],
        "test_explicit": [
            "Publishing is allowed only after the data has passed validation.",
            "Do the validation step ahead of releasing the report.",
        ],
        "train_implicit": [
            "The release checklist treats validated data as a prerequisite for publication.",
            "The quality procedure requires data validation to be complete before publication.",
        ],
        "test_implicit": [
            "The release gate will not open until the data-check step has finished.",
            "Quality control places the validation checkpoint ahead of making the report public.",
        ],
        "params": {"before_role": "validate_data", "after_role": "publish_report"},
        "description": "Data validation must precede report publication.",
        "severity": "medium",
        "scope": ["validate_data", "publish_report"],
    },
}


def _node(node_id: int, role: str, group_id: str, **attrs: Any) -> dict[str, Any]:
    return {"id": node_id, "tool_id": f"{group_id}_{role}", "role": role, **attrs}


def build_graph(kind: str, group_id: str) -> tuple[dict[str, Any], list[int]]:
    if kind == "budget":
        nodes = [
            _node(0, "search_flight", group_id, cost_cny=0),
            _node(1, "book_flight", group_id, cost_cny=1800),
            _node(2, "search_hotel", group_id, cost_cny=0),
            _node(3, "book_hotel", group_id, cost_cny=2100),
        ]
        edges = [{"from": 0, "to": 1}, {"from": 2, "to": 3}]
    elif kind == "deadline":
        nodes = [
            _node(0, "collect_data", group_id, duration_min=60),
            _node(1, "analyze_data", group_id, duration_min=90),
            _node(2, "prepare_report", group_id, duration_min=90),
            _node(3, "submit_report", group_id, duration_min=30),
        ]
        edges = [{"from": 0, "to": 1}, {"from": 1, "to": 2}, {"from": 2, "to": 3}]
    elif kind == "privacy":
        nodes = [
            _node(0, "read_customer_records", group_id, recipient="local", data_classes=["customer_pii"]),
            _node(1, "local_anonymize", group_id, recipient="local", data_classes=["customer_pii"]),
            _node(2, "aggregate_metrics", group_id, recipient="local", data_classes=["aggregate_metrics"]),
            _node(3, "send_report", group_id, recipient="external", data_classes=["aggregate_metrics"]),
        ]
        edges = [{"from": 0, "to": 1}, {"from": 1, "to": 2}, {"from": 2, "to": 3}]
    elif kind == "tool_auth":
        nodes = [
            _node(0, "prepare_payroll", group_id),
            _node(1, "record_approval", group_id, approval_record=True),
            _node(2, "payroll_export", group_id, requires_approval=True),
        ]
        edges = [{"from": 0, "to": 1}, {"from": 1, "to": 2}]
    elif kind == "order":
        nodes = [
            _node(0, "load_data", group_id),
            _node(1, "validate_data", group_id),
            _node(2, "publish_report", group_id),
        ]
        edges = [{"from": 0, "to": 1}, {"from": 1, "to": 2}]
    else:
        raise ValueError(f"unknown constraint type: {kind}")
    return {"nodes": nodes, "edges": edges}, [node["id"] for node in nodes]


def _constraint(kind: str, variant: str, query: str, evidence: str, family: dict[str, Any]) -> dict[str, Any]:
    description = family["description"]
    if kind == "budget":
        description = "The combined trip cost must not exceed CNY 4,500."
    if kind == "deadline":
        description = "The report must be submitted within five hours."
    if kind == "privacy":
        description = "Customer PII must not be sent to external services."
    if kind == "tool_auth":
        description = "Payroll export requires a recorded approval first."
    if kind == "order":
        description = "Data validation must precede report publication."
    if evidence not in query:
        raise ValueError(f"evidence span is not present in rendered query for {kind}/{variant}")
    return {
        "type": kind,
        "description": description,
        "evidence_span": evidence,
        "state": variant,
        "confidence": 1.0,
        "severity": family["severity"],
        "scope": [f"role:{role}" for role in family["scope"]],
        "params": family["params"],
    }


def render_rows(n_train_groups: int = 50, n_test_groups: int = 17) -> list[dict[str, Any]]:
    """Create E/I/N records with task-level split isolation."""
    rows: list[dict[str, Any]] = []
    family_names = list(FAMILIES)
    total = n_train_groups + n_test_groups
    for index in range(total):
        split = "train" if index < n_train_groups else "test"
        group_id = f"task-{index:03d}"
        kind = family_names[index % len(family_names)]
        family = FAMILIES[kind]
        goal_bank = family[f"{split}_goals"]
        goal_index = (index // len(family_names)) % len(goal_bank)
        task_goal = goal_bank[goal_index]
        graph, witness = build_graph(kind, group_id)
        role_vocab = [f"role:{role}" for role in family["roles"]]

        if kind == "budget":
            substitutions = {"limit": "4,500"}
        elif kind == "deadline":
            substitutions = {"hours": "five"}
        else:
            substitutions = {}

        for variant in ("explicit", "implicit", "none"):
            query = task_goal
            gold_constraints: list[dict[str, Any]] = []
            if variant != "none":
                phrase_bank = family[f"{split}_{variant}"]
                phrase_index = (index // len(family_names)) % len(phrase_bank)
                evidence = phrase_bank[phrase_index].format(**substitutions)
                query = f"{task_goal} {evidence}"
                gold_constraints = [_constraint(kind, variant, query, evidence, family)]
            row = {
                "sample_id": f"{group_id}-{variant[0].upper()}",
                "group_id": group_id,
                "split": split,
                "variant": variant,
                "template_id": f"{split}:{kind}:{variant}:{phrase_index}" if variant != "none" else f"{split}:{kind}:none",
                "task_goal": task_goal,
                "query": query,
                "available_roles": role_vocab,
                "compiler_input": {"query": query, "available_roles": role_vocab},
                "graph": graph,
                "witness": witness,
                "gold": {
                    "query_state": variant,
                    "abstain": False,
                    "constraints": gold_constraints,
                },
            }
            rows.append(row)
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--train-groups", type=int, default=50)
    parser.add_argument("--test-groups", type=int, default=17)
    parser.add_argument("--out", type=Path, default=ROOT / "data" / "processed")
    args = parser.parse_args()
    rows = render_rows(args.train_groups, args.test_groups)
    errors = validate_rows(rows)
    if errors:
        raise SystemExit("pilot validation failed:\n" + "\n".join(errors))
    for split in ("train", "test"):
        split_rows = [row for row in rows if row["split"] == split]
        write_jsonl(args.out / f"{split}.jsonl", split_rows)
    train_path = args.out / "train.jsonl"
    test_path = args.out / "test.jsonl"
    train_templates = {
        row["gold"]["constraints"][0]["evidence_span"]
        for row in rows if row["split"] == "train" and row["gold"]["constraints"]
    }
    test_templates = {
        row["gold"]["constraints"][0]["evidence_span"]
        for row in rows if row["split"] == "test" and row["gold"]["constraints"]
    }
    report = {
        "dataset": "synthetic_evidence_bound_compiler_pilot_v1",
        "synthetic_only": True,
        "oracle_or_human_reviewed": False,
        "groups": args.train_groups + args.test_groups,
        "records": {"train": sum(r["split"] == "train" for r in rows), "test": sum(r["split"] == "test" for r in rows)},
        "variants_per_group": ["explicit", "implicit", "none"],
        "constraint_types": sorted(FAMILIES),
        "all_witnesses_feasible": True,
        "template_overlap": sorted(train_templates & test_templates),
        "template_overlap_count": len(train_templates & test_templates),
        "pair_validation_errors": [],
        "train_sha256": hashlib.sha256(train_path.read_bytes()).hexdigest(),
        "test_sha256": hashlib.sha256(test_path.read_bytes()).hexdigest(),
        "limitations": [
            "Hand-authored controlled examples are not a naturalistic corpus.",
            "Implicit cue recoverability has not been checked by an independent oracle or human annotators.",
            "All gold confidence values are construction-time 1.0 and do not provide a calibration target.",
            "No ambiguous or abstention-required examples are included in this first pilot.",
            "Train and test constrained wording templates are disjoint; role/type/graph families remain shared.",
        ],
    }
    (args.out / "validation_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

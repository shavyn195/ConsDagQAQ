"""dataset_v4 规范层：可执行任务世界 + 最小三元组措辞模板（可信数据空间案例域）。

相对 v3 的修复（见 reports/design_v4_ccfb.md）：
- 约束必须"咬合"：任务世界里每个阶段有多个可替换工具，默认计划违反每条金标约束；
- E/I/N 为最小三元组：同一组句槽，N 版用同主题近似干扰句（豁免/否定/他人适用）替换约束句；
- I 版线索不含指令词，budget/deadline 的 d2/d3 需要算术才能恢复参数，privacy d2/d3 需要字段→数据类映射；
- held-out 工具子系统的角色名在 train/dev/tpl_ho 的任何输入中都不出现；
- severity/scope 的规则写进策略卡（随 prompt 给出），不再是模型无从得知的隐藏约定。
"""

from __future__ import annotations

import re

# ---------------------------------------------------------------- 工具表
# role: (pool, readable_name, recipient, cost_range_cny, duration_range_min, clears_pii)
TOOLS: dict[str, tuple[str, str, str, tuple[int, int], tuple[int, int], bool]] = {
    # ---- train 池 ----
    "purchase_data_asset": ("train", "the data-asset purchase", "local", (400, 1800), (20, 45), False),
    "request_data_access": ("train", "the access request", "local", (0, 0), (150, 360), False),
    "download_raw_file": ("train", "the raw-file download", "local", (0, 0), (45, 120), False),
    "mount_data_into_sandbox": ("train", "the sandbox mount", "local", (0, 0), (20, 60), False),
    "upload_data_asset": ("train", "the platform upload", "external", (20, 120), (10, 30), False),
    "execute_sandbox_job": ("train", "the sandbox job", "local", (0, 0), (120, 300), False),
    "call_external_api": ("train", "the external API call", "external", (150, 900), (20, 60), False),
    "run_production_mode": ("train", "the production run", "local", (0, 0), (60, 150), False),
    "aggregate_dataset_stats": ("train", "the stats aggregation", "local", (0, 0), (30, 90), True),
    "generate_analysis_report": ("train", "the report generation", "local", (0, 0), (30, 90), False),
    "deliver_report_to_team": ("train", "the report delivery", "external", (0, 0), (10, 40), False),
    "archive_project_files": ("train", "the archival", "local", (0, 0), (10, 40), False),
    "notify_stakeholders": ("train", "the stakeholder notification", "external", (0, 0), (5, 20), False),
    "record_finance_approval": ("train", "the finance approval", "local", (0, 0), (30, 120), False),
    "grant_resource_permission": ("train", "the permission grant", "local", (0, 0), (30, 120), False),
    "anonymize_sensitive_fields": ("train", "the anonymization", "local", (0, 0), (40, 100), True),
    "validate_workflow": ("train", "the workflow validation", "local", (0, 0), (20, 60), False),
    "cross_check_data_quality": ("train", "the quality cross-check", "local", (0, 0), (30, 90), False),
    # train 池干扰工具（只进目录，不进阶段）
    "list_data_assets": ("train", "the asset listing", "local", (0, 0), (5, 20), False),
    "check_sandbox_status": ("train", "the sandbox status check", "local", (0, 0), (5, 20), False),
    "browse_service_market": ("train", "the service-market browse", "local", (0, 0), (10, 30), False),
    "get_wallet_balance": ("train", "the balance check", "local", (0, 0), (5, 15), False),
    "view_execution_history": ("train", "the execution-history view", "local", (0, 0), (5, 20), False),
    "refund_wallet_order": ("train", "the refund", "local", (0, 0), (20, 60), False),
    # ---- held-out 池（只出现在 test_tool_ho）----
    "lease_partner_dataset": ("heldout", "the partner-dataset lease", "local", (400, 1800), (20, 45), False),
    "request_federated_access": ("heldout", "the federated access request", "local", (0, 0), (150, 360), False),
    "pull_client_snapshots": ("heldout", "the client-snapshot pull", "local", (0, 0), (45, 120), False),
    "stage_secure_enclave": ("heldout", "the enclave staging", "local", (0, 0), (20, 60), False),
    "sync_to_partner_hub": ("heldout", "the partner-hub sync", "external", (20, 120), (10, 30), False),
    "run_federated_training": ("heldout", "the federated training", "local", (0, 0), (120, 300), False),
    "rent_cloud_gpu_job": ("heldout", "the rented cloud GPU job", "external", (150, 900), (20, 60), False),
    "launch_fl_production_round": ("heldout", "the production FL round", "local", (0, 0), (60, 150), False),
    "aggregate_fl_model": ("heldout", "the model aggregation", "local", (0, 0), (30, 90), True),
    "compile_qos_report": ("heldout", "the QoS report compilation", "local", (0, 0), (30, 90), False),
    "export_audit_trail": ("heldout", "the audit-trail export", "external", (0, 0), (10, 40), False),
    "mark_compliance_checkpoint": ("heldout", "the compliance checkpoint", "local", (0, 0), (10, 40), False),
    "publish_model_card": ("heldout", "the model-card publication", "external", (0, 0), (5, 20), False),
    "sign_compute_voucher": ("heldout", "the compute-voucher signature", "local", (0, 0), (30, 120), False),
    "approve_partner_access": ("heldout", "the partner-access approval", "local", (0, 0), (30, 120), False),
    "mask_client_identifiers": ("heldout", "the identifier masking", "local", (0, 0), (40, 100), True),
    "verify_log_signature": ("heldout", "the log-signature verification", "local", (0, 0), (20, 60), False),
    "audit_model_quality": ("heldout", "the model-quality audit", "local", (0, 0), (30, 90), False),
    "query_provenance_chain": ("heldout", "the provenance query", "local", (0, 0), (5, 20), False),
    "measure_throughput": ("heldout", "the throughput measurement", "local", (0, 0), (5, 20), False),
    "check_service_availability": ("heldout", "the availability check", "local", (0, 0), (5, 20), False),
    "evaluate_fl_model": ("heldout", "the model evaluation", "local", (0, 0), (10, 30), False),
}

# 阶段：(stage, alternatives, presence_probability)；顺序即任务依赖顺序
# finish 阶段从 FINISH 中取 2 个，二者相互独立（默认顺序随机，order 约束可要求反转）
WORLDS: dict[str, dict[str, object]] = {
    "train": {
        "stages": [
            ("acquire", ["purchase_data_asset", "request_data_access", "download_raw_file"], 1.0),
            ("prepare", ["mount_data_into_sandbox", "upload_data_asset"], 0.5),
            ("process", ["execute_sandbox_job", "call_external_api", "run_production_mode"], 1.0),
            ("analyze", ["aggregate_dataset_stats"], 0.4),
            ("report", ["generate_analysis_report"], 1.0),
        ],
        "finish": ["deliver_report_to_team", "archive_project_files", "notify_stakeholders"],
        # 可插入步骤 -> 其规范插入位置（紧挨在任一目标角色之前；"@acquire" 表示紧跟获取阶段之后）
        "optional": {
            "record_finance_approval": ["purchase_data_asset"],
            "grant_resource_permission": ["call_external_api", "run_production_mode"],
            "anonymize_sensitive_fields": ["@acquire"],
            "validate_workflow": ["run_production_mode", "execute_sandbox_job"],
            "cross_check_data_quality": ["deliver_report_to_team"],
        },
        "auth_pairs": [
            ("record_finance_approval", "purchase_data_asset"),
            ("grant_resource_permission", "call_external_api"),
            ("grant_resource_permission", "run_production_mode"),
        ],
        "order_pairs": [
            ("validate_workflow", "run_production_mode"),
            ("validate_workflow", "execute_sandbox_job"),
            ("cross_check_data_quality", "deliver_report_to_team"),
            ("archive_project_files", "notify_stakeholders"),
            ("deliver_report_to_team", "notify_stakeholders"),
            ("deliver_report_to_team", "archive_project_files"),
        ],
        "distractors": [
            "list_data_assets", "check_sandbox_status", "browse_service_market",
            "get_wallet_balance", "view_execution_history", "refund_wallet_order",
        ],
    },
    "heldout": {
        "stages": [
            ("acquire", ["lease_partner_dataset", "request_federated_access", "pull_client_snapshots"], 1.0),
            ("prepare", ["stage_secure_enclave", "sync_to_partner_hub"], 0.5),
            ("process", ["run_federated_training", "rent_cloud_gpu_job", "launch_fl_production_round"], 1.0),
            ("analyze", ["aggregate_fl_model"], 0.4),
            ("report", ["compile_qos_report"], 1.0),
        ],
        "finish": ["export_audit_trail", "mark_compliance_checkpoint", "publish_model_card"],
        "optional": {
            "sign_compute_voucher": ["lease_partner_dataset"],
            "approve_partner_access": ["rent_cloud_gpu_job", "launch_fl_production_round"],
            "mask_client_identifiers": ["@acquire"],
            "verify_log_signature": ["launch_fl_production_round", "run_federated_training"],
            "audit_model_quality": ["export_audit_trail"],
        },
        "auth_pairs": [
            ("sign_compute_voucher", "lease_partner_dataset"),
            ("approve_partner_access", "rent_cloud_gpu_job"),
            ("approve_partner_access", "launch_fl_production_round"),
        ],
        "order_pairs": [
            ("verify_log_signature", "launch_fl_production_round"),
            ("verify_log_signature", "run_federated_training"),
            ("audit_model_quality", "export_audit_trail"),
            ("mark_compliance_checkpoint", "publish_model_card"),
            ("export_audit_trail", "publish_model_card"),
            ("export_audit_trail", "mark_compliance_checkpoint"),
        ],
        "distractors": [
            "query_provenance_chain", "measure_throughput", "check_service_availability",
            "evaluate_fl_model",
        ],
    },
}

HELDOUT_ROLES = sorted(r for r, spec in TOOLS.items() if spec[0] == "heldout")

# PII 数据类：可读名 + 字段别名（train 池 / test 池分开，tpl_ho 只用 test 池别名）
PII_CLASSES: dict[str, dict[str, object]] = {
    "customer_pii": {
        "name": "customer-identifying records",
        "fields": {"train": ["customer phone numbers", "customer home addresses"],
                   "test": ["customer national ID numbers"]},
    },
    "employee_pii": {
        "name": "employee-identifying records",
        "fields": {"train": ["employee salary records", "staff ID card numbers"],
                   "test": ["employee home addresses"]},
    },
    "patient_records": {
        "name": "patient records",
        "fields": {"train": ["patient diagnosis codes", "medical record numbers"],
                   "test": ["patient insurance IDs"]},
    },
}

CONSTRAINT_TYPES = ["budget", "deadline", "privacy", "tool_auth", "order"]

# 策略卡：severity 与 scope 由类型决定（C-LOOP-2 的 severity 监督链在此显式化）
DEFAULT_SEVERITY = {
    "budget": "high", "deadline": "high", "privacy": "high",
    "tool_auth": "medium", "order": "medium",
}

POLICY_CARD = (
    "Constraint types and params:\n"
    "- budget: {\"max_total_cost_cny\": int}; severity high; scope = every paid role in the catalog.\n"
    "- deadline: {\"max_duration_hours\": int}; severity high; scope = [\"role:*\"] (whole trace).\n"
    "- privacy: {\"protected_data_classes\": [class], \"forbidden_recipients\": [\"external\"]}; severity high; "
    "scope = every external role in the catalog. Classes: customer_pii (e.g. customer phone numbers, home "
    "addresses, national ID numbers), employee_pii (e.g. salary records, staff ID card numbers, employee home "
    "addresses), patient_records (e.g. diagnosis codes, medical record numbers, insurance IDs).\n"
    "- tool_auth: {\"approval_role\": role, \"required_role\": role}; severity medium; scope = [required_role].\n"
    "- order: {\"before_role\": role, \"after_role\": role}; severity medium; scope = [before_role, after_role].\n"
    "state: explicit = the user states the constraint as a directive; implicit = no directive, but the "
    "constraint follows from facts in the query (values may need arithmetic or mapping); query_state = none "
    "when nothing in the query restricts the plan (waived, negated or someone else's rules do not count).\n"
    "Roles are written with the prefix role: in scope and without it in params."
)

DATASETS = [
    "customer records", "sales ledger", "sensor telemetry", "support tickets",
    "market research panel", "HR roster", "inventory snapshot", "contract corpus",
    "partner orders", "device logs", "customer churn panel", "pricing experiments log",
    "fraud alerts archive", "supplier scorecards", "warehouse movement logs",
    "clinical trial extracts", "insurance claims feed", "loyalty program data",
    "clickstream extracts", "ad campaign metrics", "weather station feed",
    "energy meter readings", "fleet GPS traces", "help-center macros",
    "training enrollment data", "payroll adjustment files", "procurement bid sheets",
    "quality inspection records", "churn survey responses", "app crash reports",
]
TEAMS = [
    "operations team", "finance team", "compliance office", "data governance board",
    "product team", "marketing team", "risk committee", "analytics chapter",
    "supply chain desk", "clinical affairs unit", "revenue ops circle", "executive briefing group",
]

GOAL_TEMPLATES: dict[str, list[str]] = {
    "train": [
        "Compile the monthly {dataset} report and hand the deliverable to the {team}.",
        "Run the {dataset} through the analysis pipeline and deliver a summary to the {team}.",
        "Set up an analysis of the {dataset} and produce the deliverable for the {team}.",
        "Assemble a quality-checked overview of the {dataset} for the {team}.",
        "Build the reporting workflow over the {dataset} and release it to the {team}.",
        "Process the {dataset} end to end and brief the {team} on the outcome.",
        "Prepare the periodic review pack from the {dataset} for the {team}.",
        "Turn the {dataset} into a validated deliverable for the {team}.",
        "Orchestrate the analysis of the {dataset} and submit the result to the {team}.",
        "Produce the standing report on the {dataset} and share it with the {team}.",
        "Prepare the {dataset} briefing and circulate it to the {team}.",
        "Assemble the {dataset} package and stage it for the {team}.",
        "Work the {dataset} into a polished summary for the {team}.",
        "Coordinate the {dataset} analysis and route the output to the {team}.",
        "Pull the {dataset} into a reviewed deliverable for the {team}.",
        "Draft the {dataset} digest and hand it off to the {team}.",
        "Scaffold the {dataset} run and present results to the {team}.",
        "Consolidate the {dataset} and brief the {team} on the outcome.",
        "Move the {dataset} into production reporting for the {team}.",
        "Frame the {dataset} analysis and deliver the pack to the {team}.",
    ],
    "test": [
        "Put together this cycle's {dataset} summary for the {team}.",
        "Get the {dataset} analyzed and the write-up over to the {team}.",
        "Take the {dataset} from raw input to a finished hand-off for the {team}.",
        "Generate the working brief on the {dataset} and route it to the {team}.",
        "Move the {dataset} through the full pipeline and land the output with the {team}.",
        "Create this quarter's {dataset} breakdown and deliver it to the {team}.",
        "Carry the {dataset} from intake to a reviewed deliverable for the {team}.",
        "Shape the {dataset} into the standing report the {team} expects.",
        "Drive the {dataset} analysis to completion and hand the pack to the {team}.",
        "Convert the {dataset} into the scheduled digest for the {team}.",
        "Sketch out the {dataset} rollup and get it to the {team}.",
        "See the {dataset} through to a signed-off deliverable for the {team}.",
        "Fetch the {dataset}, run the numbers, and pass the pack to the {team}.",
        "Pull together the {dataset} story for the {team}.",
        "Push the {dataset} through the pipeline and drop the result with the {team}.",
        "Line up the {dataset} hand-off for the {team}.",
        "Nail down the {dataset} deliverable and send it to the {team}.",
        "Round out the {dataset} analysis for the {team}.",
        "Stitch the {dataset} into the report the {team} is waiting on.",
        "Walk the {dataset} end to end and close the loop with the {team}.",
    ],
}

# 中性背景句：三版共享，不携带任何约束语义
BACKGROUND: dict[str, list[str]] = {
    "train": [
        "The source files arrive as weekly CSV exports.",
        "This is the second run of this workflow this month.",
        "The {team} likes a one-paragraph summary at the top.",
        "Last cycle's charts were well received.",
        "The dataset owner is on the analytics chapter rota this week.",
        "Column names follow the usual warehouse naming scheme.",
    ],
    "test": [
        "Input files land in the shared drop folder every Monday.",
        "This workflow has run without incident for several cycles.",
        "The {team} prefers tables over long prose.",
        "Feedback on the previous edition was mostly about formatting.",
        "The data steward rotated to a new team last month.",
        "Field names match the catalog conventions.",
    ],
}

# ---------------------------------------------------------------- E 版（指令式直陈）
E_TEMPLATES: dict[str, dict[str, list[str]]] = {
    "budget": {
        "train": [
            "Keep the total spend on this task at or below CNY {limit}.",
            "The combined cost of all billable steps must not exceed CNY {limit}.",
            "Budget cap for the whole run: CNY {limit}.",
            "Do not let the cumulative charges pass CNY {limit}.",
            "Total spend across purchases and paid services is capped at CNY {limit}.",
            "Stay within a CNY {limit} budget for every billable step combined.",
            "Spend no more than CNY {limit} in total on this task.",
            "All payable actions together must stay under CNY {limit}.",
        ],
        "test": [
            "The all-in cost of this task may total no more than CNY {limit}.",
            "Cap the overall charges for this engagement at CNY {limit}.",
            "Nothing in this task should push total spend past CNY {limit}.",
            "The whole assignment has to fit inside CNY {limit}.",
            "Across every paid call, keep the aggregate at or under CNY {limit}.",
            "CNY {limit} is the hard ceiling for the sum of all charges here.",
            "The entire task must not cost more than CNY {limit} in total.",
            "Hold the combined price tag of this work to CNY {limit} or less.",
        ],
    },
    "deadline": {
        "train": [
            "Finish the entire task within {hours} hours.",
            "Complete all steps in at most {hours} hours.",
            "The whole run has to be done inside {hours} hours.",
            "Wrap everything up before {hours} hours have elapsed.",
            "Allow no more than {hours} hours for the full task.",
            "The full assignment must be completed within {hours} hours.",
            "Everything needs to be finished in {hours} hours or less.",
            "Set the completion limit for the whole task at {hours} hours.",
        ],
        "test": [
            "The task has to reach its final state before {hours} hours pass.",
            "Time-box the entire effort to {hours} hours.",
            "No step of this task may run beyond the {hours}-hour mark.",
            "Deliver the completed work inside a {hours}-hour window.",
            "From start to finish, this must take at most {hours} hours.",
            "The {hours}-hour limit applies to the task as a whole.",
            "Have every step finished within {hours} hours of starting.",
            "Make sure the work is done no later than {hours} hours from now.",
        ],
    },
    "privacy": {
        "train": [
            "Do not send {pii} to any external service.",
            "Keep all {pii} within the local environment.",
            "{Pii} must never leave the local system.",
            "External services must not receive {pii}.",
            "Processing of {pii} is restricted to local tools only.",
            "Keep {pii} inside the trusted environment with no outbound transfer.",
            "Apply the local-only rule to {pii} for this task.",
            "{Pii} must stay on-premise throughout the task.",
        ],
        "test": [
            "No outbound channel may carry {pii}.",
            "{Pii} are off-limits for anything that leaves the environment.",
            "Restrict {pii} to local processing and storage only.",
            "Do not push {pii} to outside services.",
            "Any external hand-off of {pii} is prohibited.",
            "Keep {pii} away from all outbound destinations.",
            "The environment boundary must stay closed for {pii}.",
            "Handle {pii} locally only and never disclose them externally.",
        ],
    },
    "tool_auth": {
        "train": [
            "Run {required} only after {approval} has completed.",
            "{Required} requires {approval} first.",
            "Wait for {approval} before executing {required}.",
            "{Approval} must precede {required}.",
            "Do not execute {required} without a completed {approval}.",
            "A completed {approval} is a precondition for {required}.",
            "Gate {required} behind {approval}.",
            "{Required} is allowed only once {approval} is on record.",
        ],
        "test": [
            "Before {required} runs, {approval} has to be finished.",
            "{Required} must stay blocked until {approval} is done.",
            "Only proceed with {required} after {approval} completes.",
            "Make sure {approval} exists before {required} executes.",
            "{Required} must not start while {approval} is still outstanding.",
            "Do {approval} first, then {required}.",
            "Executing {required} ahead of {approval} is not permitted.",
            "Ensure {approval} is complete prior to {required}.",
        ],
    },
    "order": {
        "train": [
            "Complete {before} before {after}.",
            "Run {before} first, then {after}.",
            "{Before} must precede {after}.",
            "Do {after} only after {before} is finished.",
            "The order is fixed: {before} then {after}.",
            "Finish {before} ahead of {after}.",
            "{After} may start only once {before} is done.",
            "Keep {before} ahead of {after} in the execution order.",
        ],
        "test": [
            "{Before} must come before {after}, not the other way round.",
            "Sequence the run so that {before} is completed prior to {after}.",
            "{After} has to wait until {before} has finished.",
            "Do {before} first and {after} second.",
            "Do not begin {after} until {before} is complete.",
            "{Before} needs to be finished before {after} starts.",
            "Never run {after} ahead of {before}.",
            "Order the steps with {before} in front of {after}.",
        ],
    },
}

# ---------------------------------------------------------------- I 版（事实/后果/惯例线索，无指令词）
# (hint_type, difficulty, text)。difficulty = 恢复参数所需推理步数：
#   budget/deadline: d1 数值直给；d2/d3 需要减法/加法（金标数值不出现在句中）
#   privacy: d1 数据类名直给；d2/d3 只给字段名，需要按策略卡映射到数据类
#   tool_auth/order: d1 系统规则事实；d2 事故/后果；d3 依赖链事实
# 占位符：{limit} {hours} {a} {b} {now} {end} {pii} {field} {approval} {required} {before} {after} {dataset}
I_TEMPLATES: dict[str, dict[str, list[tuple[str, int, str]]]] = {
    "budget": {
        "train": [
            ("fact", 1, "There is exactly CNY {limit} left in the project wallet, and it cannot be topped up this month."),
            ("consequence", 1, "The corporate card for this task declines anything beyond CNY {limit} in total."),
            ("fact", 2, "The project wallet holds CNY {a}, of which CNY {b} is already reserved for the license renewal."),
            ("consequence", 2, "Finance released CNY {a} for this engagement but will claw back CNY {b} of it for the audit fee."),
            ("fact", 3, "The only funding is two prepaid vouchers worth CNY {a} and CNY {b}, and the card on file is frozen."),
            ("convention", 3, "This task is paid from two cost centers that contribute CNY {a} and CNY {b}, and nothing else is chargeable."),
        ],
        "test": [
            ("fact", 1, "The engagement wallet shows a balance of CNY {limit}, and finance has frozen top-ups."),
            ("consequence", 1, "Payments on this engagement bounce once the running total goes past CNY {limit}."),
            ("fact", 2, "The cost center was funded with CNY {a}, and CNY {b} of that is earmarked for next week's renewal."),
            ("consequence", 2, "The grant pays out CNY {a} for this work, minus a CNY {b} overhead the university keeps."),
            ("fact", 3, "Two gift balances of CNY {a} and CNY {b} are the only money attached to this request."),
            ("convention", 3, "Two departments chip in CNY {a} and CNY {b} for jobs like this, and there is no other source of funds."),
        ],
    },
    "deadline": {
        "train": [
            ("fact", 1, "The {team} reviews this deliverable at a call that starts in {hours} hours."),
            ("consequence", 1, "The working environment is reclaimed {hours} hours from now, and anything unfinished is discarded."),
            ("fact", 2, "It is {now} now, and the reviewers sign off for the day at {end}."),
            ("consequence", 2, "The shared cluster goes into maintenance at {end}, and it is {now} right now."),
            ("fact", 3, "The compute lease was booked for {a} hours, and {b} of those hours are already used up."),
            ("convention", 3, "The team gets {a} hours of shared-lane time per request, and an earlier step of this request already consumed {b} of them."),
        ],
        "test": [
            ("fact", 1, "The board pre-read that includes this deliverable locks in {hours} hours."),
            ("consequence", 1, "The scheduler rolls back anything still unfinished {hours} hours from now."),
            ("fact", 2, "The clock reads {now}, and the auditors collect artifacts at {end}."),
            ("consequence", 2, "The batch window that preempts interactive jobs opens at {end}; it is currently {now}."),
            ("fact", 3, "The sandbox reservation covers {a} hours in total, and {b} hours of it have already elapsed."),
            ("convention", 3, "Requests on this lane receive a {a}-hour allotment, and the intake checks have already eaten {b} hours of it."),
        ],
    },
    "privacy": {
        "train": [
            ("fact", 1, "The {dataset} contains {pii}, and the data agreement lists no external processors."),
            ("consequence", 1, "The outbound gateway quarantines any payload that carries {pii}."),
            ("fact", 2, "Every row of the {dataset} carries {field}, and the data agreement names no external processors for such fields."),
            ("consequence", 2, "The {dataset} includes {field}; regulators treat any transfer of that kind of data outside our environment as a reportable breach."),
            ("fact", 3, "The {dataset} holds {field}, which the governance matrix places in tier 3, and tier 3 has no approved destinations outside our environment."),
            ("convention", 3, "The {dataset} still includes {field}, and the house data charter files such fields under the class it keeps on local tooling only."),
        ],
        "test": [
            ("fact", 1, "The {dataset} includes {pii}, and our processing agreement covers on-premise handling alone."),
            ("consequence", 1, "Anything carrying {pii} bounces at the egress proxy."),
            ("fact", 2, "The {dataset} has a column of {field}, and the processing agreement covers on-premise handling alone for that kind of column."),
            ("consequence", 2, "The {dataset} carries {field}; an outbound transfer of such data triggers a supervised review that freezes the project."),
            ("fact", 3, "The {dataset} lists {field}, the catalog tags that field with the strictest tier, and the strictest tier has no external destinations."),
            ("convention", 3, "The {dataset} contains {field}, and house practice routes that whole class of data through on-premise tooling alone."),
        ],
    },
    "tool_auth": {
        "train": [
            ("fact", 1, "On this account, {required} is rejected unless {approval} is already on record."),
            ("consequence", 1, "The audit gate bounces any attempt at {required} that has no {approval} behind it."),
            ("consequence", 2, "Last quarter {a_required} went through without {approval}, and the auditors reversed it."),
            ("fact", 2, "The control matrix lists {approval} as a prerequisite for {required}."),
            ("fact", 3, "The workflow engine enforces the published control sequence, and that sequence chains {approval} into {required} with no skip path."),
            ("convention", 3, "The ops runbook opens the checklist for {required} with {approval}, and reviewers escalate any plan that skips the checklist."),
        ],
        "test": [
            ("fact", 1, "The platform refuses {required} whenever {approval} is missing from the log."),
            ("consequence", 1, "Without {approval} on file, {required} dead-ends at the control gate."),
            ("consequence", 2, "The last {required_bare} attempted without {approval} was rolled back by compliance within the hour."),
            ("fact", 2, "For this task class, the sign-off sheet slots {approval} ahead of {required}."),
            ("fact", 3, "The control template that governs this lane links {required} to a completed {approval}, and the template has no override path."),
            ("convention", 3, "House practice files {approval} as the opening item for any {required_bare}, and the audit template checks for it."),
        ],
    },
    "order": {
        "train": [
            ("fact", 1, "{After} picks up its input from {before}."),
            ("consequence", 1, "{After} fails if it starts while {before} is still pending."),
            ("consequence", 2, "Last cycle {after} ran first and had to be redone once {before} finished."),
            ("fact", 2, "{After} reads the stamped output, and only {before} stamps it."),
            ("fact", 3, "The lineage for this task class shows {after} subscribing to the topic that {before} publishes, and that topic has no other publisher."),
            ("convention", 3, "The delivery template lists {before} as the entry that unblocks {after}, and the template is checked at review."),
        ],
        "test": [
            ("fact", 1, "{After} takes its input straight from what {before} produces."),
            ("consequence", 1, "Starting {after} before {before} finishes just throws an error."),
            ("consequence", 2, "The previous run did {after} early and lost a day redoing it after {before}."),
            ("fact", 2, "The only source of the manifest that {after} needs is {before}."),
            ("fact", 3, "The lineage graph places {after} downstream of {before}, and no alternate producer is registered for its input."),
            ("convention", 3, "The review checklist for this lane expects {before} to gate {after}, and reviewers return plans that invert it."),
        ],
    },
}

# ---------------------------------------------------------------- N 版近似干扰句（同主题、无约束力）
NEAR_MISS: dict[str, dict[str, list[str]]] = {
    "budget": {
        "train": [
            "There is no spending cap on this task; finance will cover whatever it costs.",
            "The CNY {limit} ceiling from the pilot phase was lifted last week.",
            "Another team works under a CNY {limit} cap, but that cap does not cover this task.",
            "Cost is not a factor here, even if the bill goes well past CNY {limit}.",
        ],
        "test": [
            "Spending is unrestricted for this engagement.",
            "An old CNY {limit} limit was withdrawn when the budget was renewed.",
            "The CNY {limit} allowance belongs to a separate project and does not apply here.",
            "Finance confirmed the bill can exceed CNY {limit} if needed.",
        ],
    },
    "deadline": {
        "train": [
            "There is no fixed deadline; the {team} will pick it up whenever it lands.",
            "The {hours}-hour turnaround applies to a different queue, not to this task.",
            "An earlier draft mentioned a {hours}-hour window, but that has since been dropped.",
            "Take as long as the work needs; even well over {hours} hours is fine.",
        ],
        "test": [
            "Timing is flexible on this one.",
            "The {hours}-hour target was retired after the last planning review.",
            "A {hours}-hour window exists for the other lane only.",
            "Nobody is waiting on this, so running past {hours} hours is acceptable.",
        ],
    },
    "privacy": {
        "train": [
            "Sharing the outputs with outside services is fine; the data agreement covers external processing.",
            "The local-only rule for {pii} applies to the archive team, not to this task.",
            "External processing of {pii} was approved for this engagement last week.",
            "Outside services may receive the data here, {pii} included.",
        ],
        "test": [
            "External tools are cleared to handle every field in this engagement.",
            "A local-only rule for {pii} exists on another project but not on this one.",
            "Legal signed off on sending {pii} to approved outside processors for this work.",
            "Outbound transfers are permitted for this job, {pii} included.",
        ],
    },
    "tool_auth": {
        "train": [
            "{Required} does not need {approval} on this account.",
            "{Approval} used to be required before {required}, but that rule was retired.",
            "On the other team's account {required} waits for {approval}; ours has no such gate.",
            "{Required} can go ahead without {approval} this time.",
        ],
        "test": [
            "No sign-off is attached to {required} here.",
            "The old rule tying {required} to {approval} was removed this quarter.",
            "Only the partner account gates {required} behind {approval}.",
            "{Approval} is optional for {required} in this workspace.",
        ],
    },
    "order": {
        "train": [
            "{Before} and {after} can run in either order.",
            "Whether {before} or {after} goes first makes no difference here.",
            "There is no dependency between {before} and {after}.",
            "{After} does not rely on anything from {before}.",
        ],
        "test": [
            "The sequence of {before} and {after} is up to you.",
            "{Before} and {after} are fully independent of each other.",
            "Either {before} or {after} may come first.",
            "Nothing ties {after} to {before}.",
        ],
    },
}

# I 版禁用的指令性词汇（verify_dataset_v4 与单测共用；按词边界匹配）
DIRECTIVE_LEXICON = [
    "must", "do not", "don't", "never", "only after", "only once", "no more than", "at most",
    "at or below", "keep", "stay", "cap", "capped", "ceiling", "limit", "required to",
    "has to", "have to", "need to", "needs to", "should", "ensure", "make sure", "not permitted",
    "prohibited", "forbidden", "allowed only",
]
_DIRECTIVE_RE = re.compile(r"\b(?:" + "|".join(re.escape(w) for w in DIRECTIVE_LEXICON) + r")\b", re.IGNORECASE)


def directive_hits(text: str) -> list[str]:
    """返回句中出现的指令词（占位符不计）。"""
    return _DIRECTIVE_RE.findall(re.sub(r"\{[^}]*\}", "X", text))


def tool_name(role: str) -> str:
    return TOOLS[role][1]


def bare_name(role: str) -> str:
    """去冠词的可读名（用于 "a {required_bare}" 句式）。"""
    name = tool_name(role)
    return name[4:] if name.startswith("the ") else name


def with_article(role: str) -> str:
    bare = bare_name(role)
    return ("an " if bare[0] in "aeiouAEIOU" else "a ") + bare


def fill_template(text: str, mapping: dict[str, str]) -> str:
    """占位符填充；{Pii}/{Approval} 等首字母大写变体由本函数统一处理。"""
    out = text
    for key, value in mapping.items():
        out = out.replace("{" + key[0].upper() + key[1:] + "}", value[0].upper() + value[1:])
        out = out.replace("{" + key + "}", value)
    return out

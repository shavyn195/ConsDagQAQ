"""dataset_v2 角色词表与措辞模板池（可信数据空间背景，S1+S4 规范层）。

词表来源：docs/rules 可信数据空间规则（权限/沙箱/数据资产/钱包/QoS/联邦学习）。
- 角色带类别标签（observe/mutate/verify/terminal），派生两阶段 scope 的编译期锚。
- HELDOUT 子系统的角色仅出现在测试 tool-ho 子集的 DAG 中（S7 加严：2-子集检查）。
- 模板池 A（explicit）与 B（implicit 线索）按 split 严格分池；implicit 线索三类型
  （consequence/fact/convention）× 难度 1-3，红线：线索只指向金标约束。
"""

from __future__ import annotations

# ---------------------------------------------------------------- 角色词表
# role: (subsystem, category, readable_name)
ROLES: dict[str, tuple[str, str, str]] = {
    # 数据资产目录子系统
    "list_data_assets": ("catalog", "observe", "the data-asset listing"),
    "search_data_catalog": ("catalog", "observe", "the catalog search"),
    "read_asset_metadata": ("catalog", "observe", "the metadata read"),
    "preview_asset_sample": ("catalog", "observe", "the sample preview"),
    "purchase_data_asset": ("catalog", "mutate", "the data-asset purchase"),
    "download_raw_file": ("catalog", "mutate", "the raw-file download"),
    "upload_data_asset": ("catalog", "mutate", "the asset upload"),
    # 权限子系统
    "check_resource_permission": ("permission", "verify", "the permission check"),
    "request_data_access": ("permission", "mutate", "the access request"),
    "grant_resource_permission": ("permission", "mutate", "the permission grant"),
    "record_finance_approval": ("permission", "mutate", "the finance approval entry"),
    "review_access_request": ("permission", "observe", "the access-request review"),
    "revoke_resource_permission": ("permission", "mutate", "the permission revocation"),
    "export_permission_audit": ("permission", "verify", "the permission audit export"),
    # 工作流子系统
    "open_workflow_canvas": ("workflow", "observe", "the canvas view"),
    "edit_workflow_dag": ("workflow", "mutate", "the workflow edit"),
    "validate_workflow": ("workflow", "verify", "the workflow validation"),
    "run_debug_mode": ("workflow", "mutate", "the debug run"),
    "run_test_mode": ("workflow", "mutate", "the test run"),
    "run_production_mode": ("workflow", "terminal", "the production run"),
    "view_execution_history": ("workflow", "observe", "the execution-history view"),
    # 沙箱子系统
    "create_sandbox": ("sandbox", "mutate", "the sandbox creation"),
    "mount_data_into_sandbox": ("sandbox", "mutate", "the data mount"),
    "execute_sandbox_job": ("sandbox", "mutate", "the sandbox job"),
    "stream_sandbox_logs": ("sandbox", "observe", "the log stream"),
    "collect_sandbox_artifacts": ("sandbox", "mutate", "the artifact collection"),
    "teardown_sandbox": ("sandbox", "mutate", "the sandbox teardown"),
    "check_sandbox_status": ("sandbox", "verify", "the sandbox status check"),
    # 服务组合子系统
    "browse_service_market": ("service", "observe", "the service-market browse"),
    "test_service_endpoint": ("service", "verify", "the endpoint test"),
    "add_service_to_workflow": ("service", "mutate", "the service addition"),
    "compose_service_workflow": ("service", "mutate", "the workflow composition"),
    "call_external_api": ("service", "mutate", "the external API call"),
    "register_new_service": ("service", "mutate", "the service registration"),
    "compare_service_versions": ("service", "observe", "the version comparison"),
    # 钱包子系统
    "get_wallet_balance": ("wallet", "observe", "the balance check"),
    "create_purchase_order": ("wallet", "mutate", "the purchase order"),
    "pay_with_wallet": ("wallet", "mutate", "the wallet payment"),
    "list_wallet_transactions": ("wallet", "observe", "the transaction listing"),
    "apply_recharge_package": ("wallet", "mutate", "the recharge"),
    "refund_wallet_order": ("wallet", "mutate", "the refund"),
    "reconcile_finance_records": ("wallet", "verify", "the finance reconciliation"),
    # 分析产出子系统
    "aggregate_dataset_stats": ("report", "mutate", "the stats aggregation"),
    "generate_analysis_report": ("report", "mutate", "the report generation"),
    "anonymize_sensitive_fields": ("report", "mutate", "the anonymization"),
    "cross_check_data_quality": ("report", "verify", "the quality cross-check"),
    "deliver_report_to_team": ("report", "terminal", "the report delivery"),
    "archive_project_files": ("report", "mutate", "the archival"),
    "notify_stakeholders": ("report", "mutate", "the stakeholder notification"),
    # ---- held-out 专属子系统（仅 test-tool-ho 的 DAG 使用）----
    "query_provenance_chain": ("trace", "observe", "the provenance query"),
    "verify_log_signature": ("trace", "verify", "the signature verification"),
    "export_audit_trail": ("trace", "mutate", "the audit-trail export"),
    "mark_compliance_checkpoint": ("trace", "verify", "the compliance checkpoint"),
    "measure_response_time": ("qos", "verify", "the response-time measurement"),
    "measure_throughput": ("qos", "verify", "the throughput measurement"),
    "check_service_availability": ("qos", "verify", "the availability check"),
    "compile_qos_report": ("qos", "terminal", "the QoS report compilation"),
    "create_fl_round": ("fl", "mutate", "the FL round creation"),
    "collect_client_updates": ("fl", "mutate", "the update collection"),
    "aggregate_fl_model": ("fl", "mutate", "the model aggregation"),
    "evaluate_fl_model": ("fl", "terminal", "the model evaluation"),
}

HELDOUT_SUBSYSTEMS = {"trace", "qos", "fl"}
TRAIN_ROLE_POOL = sorted(r for r, (s, _, _) in ROLES.items() if s not in HELDOUT_SUBSYSTEMS)
HELDOUT_ROLE_POOL = sorted(r for r, (s, _, _) in ROLES.items() if s in HELDOUT_SUBSYSTEMS)
ALL_ROLE_POOL = sorted(ROLES)

# 付费角色：cost_cny 采样范围（wallet/service/fl 规则：余额扣款、数据购买、外部 API 计费、FL 算力配额）
PAID_ROLES: dict[str, tuple[int, int]] = {
    "purchase_data_asset": (600, 2800),
    "create_purchase_order": (0, 0),
    "pay_with_wallet": (150, 1600),
    "call_external_api": (20, 180),
    "register_new_service": (0, 60),
    "upload_data_asset": (0, 40),
    "create_fl_round": (100, 800),
}

# 外发候选角色（recipient=external；privacy 约束的管辖对象，含 held-out 的审计导出）
EXTERNAL_ROLES = ["call_external_api", "notify_stakeholders", "deliver_report_to_team", "export_audit_trail"]

# PII 载体角色：处理原始可识别数据（data_classes 含 pii 类）
PII_CARRIER_ROLES = [
    "preview_asset_sample", "download_raw_file", "mount_data_into_sandbox",
    "execute_sandbox_job", "anonymize_sensitive_fields",
]

# PII 数据类变体（privacy 约束参数与措辞共用）
PII_CLASSES: dict[str, str] = {
    "customer_pii": "customer-identifying records",
    "employee_pii": "employee-identifying records",
    "patient_records": "patient records",
}

# 授权惯例对（tool_auth）：approval 角色须先于 required 角色（witness 拓扑序保证）
AUTH_PAIRS: list[tuple[str, str]] = [
    ("record_finance_approval", "pay_with_wallet"),
    ("record_finance_approval", "create_purchase_order"),
    ("grant_resource_permission", "run_production_mode"),
]

# 先后依赖对（order）：before 须先于 after
ORDER_PAIRS: list[tuple[str, str]] = [
    ("validate_workflow", "run_production_mode"),
    ("cross_check_data_quality", "deliver_report_to_team"),
    ("collect_sandbox_artifacts", "archive_project_files"),
    ("anonymize_sensitive_fields", "aggregate_dataset_stats"),
    ("aggregate_dataset_stats", "generate_analysis_report"),
    ("generate_analysis_report", "deliver_report_to_team"),
    ("compose_service_workflow", "validate_workflow"),
    ("create_sandbox", "mount_data_into_sandbox"),
    ("mount_data_into_sandbox", "execute_sandbox_job"),
    ("query_provenance_chain", "export_audit_trail"),
    ("collect_client_updates", "aggregate_fl_model"),
]

# 约束五类默认 severity（手册 2.2；C-LOOP-2：severity 在③构造期给定）
DEFAULT_SEVERITY = {
    "budget": "high", "deadline": "high", "privacy": "high",
    "tool_auth": "medium", "order": "medium",
}

DATASETS = [
    "customer records", "sales ledger", "sensor telemetry", "support tickets",
    "market research panel", "HR roster", "inventory snapshot", "contract corpus",
    "partner orders", "device logs",
]
TEAMS = [
    "operations team", "finance team", "compliance office",
    "data governance board", "product team", "marketing team",
]

# ---------------------------------------------------------------- 任务 goal 模板
GOAL_TEMPLATES: dict[str, list[str]] = {
    "train": [
        "Compile the monthly {dataset} report and hand the deliverable to the {team}.",
        "Run the {dataset} through the analysis pipeline and deliver a summary to the {team}.",
        "Set up a sandboxed analysis of the {dataset} and produce the deliverable for the {team}.",
        "Assemble a quality-checked overview of the {dataset} for the {team}.",
        "Build the reporting workflow over the {dataset} and release it to the {team}.",
        "Process the {dataset} end to end and brief the {team} on the outcome.",
        "Prepare the periodic review pack from the {dataset} for the {team}.",
        "Turn the {dataset} into a validated deliverable for the {team}.",
        "Orchestrate the analysis of the {dataset} and submit the result to the {team}.",
        "Produce the standing report on the {dataset} and share it with the {team}.",
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
    ],
}

# ---------------------------------------------------------------- E 版模板（池 A）
# 每类每 split 8 条；占位符 {limit}/{hours}/{pii}/{approval}/{required}/{before}/{after}
E_TEMPLATES: dict[str, dict[str, list[str]]] = {
    "budget": {
        "train": [
            "Keep the total wallet spend on this task at or below CNY {limit}.",
            "The combined cost of all billable steps must not exceed CNY {limit}.",
            "Budget cap for the whole run: CNY {limit}.",
            "Do not let the cumulative charges pass CNY {limit}.",
            "Total spend across purchases and paid services is capped at CNY {limit}.",
            "Stay within a CNY {limit} budget for every billable step combined.",
            "The finance plan for this task allows at most CNY {limit} in total charges.",
            "All payable actions together must stay under CNY {limit}.",
        ],
        "test": [
            "The all-in cost of this task may total no more than CNY {limit}.",
            "Cap the overall charges for this engagement at CNY {limit}.",
            "Nothing in this task should push total spend past CNY {limit}.",
            "The whole assignment has to fit inside CNY {limit}.",
            "Across every paid call, keep the aggregate at or under CNY {limit}.",
            "CNY {limit} is the hard ceiling for the sum of all charges here.",
            "Payment-wise, the entire task must not cost more than CNY {limit} in total.",
            "Hold the combined price tag of this work to CNY {limit} or less.",
        ],
    },
    "deadline": {
        "train": [
            "Finish the entire task within {hours} hours.",
            "Complete all steps in at most {hours} hours.",
            "The whole run has to be done inside {hours} hours.",
            "Wrap everything up before {hours} hours have elapsed.",
            "Allow no more than {hours} hours for completing the full task.",
            "The full assignment must reach completion within {hours} hours.",
            "Everything needs to be finished in {hours} hours or less.",
            "Set the completion boundary for the whole task at {hours} hours.",
        ],
        "test": [
            "The task has to reach its final state before {hours} hours pass.",
            "Time-box the entire effort to {hours} hours.",
            "No step of this task may run beyond the {hours}-hour mark.",
            "The clock on this assignment runs out after {hours} hours.",
            "Deliver the completed work inside a {hours}-hour window.",
            "From start to finish, this must take at most {hours} hours.",
            "The {hours}-hour limit applies to the task as a whole.",
            "Have every step finished within {hours} hours of starting.",
        ],
    },
    "privacy": {
        "train": [
            "Do not send {pii} to any external service.",
            "Keep all {pii} within the local environment.",
            "{Pii} must never leave the local system.",
            "External services must not receive {pii}.",
            "Processing of {pii} is restricted to local tools only.",
            "Keep {pii} inside the trusted environment; no outbound transfer.",
            "The local-only policy applies to {pii} for this task.",
            "{Pii} stays on-premise throughout the entire task.",
        ],
        "test": [
            "No outbound channel may carry {pii}.",
            "{Pii} is off-limits for anything that leaves the environment.",
            "Restrict {pii} to local processing and storage only.",
            "It is forbidden to push {pii} to outside services.",
            "Any external hand-off of {pii} is prohibited.",
            "Keep {pii} away from all outbound destinations.",
            "The environment boundary is closed for {pii}.",
            "Local handling only — {pii} must not be disclosed externally.",
        ],
    },
    "tool_auth": {
        "train": [
            "Run {required} only after {approval} has completed.",
            "{Required} requires a recorded {approval} first.",
            "Wait for {approval} before executing {required}.",
            "{Approval} must precede {required}.",
            "Do not execute {required} without a completed {approval}.",
            "A completed {approval} is a precondition for {required}.",
            "Gate {required} behind {approval}.",
            "{Required} is allowed only once {approval} is on record.",
        ],
        "test": [
            "Before {required} runs, {approval} has to be finished.",
            "{Required} is blocked until {approval} is done.",
            "Only proceed with {required} after {approval} completes.",
            "The {approval} entry must exist before {required} executes.",
            "{Required} cannot start while {approval} is still outstanding.",
            "Sequence matters: {approval} first, then {required}.",
            "Executing {required} ahead of {approval} is not permitted.",
            "Make sure {approval} is complete prior to {required}.",
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
            "{Before} comes before {after}, not the other way round.",
            "Sequence the run so that {before} is completed prior to {after}.",
            "{After} waits until {before} has finished.",
            "First {before}, then {after} — in that order.",
            "Do not begin {after} until {before} is complete.",
            "{Before} needs to be finished before {after} starts.",
            "The dependency runs {before} into {after}, never reversed.",
            "Order the steps with {before} in front of {after}.",
        ],
    },
}

# ---------------------------------------------------------------- I 版模板（池 B）
# (hint_type, difficulty, text)；hint_type ∈ consequence/fact/convention；difficulty 1-3
# 红线：线索只指向金标约束语义，不得引入金标外新约束（S6 oracle 复查兜底）
I_TEMPLATES: dict[str, dict[str, list[tuple[str, int, str]]]] = {
    "budget": {
        "train": [
            ("consequence", 1, "Anything that pushes the total charges past CNY {limit} gets flagged by the finance monitor and blocked."),
            ("consequence", 2, "The corporate card on file tops out at CNY {limit} for this category; anything beyond that declines automatically."),
            ("consequence", 3, "Procurement's sign-off threshold for this task class sits at CNY {limit}, and the director who grants exceptions is on leave all week."),
            ("fact", 1, "The wallet was topped up with exactly CNY {limit} for this task."),
            ("fact", 2, "Finance set aside CNY {limit} for this engagement; the ledger entry is already booked against it."),
            ("fact", 3, "The engagement letter caps reimbursable spend at CNY {limit}, and the accounting system rejects overages without a variance memo we cannot obtain in time."),
            ("convention", 1, "Team policy for vendor-facing tasks: the all-in cost ceiling is CNY {limit}."),
            ("convention", 2, "By convention, engagements of this class run under a CNY {limit} all-in ceiling."),
            ("convention", 3, "The standing procurement rule for this task tier holds total charges to CNY {limit}; waivers need a board vote that convenes next month."),
        ],
        "test": [
            ("consequence", 1, "The spend guardrail on this engagement rejects any total above CNY {limit}."),
            ("consequence", 2, "Our department card hard-stops at CNY {limit} per engagement of this type."),
            ("consequence", 3, "Budget control auto-escalates anything over CNY {limit} to the audit committee, which is in a reporting freeze until further notice."),
            ("fact", 1, "There is precisely CNY {limit} left in the project wallet."),
            ("fact", 2, "The cost center for this task carries a CNY {limit} balance, and finance already matched it to this work order."),
            ("fact", 3, "The grant funding this task releases only CNY {limit} per engagement, and the program officer is unreachable for amendments this quarter."),
            ("convention", 1, "House rule here: CNY {limit} is the ceiling for the whole job."),
            ("convention", 2, "This task class is customarily run inside a CNY {limit} envelope."),
            ("convention", 3, "Per the finance playbook, work like this is budgeted to CNY {limit}, and any excess needs the year-end review cycle to clear."),
        ],
    },
    "deadline": {
        "train": [
            ("consequence", 1, "The platform reclaims the working environment {hours} hours from now and kills anything still running."),
            ("consequence", 2, "The sandbox cluster is drained for overnight maintenance {hours} hours from now, and unfinished jobs are discarded."),
            ("consequence", 3, "The vendor license slot expires in {hours} hours, renewal quotes take a week, and the fallback slot is already booked by another team."),
            ("fact", 1, "The deadline for this deliverable is {hours} hours away."),
            ("fact", 2, "The steering committee convenes in {hours} hours and expects this delivered at the table."),
            ("fact", 3, "The client's review call is in {hours} hours; their procurement only countersigns deliverables presented on that call, and the next slot opens next month."),
            ("convention", 1, "Standard turnaround for this task class is {hours} hours."),
            ("convention", 2, "Ops convention: anything touching the shared lane must complete inside {hours} hours."),
            ("convention", 3, "The runbook allows {hours} hours for work of this type; overruns trigger the incident-review lane, which is backed up behind the audit."),
        ],
        "test": [
            ("consequence", 1, "Anything still unfinished after {hours} hours gets rolled back by the scheduler."),
            ("consequence", 2, "The batch window opens in {hours} hours and the platform preempts interactive jobs to make room."),
            ("consequence", 3, "The partner sandbox lease runs out in {hours} hours, extension approvals sit in a queue with a multi-day SLA, and the data mount cannot be recreated elsewhere."),
            ("fact", 1, "You have {hours} hours on the clock for this assignment."),
            ("fact", 2, "The board pre-read is locked in {hours} hours, and this deliverable is on the pre-read list."),
            ("fact", 3, "The audit fieldwork starts in {hours} hours; auditors only accept artifacts staged before fieldwork, and restaging after their arrival is out of scope."),
            ("convention", 1, "Delivery norm for this kind of request: {hours} hours."),
            ("convention", 2, "Around here, jobs on this lane are expected back within {hours} hours."),
            ("convention", 3, "The escalation policy gives {hours} hours for tasks like this before they are pulled into the steering queue, which meets weekly."),
        ],
    },
    "privacy": {
        "train": [
            ("consequence", 1, "The compliance scanner rejects any outbound artifact that carries {pii}."),
            ("consequence", 2, "The DLP gateway sits in front of every outbound channel and quarantines transfers containing {pii}."),
            ("consequence", 3, "The regulator's new guidance treats outbound {pii} as a reportable breach, and the disclosure process freezes the whole project while it runs."),
            ("fact", 1, "{Pii} are classified local-only under the data-governance policy."),
            ("fact", 2, "The data agreement for this engagement allows local handling of {pii} but lists no approved external recipients."),
            ("fact", 3, "The source system tags {pii} with the highest handling tier, and the tier table maps that level to on-premise processing with no external recipients."),
            ("convention", 1, "Company policy keeps {pii} local-only."),
            ("convention", 2, "In this office, {pii} never travel through outside services."),
            ("convention", 3, "The standing data-handling charter routes {pii} through on-premise tooling only; external routing needs a data-processing addendum that legal has not signed for this vendor."),
        ],
        "test": [
            ("consequence", 1, "Any outbound payload with {pii} in it bounces at the gateway."),
            ("consequence", 2, "Outbound channels are wired through the DLP proxy, and it quarantines anything containing {pii}."),
            ("consequence", 3, "Under the new consent decree, an outbound {pii} transfer triggers a 30-day supervised review that this engagement's timeline cannot absorb."),
            ("fact", 1, "The handling rules pin {pii} to the local environment."),
            ("fact", 2, "This engagement's data schedule permits {pii} on-premise only and names no external processors."),
            ("fact", 3, "The {pii} carry the strictest classification in the catalog, and the classification matrix allows no external destination at that level."),
            ("convention", 1, "Local-only is the rule for {pii} here."),
            ("convention", 2, "House practice keeps {pii} off any outside service."),
            ("convention", 3, "The data charter confines {pii} to on-premise tooling; any external hop requires a signed addendum that is still with legal."),
        ],
    },
    "tool_auth": {
        "train": [
            ("consequence", 1, "{Required} attempts without a recorded {approval} get bounced by the audit gate."),
            ("consequence", 2, "The control workflow monitors {required} and rolls it back if the {approval} entry is missing."),
            ("consequence", 3, "After last quarter's incident, the audit gate hard-stops {required} whenever the {approval} record is absent, and the override switch needs two officers who are both off-site."),
            ("fact", 1, "The audit trail requires a {approval} record before {required} can run."),
            ("fact", 2, "The control matrix lists {approval} as a prerequisite for {required}."),
            ("fact", 3, "The compliance checklist published for this task class starts with the {approval} entry, and the workflow engine enforces checklist order on {required}."),
            ("convention", 1, "Standard practice here: {approval} first, then {required}."),
            ("convention", 2, "Team convention treats {approval} as the green light for {required}."),
            ("convention", 3, "The ops runbook puts {approval} at the head of the checklist for anything ending in {required}, and deviations are escalated by default."),
        ],
        "test": [
            ("consequence", 1, "Skip {approval} and the platform will refuse {required}."),
            ("consequence", 2, "The approval ledger is wired into {required}; without its {approval} entry the step dead-ends."),
            ("consequence", 3, "The hardening review last month made the {approval} record a blocking precondition for {required}, and the break-glass path requires a change ticket that takes days."),
            ("fact", 1, "The process log only clears {required} once {approval} is on record."),
            ("fact", 2, "For this task class, the sign-off sheet slots {approval} ahead of {required}."),
            ("fact", 3, "The workflow engine runs the published control sequence, which chains {approval} into {required} with no skip path enabled."),
            ("convention", 1, "As always around here, {approval} comes before {required}."),
            ("convention", 2, "Local custom: no {required} until {approval} is logged."),
            ("convention", 3, "The team's standing checklist routes {required} through {approval}, and the checklist is enforced by the audit template."),
        ],
    },
    "order": {
        "train": [
            ("consequence", 1, "{After} fails if it starts while {before} is still pending."),
            ("consequence", 2, "The scheduler cancels {after} whenever the {before} output is missing from the hand-off shelf."),
            ("consequence", 3, "The pipeline watchdog enforces the published dependency chain, which chains {before} into {after}, and manual reordering is disabled on this lane."),
            ("fact", 1, "The hand-off package that {after} consumes is produced by {before}."),
            ("fact", 2, "{After} reads the stamped output, and only {before} stamps it."),
            ("fact", 3, "The data lineage for this task class shows {after} subscribing to the {before} topic, and the broker has no other publisher for that stream."),
            ("convention", 1, "The runbook always puts {before} ahead of {after}."),
            ("convention", 2, "Team habit: {before} clears the way for {after}."),
            ("convention", 3, "The delivery template for this task tier lists {before} as the entry that unblocks {after}, and the template is checked at review."),
        ],
        "test": [
            ("consequence", 1, "Starting {after} before {before} finishes just throws an error."),
            ("consequence", 2, "{After} times out unless the {before} artifact lands first — the intake has no retry window."),
            ("consequence", 3, "The orchestration engine pins {after} to the {before} completion event, and the pin is managed by the platform team with a change-freeze in effect."),
            ("fact", 1, "{After} takes its input straight from what {before} produces."),
            ("fact", 2, "The only source of the manifest that {after} needs is {before}."),
            ("fact", 3, "The lineage graph routes {after} downstream of {before}, and there is no alternate producer registered for its input."),
            ("convention", 1, "Order of operations here: {before}, then {after}."),
            ("convention", 2, "Common practice is to let {before} clear the path for {after}."),
            ("convention", 3, "The review checklist for this lane expects {before} to gate {after}, and reviewers reject plans that invert it."),
        ],
    },
}

# ---------------------------------------------------------------- 金标 description 模板
DESCRIPTIONS: dict[str, list[str]] = {
    "budget": [
        "The combined spend across all billable steps must stay within CNY {limit}.",
        "Total charges for the task, purchases and paid services included, are capped at CNY {limit}.",
    ],
    "deadline": [
        "The full task must be completed within {hours} hours.",
        "All steps together must finish inside a {hours}-hour window.",
    ],
    "privacy": [
        "{Pii} must not be sent to any external service; processing stays local.",
        "External services must not receive {pii}; local handling only.",
    ],
    "tool_auth": [
        "{Approval} must be completed before {required} runs.",
        "{Required} requires a recorded {approval} as a precondition.",
    ],
    "order": [
        "{Before} must be completed before {after}.",
        "The execution order must run {before} ahead of {after}.",
    ],
}


def readable(role: str) -> str:
    """角色的自然语言可读名（query 指代与 scope 映射的唯一锚）。"""
    return ROLES[role][2]


def fill_template(text: str, mapping: dict[str, str]) -> str:
    """占位符填充；{Pii}/{Approval} 等首字母大写变体由本函数统一处理。"""
    out = text
    for key, value in mapping.items():
        out = out.replace("{" + key[0].upper() + key[1:] + "}", value[0].upper() + value[1:])
        out = out.replace("{" + key + "}", value)
    return out

"""dataset_v5 规范层：在 v4 可执行任务世界上修三处设计缺陷，并新增结构不同的冻结 OOD 世界。

相对 v4 的改动（理由与证据见 reports/design_v5_ccfb.md §3）：
- N 近似干扰句按子类型（waiver / revoked / other_party / permission）每类每池 8 条；全部通过词法门槛：
  G1 提到他方规则时必须带"不适用于本任务"的条款，G2 必须锚定本任务（v4 test 池有 2 条违反 G1，
  五个训练 run 的公共错误集中在这两条上）；
- order / tool_auth 的 E、I 模板按"先提哪个角色"严格平衡，去掉 v4 I 版 5/6 先提 after 的位置伪影；
- 策略卡只给数据类定义，不再列字段别名示例（v4 卡把 test 池别名原样列出）；
- 新增 struct 世界：6 个阶段、单阶段 4 个备选、3 步 finish 块、审批锚定在 finish 步、时长分布右移，
  工具名与 train/heldout 两个世界都不重叠。其结构签名与 train 世界不相交（V12 校验）。
"""

from __future__ import annotations

import re

from dataset_v4_spec import (  # noqa: F401  （v4 原样沿用的部分）
    BACKGROUND, CONSTRAINT_TYPES, DATASETS, DEFAULT_SEVERITY, DIRECTIVE_LEXICON, GOAL_TEMPLATES,
    PII_CLASSES, TEAMS, directive_hits, fill_template,
)
from dataset_v4_spec import E_TEMPLATES as _E_V4
from dataset_v4_spec import I_TEMPLATES as _I_V4
from dataset_v4_spec import TOOLS as _TOOLS_V4
from dataset_v4_spec import WORLDS as _WORLDS_V4

SPEC_VERSION = "v5"

# ---------------------------------------------------------------- 工具表（v4 + struct 世界）
# role: (pool, readable_name, recipient, cost_range_cny, duration_range_min, clears_pii)
TOOLS: dict[str, tuple[str, str, str, tuple[int, int], tuple[int, int], bool]] = {
    **_TOOLS_V4,
    # ---- struct 池（只出现在 test_struct_ho）----
    "license_vendor_extract": ("struct", "the vendor-extract license", "local", (500, 2200), (30, 60), False),
    "query_open_registry": ("struct", "the open-registry query", "local", (0, 0), (200, 420), False),
    "replay_archived_feed": ("struct", "the archived-feed replay", "local", (0, 0), (90, 180), False),
    "scrape_partner_portal": ("struct", "the partner-portal scrape", "local", (100, 400), (60, 120), False),
    "load_into_clean_room": ("struct", "the clean-room load", "local", (0, 0), (60, 150), False),
    "push_to_shared_bucket": ("struct", "the shared-bucket push", "external", (30, 150), (15, 40), False),
    "run_schema_linter": ("struct", "the schema lint", "local", (0, 0), (20, 50), False),
    "run_sample_audit": ("struct", "the sample audit", "local", (0, 0), (90, 200), False),
    "train_on_rented_cluster": ("struct", "the rented-cluster training", "external", (200, 1100), (40, 90), False),
    "train_on_local_rack": ("struct", "the local-rack training", "local", (0, 0), (240, 480), False),
    "batch_score_offline": ("struct", "the offline batch scoring", "local", (0, 0), (120, 260), False),
    "bucketize_metrics": ("struct", "the metric bucketing", "local", (0, 0), (30, 80), True),
    "draft_findings_memo": ("struct", "the findings memo", "local", (0, 0), (40, 100), False),
    "publish_dashboard": ("struct", "the dashboard publication", "external", (0, 0), (15, 45), False),
    "email_regulator_digest": ("struct", "the regulator digest email", "external", (0, 0), (10, 30), False),
    "file_retention_record": ("struct", "the retention-record filing", "local", (0, 0), (15, 40), False),
    "brief_steering_board": ("struct", "the steering-board briefing", "external", (0, 0), (20, 50), False),
    "sign_release_ticket": ("struct", "the release-ticket signature", "local", (0, 0), (40, 120), False),
    "approve_cluster_lease": ("struct", "the cluster-lease approval", "local", (0, 0), (40, 120), False),
    "mask_identifiers_early": ("struct", "the early identifier masking", "local", (0, 0), (50, 110), True),
    "verify_lineage_hash": ("struct", "the lineage-hash verification", "local", (0, 0), (25, 70), False),
    "peer_review_memo": ("struct", "the memo peer review", "local", (0, 0), (40, 100), False),
    "ping_registry_status": ("struct", "the registry status ping", "local", (0, 0), (5, 15), False),
    "check_bucket_quota": ("struct", "the bucket quota check", "local", (0, 0), (5, 15), False),
    "read_rack_temperature": ("struct", "the rack temperature read", "local", (0, 0), (5, 15), False),
}

WORLDS: dict[str, dict[str, object]] = {
    **_WORLDS_V4,
    "struct": {
        "stages": [
            ("acquire", ["license_vendor_extract", "query_open_registry", "replay_archived_feed",
                         "scrape_partner_portal"], 1.0),
            ("stage", ["load_into_clean_room", "push_to_shared_bucket"], 1.0),
            ("check", ["run_schema_linter", "run_sample_audit"], 1.0),
            ("compute", ["train_on_rented_cluster", "train_on_local_rack", "batch_score_offline"], 1.0),
            ("condense", ["bucketize_metrics"], 1.0),
            ("summarize", ["draft_findings_memo"], 1.0),
        ],
        "finish": ["publish_dashboard", "email_regulator_digest", "file_retention_record", "brief_steering_board"],
        "finish_arity": 3,
        "optional": {
            "sign_release_ticket": ["publish_dashboard", "email_regulator_digest"],
            "approve_cluster_lease": ["train_on_rented_cluster"],
            "mask_identifiers_early": ["@acquire"],
            "verify_lineage_hash": ["batch_score_offline", "train_on_local_rack"],
            "peer_review_memo": ["brief_steering_board"],
        },
        "auth_pairs": [
            ("sign_release_ticket", "publish_dashboard"),
            ("sign_release_ticket", "email_regulator_digest"),
            ("approve_cluster_lease", "train_on_rented_cluster"),
        ],
        "order_pairs": [
            ("verify_lineage_hash", "batch_score_offline"),
            ("verify_lineage_hash", "train_on_local_rack"),
            ("peer_review_memo", "brief_steering_board"),
            ("file_retention_record", "publish_dashboard"),
            ("publish_dashboard", "file_retention_record"),
            ("email_regulator_digest", "brief_steering_board"),
            ("brief_steering_board", "email_regulator_digest"),
            ("file_retention_record", "email_regulator_digest"),
        ],
        "distractors": ["ping_registry_status", "check_bucket_quota", "read_rack_temperature"],
    },
}

HELDOUT_ROLES = sorted(r for r, spec in TOOLS.items() if spec[0] == "heldout")
STRUCT_ROLES = sorted(r for r, spec in TOOLS.items() if spec[0] == "struct")


def structural_signature(world: str) -> tuple[int, int, int, bool]:
    """世界的结构签名：(阶段数, finish 步数, 单阶段最大备选数, 是否存在锚定在 finish 步上的审批对)。"""
    spec = WORLDS[world]
    stages = spec["stages"]
    finish_arity = spec.get("finish_arity", 2)
    fanout = max(len(alts) for _, alts, _ in stages)
    finish_anchor = any(req in spec["finish"] for _, req in spec["auth_pairs"])
    return (len(stages), finish_arity, fanout, finish_anchor)


def possible_signatures(world: str) -> set[tuple[int, int, int, bool]]:
    """考虑阶段出现概率后，一个世界可能产生的全部签名（阶段数可变）。"""
    spec = WORLDS[world]
    stages = spec["stages"]
    required = sum(1 for _, _, p in stages if p >= 1.0)
    base = structural_signature(world)
    return {(n, *base[1:]) for n in range(required, len(stages) + 1)}


# ---------------------------------------------------------------- 策略卡（不含任何字段别名）
POLICY_CARD = (
    "Constraint types and params:\n"
    "- budget: {\"max_total_cost_cny\": int}; severity high; scope = every paid role in the catalog.\n"
    "- deadline: {\"max_duration_hours\": int}; severity high; scope = [\"role:*\"] (whole trace).\n"
    "- privacy: {\"protected_data_classes\": [class], \"forbidden_recipients\": [\"external\"]}; severity high; "
    "scope = every external role in the catalog. Classes: customer_pii (any field that identifies an "
    "individual customer), employee_pii (any field that identifies an individual employee), patient_records "
    "(any health or care record about a patient).\n"
    "- tool_auth: {\"approval_role\": role, \"required_role\": role}; severity medium; scope = [required_role].\n"
    "- order: {\"before_role\": role, \"after_role\": role}; severity medium; scope = [before_role, after_role].\n"
    "state: explicit = the user states the constraint as a directive; implicit = no directive, but the "
    "constraint follows from facts in the query (values may need arithmetic or mapping); query_state = none "
    "when nothing in the query restricts this plan. Waived, revoked or permissive statements, and rules that "
    "belong to another team, lane or project and are said not to apply here, do not count.\n"
    "Roles are written with the prefix role: in scope and without it in params."
)

# ---------------------------------------------------------------- E 版：order/tool_auth 改为提及顺序平衡
E_TEMPLATES: dict[str, dict[str, list[str]]] = {
    **_E_V4,
    "tool_auth": {
        "train": [
            "Run {required} only after {approval} has completed.",
            "{Required} requires {approval} first.",
            "Wait for {approval} before executing {required}.",
            "{Approval} must precede {required}.",
            "Do not execute {required} without a completed {approval}.",
            "A completed {approval} is a precondition for {required}.",
            "Get {approval} recorded before {required} runs.",
            "{Required} is allowed only once {approval} is on record.",
        ],
        "test": [
            "Before {required} runs, {approval} has to be finished.",
            "{Required} must stay blocked until {approval} is done.",
            "{Approval} has to be complete before {required} proceeds.",
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
            "Finish {before} ahead of {after}.",
            "Do {after} only after {before} is finished.",
            "{After} may start only once {before} is done.",
            "Start {after} only when {before} has completed.",
            "Hold {after} until {before} is complete.",
        ],
        "test": [
            "{Before} must come before {after}, not the other way round.",
            "Sequence the run so that {before} is completed prior to {after}.",
            "Do {before} first and {after} second.",
            "Order the steps with {before} in front of {after}.",
            "{After} has to wait until {before} has finished.",
            "Do not begin {after} until {before} is complete.",
            "Never run {after} ahead of {before}.",
            "{After} must not start before {before} is done.",
        ],
    },
}

# ---------------------------------------------------------------- I 版：order/tool_auth 改为提及顺序平衡
I_TEMPLATES: dict[str, dict[str, list[tuple[str, int, str]]]] = {
    **_I_V4,
    "tool_auth": {
        "train": [
            ("fact", 1, "On this account, {required} is rejected unless {approval} is already on record."),
            ("fact", 1, "{Approval} is what the audit gate checks before it lets {required} through."),
            ("consequence", 2, "Last quarter {a_required} went through without {approval}, and the auditors reversed it."),
            ("consequence", 2, "Every time {approval} was missing from the log, the platform bounced {required}."),
            ("fact", 3, "The workflow engine enforces the published control sequence, and that sequence chains {approval} into {required} with no skip path."),
            ("convention", 3, "The ops runbook opens the checklist for {required} with {approval}, and reviewers escalate any plan that skips the checklist."),
        ],
        "test": [
            ("fact", 1, "The platform refuses {required} whenever {approval} is missing from the log."),
            ("fact", 1, "{Approval} is the record the control gate looks for before {required} can proceed."),
            ("consequence", 2, "The last {required_bare} attempted without {approval} was rolled back by compliance within the hour."),
            ("consequence", 2, "After {approval} was skipped once, compliance froze {required} for a week."),
            ("fact", 3, "The control template that governs this lane links {required} to a completed {approval}, and the template has no override path."),
            ("convention", 3, "House practice files {approval} as the opening item for any {required_bare}, and the audit template checks for it."),
        ],
    },
    "order": {
        "train": [
            ("fact", 1, "{After} picks up its input from {before}."),
            ("fact", 1, "{Before} produces the file that {after} reads."),
            ("consequence", 2, "Last cycle {after} ran first and had to be redone once {before} finished."),
            ("consequence", 2, "When {before} was skipped last month, {after} returned empty results."),
            ("fact", 3, "The lineage for this task class shows {after} subscribing to the topic that {before} publishes, and that topic has no other publisher."),
            ("convention", 3, "{Before} is listed in the delivery template as the entry that unblocks {after}, and the template is checked at review."),
        ],
        "test": [
            ("fact", 1, "{After} takes its input straight from what {before} produces."),
            ("fact", 1, "{Before} writes the manifest that {after} consumes."),
            ("consequence", 2, "The previous run did {after} early and lost a day redoing it after {before}."),
            ("consequence", 2, "Whenever {before} lagged behind, {after} timed out waiting for its artifact."),
            ("fact", 3, "The lineage graph places {after} downstream of {before}, and no alternate producer is registered for its input."),
            ("convention", 3, "{Before} appears on the review checklist as the gate for {after}, and reviewers return plans that invert it."),
        ],
    },
}

# ---------------------------------------------------------------- N 版近似干扰句（子类型 × 2，每类每池 8 条）
# (subtype, text)；全部须通过 near_miss_gate（G1 + G2）。
NEAR_MISS: dict[str, dict[str, list[tuple[str, str]]]] = {
    "budget": {
        "train": [
            ("waiver", "There is no spending cap on this task; finance will cover whatever it costs."),
            ("waiver", "This task has no budget ceiling at all."),
            ("revoked", "The CNY {limit} ceiling from the pilot phase was lifted for this task last week."),
            ("revoked", "A CNY {limit} cap was once proposed for this work, but finance withdrew it."),
            ("other_party", "Another team works under a CNY {limit} cap, but that cap does not cover this task."),
            ("other_party", "The CNY {limit} limit belongs to the archive project and does not apply to this task."),
            ("permission", "Cost is not a factor here, even if the bill goes well past CNY {limit}."),
            ("permission", "This job may run over CNY {limit}; finance has pre-approved any amount."),
        ],
        "test": [
            ("waiver", "Spending is unrestricted for this engagement."),
            ("waiver", "No budget figure governs this request."),
            ("revoked", "An old CNY {limit} limit on this engagement was withdrawn when the budget was renewed."),
            ("revoked", "The CNY {limit} envelope that used to apply here was retired this quarter."),
            ("other_party", "The CNY {limit} allowance belongs to a separate project and does not apply here."),
            ("other_party", "A partner unit caps its spend at CNY {limit}, but that cap is not ours."),
            ("permission", "Finance confirmed the bill for this engagement can exceed CNY {limit} if needed."),
            ("permission", "Going past CNY {limit} is fine for this work."),
        ],
    },
    "deadline": {
        "train": [
            ("waiver", "There is no fixed deadline on this task; the {team} will pick it up whenever it lands."),
            ("waiver", "This task carries no time limit."),
            ("revoked", "An earlier draft of this task mentioned a {hours}-hour window, but that has since been dropped."),
            ("revoked", "The {hours}-hour target once set for this job was removed after replanning."),
            ("other_party", "The {hours}-hour turnaround applies to a different queue, not to this task."),
            ("other_party", "Another lane runs on a {hours}-hour clock, but that clock does not apply to this task."),
            ("permission", "Take as long as this work needs; even well over {hours} hours is fine."),
            ("permission", "This job may run past {hours} hours without any issue."),
        ],
        "test": [
            ("waiver", "Timing is flexible on this one."),
            ("waiver", "Nothing about this request is time-boxed."),
            ("revoked", "The {hours}-hour target for this engagement was retired after the last planning review."),
            ("revoked", "A {hours}-hour window was floated for this work and then withdrawn."),
            ("other_party", "A {hours}-hour window exists for the other lane only, not for this engagement."),
            ("other_party", "The partner team works to a {hours}-hour clock, which does not cover this request."),
            ("permission", "Nobody is waiting on this, so running past {hours} hours here is acceptable."),
            ("permission", "Exceeding {hours} hours is fine for this engagement."),
        ],
    },
    "privacy": {
        "train": [
            ("waiver", "Sharing the outputs with outside services is fine for this task; the data agreement covers external processing."),
            ("waiver", "No data-residency rule applies to this task."),
            ("revoked", "External processing of {pii} was approved for this engagement last week, lifting the old restriction."),
            ("revoked", "The local-only rule for {pii} was withdrawn for this work."),
            ("other_party", "The local-only rule for {pii} applies to the archive team, not to this task."),
            ("other_party", "Another unit keeps {pii} on-premise, but that rule does not cover this task."),
            ("permission", "Outside services may receive the data here, {pii} included."),
            ("permission", "This job can send {pii} to external tools."),
        ],
        "test": [
            ("waiver", "External tools are cleared to handle every field in this engagement."),
            ("waiver", "No residency restriction is attached to this request."),
            ("revoked", "Legal signed off on sending {pii} to approved outside processors for this work."),
            ("revoked", "The on-premise requirement for {pii} on this engagement was retired."),
            ("other_party", "A local-only rule for {pii} exists on another project but not on this one."),
            ("other_party", "The partner account keeps {pii} local, but that policy does not apply here."),
            ("permission", "Outbound transfers are permitted for this job, {pii} included."),
            ("permission", "Sending {pii} outside is fine for this request."),
        ],
    },
    "tool_auth": {
        "train": [
            ("waiver", "{Required} does not need {approval} on this account."),
            ("waiver", "No sign-off gates {required} in this task."),
            ("revoked", "{Approval} used to be required before {required}, but that rule was retired for this task."),
            ("revoked", "This workflow dropped {approval} as a step before {required}."),
            ("other_party", "On the other team's account {required} waits for {approval}; ours has no such gate."),
            ("other_party", "Another unit gates {required} behind {approval}, but that gate does not apply to this task."),
            ("permission", "{Required} can go ahead without {approval} this time."),
            ("permission", "This task may run {required} before {approval}."),
        ],
        "test": [
            ("waiver", "No sign-off is attached to {required} here."),
            ("waiver", "{Required} has no approval gate in this engagement."),
            ("revoked", "The old rule tying {required} to {approval} was removed this quarter for this engagement."),
            ("revoked", "For this request, the requirement to finish {approval} before {required} was lifted."),
            ("other_party", "Only the partner account gates {required} behind {approval}; this engagement does not."),
            ("other_party", "A separate team ties {required} to {approval}, but not on this request."),
            ("permission", "{Approval} is optional for {required} in this workspace."),
            ("permission", "{Required} may proceed here without waiting for {approval}."),
        ],
    },
    "order": {
        "train": [
            ("waiver", "There is no dependency between {before} and {after} in this task."),
            ("waiver", "{After} does not rely on anything from {before} here."),
            ("revoked", "{Before} used to precede {after}, but this workflow dropped that ordering."),
            ("revoked", "The old rule putting {before} ahead of {after} was retired for this task."),
            ("other_party", "Another team runs {before} ahead of {after}, but that ordering does not apply to this task."),
            ("other_party", "The archive workflow orders {before} before {after}; this task has no such ordering."),
            ("permission", "{Before} and {after} can run in either order in this task."),
            ("permission", "Whether {before} or {after} goes first makes no difference here."),
        ],
        "test": [
            ("waiver", "Nothing ties {after} to {before} in this engagement."),
            ("waiver", "{Before} and {after} are fully independent of each other on this request."),
            ("revoked", "An earlier version of this workflow put {before} first, but that requirement is gone."),
            ("revoked", "The ordering of {before} before {after} was lifted for this engagement."),
            ("other_party", "A partner pipeline sequences {before} ahead of {after}, but not on this request."),
            ("other_party", "The other lane orders {before} first; that order does not apply here."),
            ("permission", "The sequence of {before} and {after} is up to you here."),
            ("permission", "Either {before} or {after} may come first in this engagement."),
        ],
    },
}

# ---------------------------------------------------------------- N 句词法门槛（verify_dataset_v5 / 单测 / v4 复算共用）
_SELF_SCOPE = re.compile(
    r"\b(this (task|engagement|job|work|workflow|request|run|one|assignment|project|time|account|workspace)|"
    r"here|ours|our (account|workspace|lane|team))\b", re.IGNORECASE)
_OTHER_PARTY = re.compile(r"\b(another|(?<!each )other|partner|separate|different|archive (team|project|workflow))\b",
                          re.IGNORECASE)
_NON_APPLICABLE = re.compile(
    r"(not (to|on|for) this|does not (apply|cover)|doesn't (apply|cover)|but not on|not on this|"
    r"not on this one|but not (on )?this|not ours|has no such|this engagement does not|"
    r"which does not cover)", re.IGNORECASE)
_LICENSE = re.compile(
    r"\b(no|not|nothing|without|lifted|withdrawn|withdrew|retired|removed|dropped|gone|optional|either|up to you|"
    r"flexible|unrestricted|fine|permitted|cleared|signed off|approved|may|can|acceptable|exceed|"
    r"independent|difference)\b", re.IGNORECASE)


def near_miss_gate(text: str) -> dict[str, bool]:
    """G1：提到他方规则 => 必须带不适用于本任务的条款；G2：锚定本任务且带豁免/否定/许可标记。"""
    plain = re.sub(r"\{[^}]*\}", "X", text)
    other = bool(_OTHER_PARTY.search(plain))
    g1 = (not other) or bool(_NON_APPLICABLE.search(plain))
    g2 = bool(_SELF_SCOPE.search(plain)) and bool(_LICENSE.search(plain))
    return {"other_party": other, "G1": g1, "G2": g2}


def first_mention(text: str, a: str, b: str) -> str:
    """模板中先出现 {a…} 还是 {b…}（大小写不敏感；{a_required}/{required_bare} 归入 required）。"""
    low = text.lower()
    ia = min((low.find(t) for t in ("{" + a, "{a_" + a) if low.find(t) >= 0), default=10 ** 9)
    ib = min((low.find(t) for t in ("{" + b, "{a_" + b) if low.find(t) >= 0), default=10 ** 9)
    return a if ia < ib else b


# ---------------------------------------------------------------- 角色可读名（覆盖 v4 版本以包含 struct 工具）
def tool_name(role: str) -> str:
    return TOOLS[role][1]


def bare_name(role: str) -> str:
    """去冠词的可读名（用于 "a {required_bare}" 句式）。"""
    name = tool_name(role)
    return name[4:] if name.startswith("the ") else name


def with_article(role: str) -> str:
    bare = bare_name(role)
    return ("an " if bare[0] in "aeiouAEIOU" else "a ") + bare

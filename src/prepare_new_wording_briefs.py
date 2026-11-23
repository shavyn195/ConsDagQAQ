"""Prepare new group-disjoint briefs for independent writers, with no sample phrasings."""
import csv
import hashlib
import json
from pathlib import Path

from rescore_v4_side import ROOT, load_jsonl


def fact(constraint, names):
    p=constraint["params"]
    if constraint["type"]=="budget":
        return f"整项任务的总费用上限为 {p['max_total_cost_cny']} 元"
    if constraint["type"]=="deadline":
        return f"整项任务的最长耗时为 {p['max_duration_hours']} 小时"
    if constraint["type"]=="privacy":
        classes={"patient_records":"患者记录","employee_pii":"员工身份数据","customer_pii":"客户身份数据"}
        return f"{classes[p['protected_data_classes'][0]]}只能在本地处理，不可传给外部服务"
    if constraint["type"]=="tool_auth":
        return f"使用 {names[p['required_role']]} 要先完成 {names[p['approval_role']]}"
    return f"{names[p['before_role']]} 必须先于 {names[p['after_role']]}"


def main():
    out=ROOT/"outputs/independent_writer_materials"
    rows=[r for s in ("test_tpl_ho","test_tool_ho") for r in load_jsonl(ROOT/f"data/processed_v4/{s}.jsonl")]
    with (ROOT/"outputs/dataset_audit/v4-implicit-human-review-v1/reviewer-A/review.csv").open(encoding="utf-8-sig") as handle:
        blind={r["query"] for r in csv.DictReader(handle)}
    used={r["group_id"] for r in rows if r["query"] in blind}
    for folder in ("approval_wording_v1","authored_wording_v1","evidence_edits_v1"):
        for r in load_jsonl(ROOT/f"outputs/{folder}/panel.jsonl"):
            used.add(r.get("group_id") or r["group"])
    mapping=[]
    for split in ("test_tpl_ho","test_tool_ho"):
        for t in ("budget","deadline","privacy","order","tool_auth"):
            pool=[r for r in rows if r["subset"]==split and r["variant"]=="implicit" and
                  r["group_id"] not in used and [c["type"] for c in r["gold"]["constraints"]]==[t]]
            order=sorted(pool,key=lambda r: hashlib.sha256(("human-wording/20261122/"+r["group_id"]).encode()).digest())
            assert len(order)>=2
            for r in order[:2]:
                names={c["role"]:c["name"] for c in r["catalog"]}
                mapping.append(dict(group=r["group_id"],goal=r["task_goal"],fact=fact(r["gold"]["constraints"][0],names)))
                used.add(r["group_id"])
    mapping.sort(key=lambda r: hashlib.sha256(("order/"+r["group"]).encode()).digest())
    out.mkdir(exist_ok=True)
    lines=["# 独立撰写请求的事实卡","",
           "交给没有看过模型输出或原测试句子的撰写者。每张卡写两句能配合业务目标使用的英文。第一句用你自己的表达交代这次任务的约束，第二句提及只属于历史、其他任务或已撤销的同类要求。只提供事实和工具名，措辞由撰写者决定。请记录作者匿名编号、写作语言和是否使用辅助工具。","",
           "每次评测使用三种输入：目标加第一句、目标加第二句、以及目标加两句。另一名读者独立判断含义与证据，有歧义的原稿和修订分别保留。英语成绩与中文译文试读分别报告。",""]
    for i,r in enumerate(mapping,1):
        lines.extend([f"**W{i:02}**　任务目标：{r['goal']}","",f"需表达的事实：{r['fact']}。","",
                      "本次要求：","", "背景说明：",""])
    (out/"briefs.md").write_text("\n".join(lines),encoding="utf8")
    (out/"group-map.json").write_text(json.dumps({f"W{i:02}":r["group"] for i,r in enumerate(mapping,1)},indent=2))
    assert len({r["group"] for r in mapping})==20


if __name__=="__main__":
    main()

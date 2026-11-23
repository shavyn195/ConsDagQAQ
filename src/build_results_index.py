"""Index locally archived ConsDAG study data and outputs by experiment family."""
from collections import defaultdict
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
FAMILIES = {
    "部署与推理开销": "冻结权重、原生输入输出 token、单条请求耗时、完整编译正确性与固定长度生成对照。",
    "基准数据及程序化核查": "冻结的四份数据、执行见证、数据构造分布和质量核查。人工审查题包另行提供。",
    "E1 训练与同底座零示例": "三个冻结适配器的各切分原始回答与评分。metrics.json 中有训练与零示例两个分支。",
    "E1 强提示词与字段指标": "独立 API 调用得到的强模型逐题回答、配对差值与字段诊断。",
    "证据改写": "逐题原句、改写、无关标签和去引号复测。primary 为前后同时全对。",
    "逐题新措辞": "三个条件下在相同输入上比较小模型和强提示词，同时保留每条原始生成。",
    "审批歧义": "44 对澄清句、执行计划证书、模型原始回答与每题评分。",
    "E2 训练与规划": "开发探针、训练失败与种子对照、冻结留出、交叉干预及全量执行细目。",
    "历史数据和早期实验": "早期版本、诊断与本地归档的快照。版本不同，数值请结合对应台账阅读。"
}

def category(path):
    rel = path.relative_to(ROOT)
    root, name, *rest = rel.parts
    if root == "data":
        if name not in {"processed","processed_v2","processed_v3","processed_v4"}:
            return None
        return "基准数据及程序化核查" if name == "processed_v4" else "历史数据和早期实验"
    if name in {"_lit"} or "v4-implicit-human-review-v1" in rest or "private" in rel.parts:
        return None
    if name == "dataset_audit":
        return "基准数据及程序化核查"
    if name == "e1" and rest and rest[0].endswith("-v4"):
        return "E1 训练与同底座零示例"
    return {"compiler_efficiency_v1":"部署与推理开销", "e1_v4_side":"E1 强提示词与字段指标", "evidence_edits_v1":"证据改写",
            "authored_wording_v1":"逐题新措辞", "approval_wording_v1":"审批歧义",
            "e2_v4":"E2 训练与规划"}.get(name, "历史数据和早期实验")

def main():
    grouped = defaultdict(lambda: defaultdict(list))
    for directory in ("outputs","data"):
        for p in sorted((ROOT/directory).rglob("*")):
            if not p.is_file() or p.suffix.lower() not in {".json",".jsonl",".csv",".tsv",".parquet"}:
                continue
            if any("checkpoint" in part or part in {"adapter","wandb","runs"} for part in p.parts):
                continue
            family = category(p)
            if family:
                group=p.parent.relative_to(ROOT).as_posix()
                grouped[family][group].append(p)
    n=sum(len(files) for paths in grouped.values() for files in paths.values())
    lines=["# ConsDAG 逐题数据和运行文件索引","",f"本地已归档的实验数据、配置和结果文件共 {n} 个。可按目录、模型名或实验名搜索。[查看带解释的实验总表](consdag_experiments_overview.md)。","","JSONL 每行是一条记录，JSON 通常保存汇总或运行设置。历史快照可能与后续归档重复。文件数不能用作独立运行数。","","| 类别 | 文件数 | 内容 |","|---|---:|---|"]
    for family,description in FAMILIES.items():
        size=sum(map(len,grouped[family].values()))
        lines.append(f"| {family} | {size} | {description} |")
    for family in FAMILIES:
        lines.extend(["","## "+family,""])
        for group,files in grouped[family].items():
            links=[f"[{p.name}](../{quote(p.relative_to(ROOT).as_posix())})" for p in files]
            lines.extend([f"**{group}**",""," · ".join(links),""])
    (ROOT/"reports/consdag_results_index.md").write_text("\n".join(lines)+"\n",encoding="utf8")
    print(n)

if __name__ == "__main__":
    main()

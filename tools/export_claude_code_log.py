"""把 Claude Code 会话记录(jsonl)导出为可读 Markdown，仅追加新内容。

用法:
    python tools/export_claude_code_log.py            # 追加导出全部会话
    python tools/export_claude_code_log.py --session <uuid>   # 只导出指定会话

记录来源: ~/.claude/projects/D--Proj-AAAKXSJKJ-all-consdag-constraint-compiler-exp/*.jsonl
输出文件: reports/claude_code_log.md
去重状态: reports/.claude_code_log_state.json （记录每个会话已导出的行数）
"""

import argparse
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SRC_DIR = Path.home() / ".claude" / "projects" / "D--Proj-AAAKXSJKJ-all-consdag-constraint-compiler-exp"
OUT_FILE = REPO / "reports" / "claude_code_log.md"
STATE_FILE = REPO / "reports" / ".claude_code_log_state.json"

HEADER = "# Claude Code 对话记录\n\n按时间顺序追加，包含用户输入、Claude 回复、工具调用与工具结果。\n\n"


def text_of(message):
    """把 content 归一化成纯文本，保留工具调用与结果。"""
    content = message.get("content")
    if isinstance(content, str):
        return content, []
    parts, tools = [], []
    for block in content or []:
        if not isinstance(block, dict):
            parts.append(str(block))
            continue
        kind = block.get("type")
        if kind == "text":
            parts.append(block.get("text", ""))
        elif kind == "tool_use":
            tools.append((block.get("name", "unknown"), block.get("input")))
        elif kind == "tool_result":
            body = block.get("content")
            if isinstance(body, list):
                body = "\n".join(b.get("text", "") for b in body if isinstance(b, dict))
            parts.append(str(body))
        elif kind == "thinking":
            parts.append("[thinking] " + block.get("thinking", ""))
    return "\n".join(p for p in parts if p), tools


def render(entry):
    role = entry.get("type")
    ts = str(entry.get("timestamp", ""))[:19].replace("T", " ")
    message = entry.get("message") or {}
    if role == "user":
        text, tools = text_of(message)
        if not text.startswith("toolu_") and tools == [] and text:
            return f"\n#### [{ts}] 用户\n\n{text}\n"
        if text:
            return f"\n#### [{ts}] 工具结果\n\n```\n{text}\n```\n"
        return ""
    if role == "assistant":
        text, tools = text_of(message)
        out = []
        if text:
            out.append(f"\n#### [{ts}] Claude\n\n{text}\n")
        for name, inp in tools:
            payload = json.dumps(inp, ensure_ascii=False, indent=2)
            out.append(f"\n**工具调用: {name}**\n\n```json\n{payload}\n```\n")
        return "".join(out)
    return ""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--session", default=None)
    args = parser.parse_args()

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    state = {}
    if STATE_FILE.exists():
        state = json.loads(STATE_FILE.read_text(encoding="utf-8"))

    sessions = sorted(SRC_DIR.glob("*.jsonl"), key=lambda p: p.stat().st_mtime)
    if args.session:
        sessions = [p for p in sessions if p.stem == args.session]

    added = 0
    is_new = not OUT_FILE.exists()
    with OUT_FILE.open("a", encoding="utf-8") as fh:
        if is_new:
            fh.write(HEADER)
        for path in sessions:
            sid = path.stem
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
            done = state.get(sid, 0)
            if done >= len(lines):
                continue
            if done == 0:
                fh.write(f"\n---\n\n## 会话 {sid}\n")
            for raw in lines[done:]:
                try:
                    entry = json.loads(raw)
                except Exception:
                    continue
                chunk = render(entry)
                if chunk:
                    fh.write(chunk)
                    added += 1
            state[sid] = len(lines)

    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    size = OUT_FILE.stat().st_size
    print(f"appended_entries={added} sessions={len(sessions)} file={OUT_FILE} size={size}")


if __name__ == "__main__":
    main()

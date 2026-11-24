from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT / "src"))

import run_pe_v6


def row(config: dict, params: dict, messages: list[dict[str, str]]) -> dict:
    saved = {
        "sample_id": "sample-1",
        "request_hash": run_pe_v6.request_fingerprint(config, params, messages),
        "raw": "{\"constraints\": []}",
        "model": params["model"],
        "finish": "stop",
        "usage": {"total_tokens": 12},
    }
    saved["prediction_sha256"] = run_pe_v6.prediction_hash(saved)
    return saved


def test_pe_cache_hits_require_matching_global_config_and_response_integrity(tmp_path):
    config = {"data": {"train": "data-sha"}, "source_hashes": {"runner": "source-sha"}}
    params = {"model": "qwen-max", "temperature": 0, "max_tokens": 384}
    messages = [{"role": "user", "content": "query"}]
    expected = {"sample-1": run_pe_v6.request_fingerprint(config, params, messages)}
    cache = row(config, params, messages)
    path = tmp_path / "dev.jsonl"
    path.write_text(json.dumps(cache) + "\n", encoding="utf-8")

    assert set(run_pe_v6.restore_verified(path, expected, "qwen-max")) == {"sample-1"}
    changed_data = {"data": {"train": "different-data-sha"}, "source_hashes": {"runner": "source-sha"}}
    stale = {"sample-1": run_pe_v6.request_fingerprint(changed_data, params, messages)}
    with pytest.raises(ValueError, match="stale"):
        run_pe_v6.restore_verified(path, stale, "qwen-max")

    corrupted = json.loads(path.read_text(encoding="utf-8"))
    corrupted["raw"] = "changed response"
    path.write_text(json.dumps(corrupted) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="corrupt"):
        run_pe_v6.restore_verified(path, expected, "qwen-max")


def test_completed_pe_cache_detects_any_artifact_mutation(tmp_path):
    config = {"model": "qwen-max", "style": "zero"}
    (tmp_path / "config.json").write_text("{}\n", encoding="utf-8")
    (tmp_path / "dev.jsonl").write_text("{}\n", encoding="utf-8")
    subsets = ["dev"]
    artifacts = {name: run_pe_v6.file_hash(tmp_path / name) for name in ("config.json", "dev.jsonl")}
    run_pe_v6.write_json_atomic(tmp_path / "completion.json", {
        "schema_version": 1, "status": "complete", "model": "qwen-max", "style": "zero",
        "config_sha256": run_pe_v6.canonical_hash(config), "artifacts": artifacts,
    })
    run_pe_v6.verify_completion(tmp_path, config, subsets, "qwen-max", "zero")
    (tmp_path / "dev.jsonl").write_text("tampered\n", encoding="utf-8")
    with pytest.raises(ValueError, match="artifact hashes differ"):
        run_pe_v6.verify_completion(tmp_path, config, subsets, "qwen-max", "zero")


def test_complete_cache_can_resume_without_api_key_and_partial_cache_requires_it(monkeypatch, tmp_path):
    # API and OS lock are isolated; this exercises main's real cache/config flow.
    monkeypatch.setitem(sys.modules, "fcntl", SimpleNamespace(LOCK_EX=1, LOCK_NB=2, flock=lambda *_: None))
    monkeypatch.setattr(run_pe_v6, "ROOT", tmp_path)
    data = tmp_path / "data/processed_v6"
    data.mkdir(parents=True)
    records = [{"sample_id": "sample-1"}]
    for subset in ("train", "dev"):
        (data / f"{subset}.jsonl").write_text(json.dumps(records[0]) + "\n", encoding="utf-8")
    monkeypatch.setattr(run_pe_v6, "validate_v6_freeze", lambda _: None)
    monkeypatch.setattr(run_pe_v6, "eval_subsets", lambda _: ["dev"])
    monkeypatch.setattr(run_pe_v6, "chat_messages_v4", lambda _: [
        {"role": "system", "content": "JSON"}, {"role": "user", "content": "query"},
    ])
    monkeypatch.setattr(sys, "argv", ["run_pe_v6", "--model", "qwen-max", "--style", "zero"])
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
    with pytest.raises(SystemExit, match="missing requests"):
        run_pe_v6.main()

    requested = []
    def response(params, messages):
        requested.append(messages)
        return {"raw": "{}", "model": params["model"], "finish": "stop", "usage": {}}
    monkeypatch.setattr(run_pe_v6, "request", response)
    monkeypatch.setenv("DASHSCOPE_API_KEY", "unit-test-value-never-sent")
    run_pe_v6.main()
    assert len(requested) == 1

    monkeypatch.delenv("DASHSCOPE_API_KEY")
    run_pe_v6.main()
    assert len(requested) == 1


def test_analysis_admits_only_complete_untampered_pe_cache(monkeypatch, tmp_path):
    import analyze_v6_main as analysis

    data = tmp_path / "data"
    data.mkdir()
    for subset in ("train", "dev"):
        (data / f"{subset}.jsonl").write_text('{"sample_id":"sample-1"}\n', encoding="utf-8")
    messages = [{"role": "system", "content": "JSON"}, {"role": "user", "content": "query"}]
    monkeypatch.setattr(analysis, "chat_messages_v4", lambda _: messages)
    params = {"model": "qwen-max", "temperature": 0, "max_tokens": 384}
    config = {
        "params": params, "style": "zero", "url": run_pe_v6.DEFAULT_URL,
        "data": analysis.current_data_hashes(data, ["dev"]), "demo_hash": run_pe_v6.fingerprint([]),
        "source_hashes": {name: run_pe_v6.file_hash(ROOT / "src" / f"{name}.py")
                          for name in run_pe_v6.SOURCE_NAMES},
    }
    out = tmp_path / "qwen-max-zero"
    out.mkdir()
    run_pe_v6.write_json_atomic(out / "config.json", config)
    prediction = row(config, params, messages)
    (out / "dev.jsonl").write_text(json.dumps(prediction) + "\n", encoding="utf-8")

    def seal():
        run_pe_v6.write_json_atomic(out / "completion.json", {
            "schema_version": 1, "status": "complete", "model": "qwen-max", "style": "zero",
            "config_sha256": run_pe_v6.canonical_hash(config),
            "artifacts": {name: run_pe_v6.file_hash(out / name) for name in ("config.json", "dev.jsonl")},
        })
    seal()
    assert analysis.verified_pe_run(out, data, ["dev"], "qwen-max") == (True, "complete")
    prediction["raw"] = "changed response"
    (out / "dev.jsonl").write_text(json.dumps(prediction) + "\n", encoding="utf-8")
    assert analysis.verified_pe_run(out, data, ["dev"], "qwen-max")[1] == "pe_completion_or_artifact_hash_mismatch"
    seal()
    assert analysis.verified_pe_run(out, data, ["dev"], "qwen-max")[1].startswith("pe_cache_fingerprint_mismatch")
    config["params"]["temperature"] = 1
    run_pe_v6.write_json_atomic(out / "config.json", config)
    assert analysis.verified_pe_run(out, data, ["dev"], "qwen-max")[1] == "pe_config_mismatch"

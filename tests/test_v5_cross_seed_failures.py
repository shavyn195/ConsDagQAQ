from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from analyze_v5_cross_seed_failures import analyze


def test_frozen_v5_cross_seed_failure_audit_runs_on_complete_artifacts(tmp_path):
    result = analyze(ROOT / 'data/processed_v5', ROOT / 'outputs/e1')
    assert set(result['arms']) == {'dev', 'test_tpl_ho', 'test_tool_ho', 'test_struct_ho'}
    for split, values in result['arms'].items():
        assert values['task_groups'] in (300, 350)
        assert sum(values['record_failure_count_by_number_of_seeds'].values()) == values['constrained_records']
        assert sum(values['group_failure_count_by_number_of_seeds'].values()) == values['task_groups']
        assert set(values['seeds']) == {'42', '43', '44'}


def test_dataset_hash_mismatch_is_a_hard_failure(tmp_path):
    dataset = tmp_path / 'data'
    dataset.mkdir()
    for split in ('train', 'dev', 'test_tpl_ho', 'test_tool_ho', 'test_struct_ho'):
        (dataset / f'{split}.jsonl').write_text('')
    (dataset / 'generation_report.json').write_text('{"sha256": {}}')
    with pytest.raises(ValueError, match='hashes do not match'):
        analyze(dataset, ROOT / 'outputs/e1')

"""Final local evidence checks; does not edit the manuscript or Word."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
from analyze_demand_warning import sha256_file, write_json

ROOT = Path(__file__).resolve().parents[1]


def main():
    base = ROOT/'outputs/analysis'
    directories = ['SG-EXP-024-proxy-engineering', 'SG-EXP-025-rolling-calibration',
                   'SG-EXP-026-charging-decision', 'SG-EXP-024-matched-current-probe']
    count = 0
    for name in directories:
        folder = base/name
        for filename, digest in json.loads((folder/'manifest.json').read_text()).items():
            assert sha256_file(folder/filename) == digest
            count += 1
        for filename, digest in json.loads((folder/'sources.json').read_text()).items():
            assert sha256_file(ROOT/filename) == digest
    folder = base/'SG-EXP-024-matched-current-probe'
    samples = json.loads((folder/'sample_metadata.json').read_text())
    selection = json.loads((folder/'selection.json').read_text())['sessions']
    assert [r['sessionID'] for r in samples] == [r['sessionID'] for r in selection]
    profiles = pd.read_csv(folder/'normalized_bin_shapes.csv')
    checked = 0
    for s in samples:
        if s['status'] != 'MATCHED_CURRENT_SHAPE_ONLY':
            continue
        part = profiles[profiles.node == s['node']]
        p, u = part.normalized_current_fraction.to_numpy(), part.uniform_proxy_fraction.to_numpy()
        assert len(part) == s['bins'] and abs(p.sum()-1) < 1e-12 and np.all(p >= 0)
        assert np.allclose(u, 1/len(p), rtol=0, atol=1e-15)
        assert np.isclose(.5*np.abs(p-u).sum(), s['normalized_shape_total_variation'], rtol=0, atol=1e-12)
        assert np.isclose(p.max()*len(p), s['peak_bin_fraction_ratio_to_uniform'], rtol=0, atol=1e-12)
        assert s['missing_power_rows'] == s['rows'] and s['missing_voltage_rows'] == s['rows']
        checked += 1
    for path, expected in {
        'docs/thesis/thesis-manuscript.md': '0a29a4f4c8f16699d6567de792bf14cb9705ecb372a6ab39727a0ccefa45d910',
        'outputs/thesis/基于站内多关系图与机制诊断的充电节点短期负荷预测研究_正式论文.docx': 'f45d19b66e36170136f33013e8cd5cf823835c1bd2994bba9e619be8515173a3'
    }.items():
        assert sha256_file(ROOT/path) == expected
    decision = json.loads((base/'SG-EXP-026-charging-decision/actual_thesis_case_status.json').read_text())
    assert decision['status'] == 'MATERIALS_REQUIRED' and not decision['executable']
    result = dict(status='PASS', derived_artifact_hashes=count,
                  matched_current_shapes_recomputed=checked, source_hashes_unchanged=True,
                  manuscript_unchanged=True, canonical_docx_unchanged=True,
                  real_dispatch_benefit_completed=False, training_started=False)
    write_json(base/'SG-EXP-024-026-final-integrity.json', result)
    print(result)


if __name__ == '__main__':
    main()

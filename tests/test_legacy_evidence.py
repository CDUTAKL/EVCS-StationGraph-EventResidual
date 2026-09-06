"""Nontrivial guards for the offline evidence aggregation (no model training)."""
import importlib.util
from pathlib import Path
import numpy as np
import pytest

spec=importlib.util.spec_from_file_location('legacy',Path(__file__).parents[1]/'scripts/lock_legacy_evidence.py')
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

def test_cell_partition_and_contribution():
    rows=m.cell_stats(np.zeros(4),np.array([1.,2.,3.,4.]),np.array([1,1,0,0]),np.array([1,0,1,0]))
    assert [r['contribution_percent'] for r in rows]==[10.,20.,30.,40.]
    assert sum(r['sum_absolute_error'] for r in rows)/4==2.5

def test_empty_cell_is_rejected():
    with pytest.raises(ValueError,match='empty cell'):
        m.cell_stats(np.zeros(2),np.ones(2),np.zeros(2),np.zeros(2))

def test_block_weighting_not_mean_of_block_means():
    result=m.block_ci([10.,0.],[10,1])
    assert result['mean_difference']==10/11
    assert result['mean_difference']!=.5

def test_paired_constant_difference_and_reproducibility():
    a=m.block_ci([2.,6.,10.],[1,3,5]); b=m.block_ci([2.,6.,10.],[1,3,5])
    assert a==b
    assert a['lower']==a['upper']==2.

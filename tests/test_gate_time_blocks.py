import numpy as np
import pytest

from analyze_gate_time_blocks import block_totals
from analyze_independent_calibration import bootstrap_ratio


def test_block_ratio_weights_keys_instead_of_unequal_block_means():
    difference=np.array([1.,3.,9.]).reshape(3,1,1)
    sums,counts=block_totals(difference,np.ones_like(difference,dtype=bool),np.array([0,0,1]))
    np.testing.assert_array_equal(sums,[4.,9.])
    np.testing.assert_array_equal(counts,[2,1])
    ci=bootstrap_ratio(sums,counts,np.array([[0,1],[0,0],[1,1]]))
    assert ci['estimate']==pytest.approx(13/3)


def test_all_horizons_and_nodes_stay_inside_origin_block():
    difference=np.arange(12.).reshape(3,2,2)
    mask=np.zeros_like(difference,dtype=bool)
    mask[:,0,0]=True
    sums,counts=block_totals(difference,mask,np.array([0,0,1]))
    np.testing.assert_array_equal(sums,[4.,8.])
    np.testing.assert_array_equal(counts,[2,1])


def test_empty_resamples_are_rejected_not_removed():
    with pytest.raises(ValueError,match='Empty bootstrap'):
        bootstrap_ratio(np.array([1.,0]),np.array([1,0]),np.array([[1,1]]))

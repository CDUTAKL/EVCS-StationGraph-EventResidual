"""SG-EXP-021 的微型精确夹具测试；不读取或修改正式归档。"""

import unittest
import tempfile
import csv
from pathlib import Path
from datetime import datetime, timezone

import numpy as np

import analyze_demand_warning as analysis


class DemandWarningTests(unittest.TestCase):
    """验证阈值、时间、成组重采样和事件边界，不以性能为测试目标。"""

    def test_dedup_consistent(self) -> None:
        """重叠真值只按唯一目标时点计一次，同时保持节点粒度校验。"""
        times = np.array([[0, 15], [15, 30]])
        truth = np.array([[[1., 2.], [3., 4.]], [[3., 4.], [5., 6.]]])
        unique, values, diagnostics = analysis.deduplicate_truth(times, truth, 1e-10, 0.)
        np.testing.assert_array_equal(unique, [0, 15, 30])
        np.testing.assert_array_equal(values, [[1, 2], [3, 4], [5, 6]])
        self.assertEqual(diagnostics['duplicate_occurrences'], 1)

    def test_dedup_inconsistent_node_truth_refused(self) -> None:
        """即使节点总量相同，节点间抵消的不一致重叠真值也必须拒绝。"""
        truth = np.array([[[1., 2.], [3., 4.]], [[4., 3.], [5., 6.]]])
        with self.assertRaisesRegex(ValueError, 'overlapping truth'):
            analysis.deduplicate_truth(np.array([[0, 15], [15, 30]]), truth, 1e-10, 0.)

    def test_strict_tie_and_linear_quantile(self) -> None:
        """等于阈值为阴性；分位数使用指定线性插值，不选更有利阈值。"""
        threshold = float(np.quantile([0., 1., 2., 3.], .5, method='linear'))
        self.assertEqual(threshold, 1.5)
        counts = analysis.confusion_counts(np.array([1.5, 2., 1.]), np.array([2., 1.5, 1.]), threshold)
        np.testing.assert_array_equal(counts, [0, 1, 1, 1])

    def test_no_positive_denominators(self) -> None:
        """没有真实/预测阳性时 recall/precision/F1 未定义，FPR 为零。"""
        metrics = analysis.metric_values(np.array([0, 0, 0, 3]))
        self.assertTrue(np.isnan(metrics[0]))
        self.assertTrue(np.isnan(metrics[1]))
        self.assertEqual(metrics[2], 0.)
        self.assertTrue(np.isnan(metrics[3]))
        np.testing.assert_allclose(analysis.metric_values(np.array([1, 1, 1, 1])), [.5, .5, .5, .5])
        self.assertEqual(analysis.clean_json({'x': float('nan')})['x'], None)

    def test_episodes_break_on_gap_and_tie(self) -> None:
        """时间缺口必须断开事件；等于阈值不会并入事件。"""
        episodes = analysis.build_episodes(np.array([0, 15, 30, 60, 75]), np.array([2., 2., 1., 2., 2.]), 1., 15)
        self.assertEqual([(e['onset_ns'], e['last_target_ns']) for e in episodes], [(0, 15), (60, 75)])

    def test_pre_onset_same_episode_only(self) -> None:
        """事后警报和指向其他事件的警报不能记为当前事件提前命中。"""
        episode = {'onset_ns': 60, 'last_target_ns': 75}
        cutoffs = np.array([0, 15, 30, 45, 60, 75])
        times = cutoffs[:, None] + np.array([0, 15, 30, 45])
        alarms = np.zeros_like(times, dtype=bool)
        alarms[0, 3] = True  # target=45，虽提前发出但未落在本事件
        alarms[4, 0] = True  # issue=60，不严格早于 onset
        self.assertIsNone(analysis.earliest_warning(episode, cutoffs, times, alarms))
        alarms[1, 3] = True  # issue=15、target=60，为有效提前警报
        match = analysis.earliest_warning(episode, cutoffs, times, alarms)
        self.assertEqual(match['issue_ns'], 15)
        self.assertEqual(match['target_ns'], 60)

    def test_full_history_eligibility(self) -> None:
        """需要全部四个先前预测原点；缺一个也排除，不能用部分机会评价。"""
        self.assertTrue(analysis.history_eligible(60, {0, 15, 30, 45, 60}, 60, 15))
        self.assertFalse(analysis.history_eligible(60, {15, 30, 45, 60}, 60, 15))
        self.assertFalse(analysis.history_eligible(60, {0, 15, 45, 60}, 60, 15))

    def test_archived_offsets_preserved(self) -> None:
        """归档零提前量必须被标注，不能暗中把目标时点向后移动。"""
        result = analysis.time_semantics(np.array([[100, 115, 130, 145]]), np.array([100]), 15)
        self.assertEqual(result['observed_target_start_lead_steps'], [0, 1, 2, 3])
        self.assertFalse(result['strict_future_target_start_contract'])
        with self.assertRaisesRegex(ValueError, 'target timestamp'):
            analysis.time_semantics(np.array([[85, 100, 115, 130]]), np.array([100]), 15)

    def test_grouped_counts_equal_direct(self) -> None:
        """日成组四格加和精确等于全体四格，包含所有种子和步长。"""
        truth = np.array([[0., 2.], [2., 0.], [0., 0.]])
        pred = np.array([[0., 2.], [0., 2.], [2., 0.]])
        grouped = analysis.daily_counts(truth, pred, 1., np.array([0, 0, 1]), 2)
        np.testing.assert_array_equal(grouped.sum(axis=0)[-1], analysis.confusion_counts(truth, pred, 1.))
        weights = np.array([[2, 0], [0, 2], [1, 1]])
        result = analysis.apply_day_weights(grouped[None, None], weights)
        np.testing.assert_array_equal(result[2, 0, 0], grouped.sum(axis=0))

    def test_local_date_dst(self) -> None:
        """日期按 cutoff 的洛杉矶本地时间而非 UTC；夏令时由 zoneinfo 处理。"""
        values = [datetime(2021, 3, 14, 7, 45, tzinfo=timezone.utc), datetime(2021, 3, 14, 8, 0, tzinfo=timezone.utc)]
        dates, inverse = analysis.local_day_groups(np.array([int(v.timestamp()) * 10**9 for v in values]), 'America/Los_Angeles')
        self.assertEqual(dates, ['2021-03-13', '2021-03-14'])
        np.testing.assert_array_equal(inverse, [0, 1])

    def test_block_draws_consecutive_non_circular(self) -> None:
        """七日移动块只用真实连续日期，不在尾首之间形成假连续块。"""
        draws = analysis.day_draws(10, 5, 20261002, 7)
        self.assertEqual(draws.shape, (5, 10))
        np.testing.assert_array_equal(np.diff(draws[:, :7], axis=1), np.ones((5, 6)))
        self.assertTrue(np.all(draws[:, :7] <= 9))

    def test_validation_refuses_nonfinite_duplicate_and_shape(self) -> None:
        """真实审计入口必须拒绝非有限预测、重复原点及不兼容张量形状。"""
        step = 15 * analysis.NS_PER_MINUTE
        config = dict(expected_origin_counts={'test': 3}, expected_horizons=4, expected_nodes=2, step_minutes=15)
        arrays = dict(y_true=np.zeros((3, 4, 2)), y_pred=np.zeros((3, 4, 2)), origins=np.arange(3),
                      node_ids=np.array(['a', 'b']), origin_cutoff_ns=np.arange(3)*step,
                      target_timestamps_ns=(np.arange(3)[:, None]+np.arange(4))*step,
                      target_event=np.zeros((3, 4, 2), dtype=bool), rule_trigger=np.zeros((3, 4, 2), dtype=bool))
        self.assertFalse(analysis.validate_archive(arrays, config, 'test')['time_semantics']['strict_future_target_start_contract'])
        arrays['y_pred'][0, 0, 0] = np.nan
        with self.assertRaisesRegex(ValueError, 'nonfinite'):
            analysis.validate_archive(arrays, config, 'test')
        arrays['y_pred'][0, 0, 0] = 0.
        arrays['origins'][1] = 0
        with self.assertRaisesRegex(ValueError, 'monotonically unique'):
            analysis.validate_archive(arrays, config, 'test')
        arrays['origins'] = np.arange(3)
        arrays['y_true'] = np.zeros((3, 2, 4))
        with self.assertRaisesRegex(ValueError, 'shape'):
            analysis.validate_archive(arrays, config, 'test')

    def test_fixed_example_minus_45_and_display_mean_only(self) -> None:
        """纠错后同一首事件第四步包含 onset；展示均值不影响逐种子数据。"""
        minute = analysis.NS_PER_MINUTE
        cutoffs = np.arange(6)*15*minute
        times = cutoffs[:, None] + np.arange(4)*15*minute
        episode = dict(episode_id=1, onset_ns=60*minute, last_target_ns=60*minute, interval_end_ns=75*minute, eligible=True)
        models, seeds = ['mrg_full', 'tcn_wide', 'agcrn_full'], [2024, 2025, 2026]
        config = dict(models=models, seeds=seeds, expected_horizons=4, step_minutes=15, timezone='America/Los_Angeles',
                      example_origin_before_onset_minutes=45, example_display_policy='display_only', time_index_correction='source_index_correction_within_authorized_analysis')
        loaded = {}
        for model in models:
            for seed_index, seed in enumerate(seeds):
                loaded[(model, seed, 'test')] = dict(origin_cutoff_ns=cutoffs, target_timestamps_ns=times, origins=np.arange(6),
                                                    node_ids=np.array(['a']), y_true=np.ones((6, 4, 1)),
                                                    y_pred=np.ones((6, 4, 1))*(seed_index+1))
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder)
            metadata = analysis.example_tables(loaded, {'test': (np.arange(9)*15*minute, np.ones(9))}, [episode], 2., config, output)
            self.assertEqual(metadata['episode']['episode_id'], 1)
            self.assertEqual(metadata['origin_cutoff_ns'], 15*minute)
            self.assertTrue(metadata['any_fixed_origin_target_in_episode'])
            with (output/'first_example.csv').open() as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual(len(rows), 36)
            self.assertEqual([float(r['y_pred_sum']) for r in rows if r['model']=='mrg_full' and r['horizon_step']=='4'], [1., 2., 3.])
            with (output/'first_example_seed_mean_display_only.csv').open() as stream:
                display = list(csv.DictReader(stream))
            self.assertEqual(len(display), 12)
            self.assertEqual(float(display[0]['y_pred_sum_mean_display_only']), 2.)
            self.assertTrue(all(r['display_only_not_used_for_scoring']=='True' for r in display))


if __name__ == '__main__':
    unittest.main()

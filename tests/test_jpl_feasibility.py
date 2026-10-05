import pandas as pd
from scripts.audit_jpl_feasibility import describe_path, sample_indices, trace_stats
from scripts.probe_jpl_api_metadata import candidate_crosswalk, summarize_page, summarize_trace_page


def test_filename_prefix_is_candidate_not_certified_node():
    item = describe_path('time series data/jpl/Arroyo_Garage_01/1-1-178-817-2018-10-08T20-54-24-215877.csv.gz')
    assert item['candidate_id'] == '1-1-178-817'
    assert item['filename_timestamp'] == '2018-10-08T20:54:24.215877'
    assert sample_indices(1) == [0]
    assert sample_indices(10) == [0, 5, 9]


def test_empty_power_is_not_manufactured_from_current():
    f = pd.DataFrame({'timestamp':['2020-01-01T00:00:00Z','2020-01-01T00:00:05Z'],
                      'Charging Current (A)':[10, 20], 'Power (kW)':[None, None]})
    s = trace_stats(f)
    assert s['fields']['Power (kW)']['numeric_valid'] == 0
    assert s['fields']['Power (kW)']['max'] is None
    assert s['strictly_increasing'] and s['max_gap_seconds'] == 5
    assert s['cumulative_energy_span_kwh'] is None


def test_duplicate_time_and_decreasing_energy_fail_quality_checks():
    f = pd.DataFrame({'timestamp':['2020-01-01T00:00:00Z']*2,
                      'Energy Delivered (kWh)':[1, .5]})
    s = trace_stats(f)
    assert s['timestamp_duplicates'] == 1
    assert not s['strictly_increasing']
    assert not s['cumulative_energy_monotonic']


def test_api_metadata_summary_counts_coverage_without_emitting_ids():
    rows = [
        {'stationID': 'node-a', 'sessionID': 'private-a', 'connectionTime': 't0',
         'disconnectTime': 't1', 'kWhDelivered': 3.0},
        {'stationID': 'node-b', 'sessionID': 'private-b', 'connectionTime': 't2',
         'disconnectTime': 't3', 'kWhDelivered': 4.0},
    ]
    summary = summarize_page(rows)
    assert summary['record_count'] == 2
    assert summary['distinct_station_ids_in_page'] == 2
    assert summary['nonnull_field_counts']['kWhDelivered'] == 2
    assert 'private-a' not in repr(summary)
    summary.pop('station_ids_internal')
    assert 'private-a' not in repr(summary)


def test_api_trace_summary_reports_shapes_but_not_measurements():
    payload = {'_items': [{'chargingCurrent': [10.0, 11.0], 'pilotSignal': None,
                           'connectionTime': 't0', 'disconnectTime': 't1'}]}
    summary = summarize_trace_page(payload)
    assert summary['record_count'] == 1
    assert summary['records_with_chargingCurrent'] == 1
    assert summary['sample_trace_shapes']['chargingCurrent']['length'] == 2
    assert '10.0' not in repr(summary)


def test_candidate_crosswalk_is_explicitly_only_identifier_overlap():
    result = candidate_crosswalk({'a', 'b', 'c'}, {'b', 'c', 'd'})
    assert result['matching_identifier_count'] == 2
    assert result['static_candidates_not_seen_in_api_sample'] == 1
    assert result['api_sample_ids_not_in_static_candidates'] == 1
    assert 'not a physical EVSE' in result['interpretation']

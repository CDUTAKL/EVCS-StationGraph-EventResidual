"""SG-EXP-026 synthetic shadow-plan smoke evidence; no real dispatch benefit."""
from pathlib import Path
import itertools
from analyze_demand_warning import write_json, sha256_file
from evcs_station_graph.evaluation.charging_decision import ChargingJob, plan_charging

ROOT = Path(__file__).resolve().parents[1]


def main():
    out = ROOT/'outputs/analysis/SG-EXP-026-charging-decision'
    if out.exists():
        raise FileExistsError(out)
    parameters = dict(inelastic_kw=[1]*4, noncharging_kw=[1]*4, capacity_kw=[6]*4,
                      reserve_kw=[1]*4, price_per_kwh=[4,3,2,1])
    job = ChargingJob('synthetic_A', 0, 4, 1, 3)
    demo = plan_charging(**parameters, jobs=[job], scenario=True)
    # Independent enumeration on an integer-kW toy grid, not reuse LP constraints.
    candidates = [(sum(p*c*.25 for p, c in zip(power, parameters['price_per_kwh'])), power)
                  for power in itertools.product(range(4), repeat=4) if sum(power) == 4]
    optimum, _ = min(candidates)
    assert abs(demo['planned_cost']-optimum) < 1e-12
    actual_case = plan_charging(inelastic_kw=None, noncharging_kw=None, capacity_kw=None,
                               reserve_kw=None, price_per_kwh=None, jobs=None)
    assert actual_case['status'] == 'MATERIALS_REQUIRED'
    out.mkdir(parents=True)
    write_json(out/'synthetic_parameters.json', dict(**parameters, jobs=[job.__dict__], interval_hours=.25,
                                                   source='invented unit-test scenario; price is arbitrary accounting units, not a real tariff'))
    write_json(out/'shadow_plan.json', demo)
    write_json(out/'actual_thesis_case_status.json', actual_case)
    write_json(out/'audit.json', dict(status='PASS_SYNTHETIC_ONLY', enumeration_optimum=optimum,
                                     observed_dispatch_savings=None, closed_loop_simulation=False,
                                     prediction_changes=False, actuator_commands_sent=False))
    write_json(out/'sources.json', {str(p.relative_to(ROOT)): sha256_file(p) for p in
                                   [Path(__file__), ROOT/'src/evcs_station_graph/evaluation/charging_decision.py']})
    write_json(out/'manifest.json', {p.name: sha256_file(p) for p in out.iterdir()})
    print(demo, actual_case)


if __name__ == '__main__':
    main()

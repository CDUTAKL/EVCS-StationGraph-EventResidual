"""Shadow-only finite-horizon energy allocation; never sends charger commands.

Forecast of total uncontrolled charging is NOT an inelastic baseline: using it
alongside the same vehicles' requests would double count demand. A separately
identified uncontrollable baseline and validated measurement mapping are required.
"""
from dataclasses import dataclass
import numpy as np
from scipy.optimize import linprog


@dataclass(frozen=True)
class ChargingJob:
    name: str
    release_step: int
    deadline_step: int  # exclusive; request must be entirely inside this horizon
    remaining_kwh: float
    max_kw: float


def plan_charging(*, inelastic_kw, noncharging_kw, capacity_kw, reserve_kw,
                  price_per_kwh, jobs, measurement_mapping_validated=False,
                  scenario=False, interval_hours=.25):
    """Minimize energy cost while meeting every job, or explicitly refuse.

    Ideal, lossless, continuously variable charging. No export, V2G, network
    voltage constraints, integer pilots, or actuator control. Incomplete inputs
    are not converted into arbitrary defaults. Cost is planned, not realized.
    """
    if not scenario and not measurement_mapping_validated:
        return dict(status='MATERIALS_REQUIRED', reason='Unvalidated proxy-to-meter mapping', executable=False)
    if jobs is None or any(v is None for v in (inelastic_kw, noncharging_kw, capacity_kw, reserve_kw, price_per_kwh)):
        return dict(status='MATERIALS_REQUIRED', reason='Missing load, capacity, reserve, tariff, or vehicle constraints', executable=False)
    arrays = [np.asarray(v, float) for v in (inelastic_kw, noncharging_kw, capacity_kw, reserve_kw, price_per_kwh)]
    if any(a.ndim != 1 for a in arrays) or len({len(a) for a in arrays}) != 1 or not len(arrays[0]):
        raise ValueError('All time series must have identical nonempty one-dimensional shapes')
    if any(not np.isfinite(a).all() for a in arrays) or any(np.any(a < 0) for a in arrays[:4]):
        raise ValueError('Nonfinite or negative physical input')
    if not np.isfinite(interval_hours) or interval_hours <= 0:
        raise ValueError('Invalid interval duration')
    baseline, other, cap, reserve, price = arrays
    h = len(baseline)
    jobs = list(jobs)
    if len({j.name for j in jobs}) != len(jobs):
        raise ValueError('Duplicate vehicle identifiers')
    for j in jobs:
        if not isinstance(j.release_step, int) or not isinstance(j.deadline_step, int) or not 0 <= j.release_step < j.deadline_step <= h:
            raise ValueError('Job service window must lie within decision horizon')
        if not np.isfinite([j.remaining_kwh, j.max_kw]).all() or min(j.remaining_kwh, j.max_kw) < 0:
            raise ValueError('Invalid job energy/power')
    headroom = cap-reserve-baseline-other
    if np.any(headroom < 0):
        return dict(status='INFEASIBLE_BASELINE', reason='Uncontrollable load already exceeds reserved capacity', executable=False)
    if not jobs:
        return dict(status='NO_FLEXIBLE_REQUESTS', executable=False, planned_cost=0., planned_kw=np.zeros((0, h)).tolist())
    n = len(jobs)
    bounds = [(0, j.max_kw if j.release_step <= k < j.deadline_step else 0) for j in jobs for k in range(h)]
    service = np.zeros((n, n*h))
    station = np.zeros((h, n*h))
    for i in range(n):
        service[i, i*h:(i+1)*h] = interval_hours
        station[:, i*h:(i+1)*h] = np.eye(h)
    r = linprog(np.tile(price*interval_hours, n), A_ub=station, b_ub=headroom,
                A_eq=service, b_eq=[j.remaining_kwh for j in jobs], bounds=bounds, method='highs')
    if not r.success:
        return dict(status='INFEASIBLE_SERVICE' if r.status == 2 else 'SOLVER_FAILURE', reason=r.message, executable=False)
    schedule = r.x.reshape(n, h)
    delivered = schedule.sum(axis=1)*interval_hours
    total = schedule.sum(axis=0)+baseline+other
    if np.max(np.abs(delivered-[j.remaining_kwh for j in jobs])) > 1e-7 or np.any(total+reserve > cap+1e-7):
        raise RuntimeError('Solver solution failed independent constraint check')
    return dict(status='SHADOW_PLAN_SCENARIO' if scenario else 'SHADOW_PLAN_VALIDATED_INPUTS', executable=False,
                planned_kw=schedule.tolist(), delivered_kwh=delivered.tolist(), total_kw=total.tolist(),
                planned_cost=float(r.fun), minimum_reserved_headroom_kw=float(np.min(cap-reserve-total)),
                realized_savings=None, caveat='Idealized shadow plan, not commands or demonstrated dispatch benefit')

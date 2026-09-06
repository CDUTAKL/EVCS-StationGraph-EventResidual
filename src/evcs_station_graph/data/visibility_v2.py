"""Versioned event-time replay, NOT a claim about unobserved telemetry latency.

Grid timestamps are UTC bin starts. Input row k includes events strictly before
grid[k]+15min; an event exactly at the right boundary belongs to the next bin.
Final energy is used ONLY in offline labels. No ingestion timestamps exist in
the source: connections/disconnections are assumed available at event time.
"""
import numpy as np
import pandas as pd

STEP = 15 * 60 * 10**9
FEATURE_NAMES = ('access_count', 'departure_count', 'active_count',
                 'local_hour_sin', 'local_hour_cos', 'local_weekday_sin', 'local_weekday_cos')


def _grid(grid):
    g = np.asarray(grid, dtype=np.int64)
    if g.ndim != 1 or not len(g) or (len(g) > 1 and not np.all(np.diff(g) == STEP)):
        raise ValueError('Expected nonempty consecutive 15min UTC grid')
    return g


def event_features(frame, grid, nodes):
    """Use independent observed event streams; censored disconnects are allowed.

    Never drop a connection because its final energy/end is missing: that would
    itself make an input depend on future completion. active_count is the
    left-limit active state at each bin end, not the old overlap-count feature.
    """
    g = _grid(grid)
    if len(nodes) != len(set(nodes)):
        raise ValueError('Duplicate nodes')
    x = np.zeros((len(g), len(nodes), 7), dtype=np.float32)
    base = np.zeros(len(nodes), dtype=np.int64)
    for n, node in enumerate(nodes):
        sub = frame.loc[frame.spaceID.astype(str) == node]
        for col, channel, sign in [('connectionTime', 0, 1), ('disconnectTime', 1, -1)]:
            times = pd.to_datetime(sub[col], utc=True).dropna().astype('int64').to_numpy()
            base[n] += sign * np.count_nonzero(times < g[0])
            bins = (times - g[0]) // STEP
            bins = bins[(bins >= 0) & (bins < len(g))]
            x[:, n, channel] = np.bincount(bins, minlength=len(g))
    x[:, :, 2] = base + np.cumsum(x[:, :, 0] - x[:, :, 1], axis=0)
    if np.any(x[:, :, 2] < 0):
        raise ValueError('Negative active state: incomplete or inconsistent event history')
    local = pd.to_datetime(g + STEP, utc=True).tz_convert('America/Los_Angeles')
    hour = np.asarray(local.hour + local.minute / 60)
    day = np.asarray(local.dayofweek)
    for i, vals in enumerate((np.sin(2*np.pi*hour/24), np.cos(2*np.pi*hour/24),
                              np.sin(2*np.pi*day/7), np.cos(2*np.pi*day/7)), 3):
        x[:, :, i] = vals[:, None]
    return x


def proxy_targets(frame, grid, nodes):
    """Legacy-compatible equal-bin allocation plus final-label availability.

    A zero-duration session creates events but no proxy energy, as in legacy
    reconstruction. Caller must audit count/energy of these cases explicitly.
    """
    g = _grid(grid)
    y = np.zeros((len(g), len(nodes)), dtype=np.float64)
    maturity = np.broadcast_to(g[:, None] + STEP - 1, y.shape).copy()
    node_index = {node: i for i, node in enumerate(nodes)}
    for row in frame.itertuples(index=False):
        if str(row.spaceID) not in node_index:
            continue
        c = pd.Timestamp(row.connectionTime).value
        d = pd.Timestamp(row.disconnectTime).value
        energy = float(row.kWhDelivered)
        if pd.isna(row.disconnectTime) or not np.isfinite(energy) or energy < 0 or d < c:
            raise ValueError('Invalid offline label record')
        if d == c:
            continue
        lo = (c - g[0]) // STEP
        hi = (d - g[0] + STEP - 1) // STEP
        start, end = max(0, lo), min(len(g), hi)
        n = node_index[str(row.spaceID)]
        if start < end:
            y[start:end, n] += energy / (hi-lo)
            maturity[start:end, n] = np.maximum(maturity[start:end, n], d)
    return y, maturity


def mature_prefix_end(maturity, grid, boundary):
    """Exclusive contiguous train-fit end; no incomplete session labels in fit."""
    g = _grid(grid)
    cutoff = g[boundary] if boundary < len(g) else g[-1] + STEP
    bad = np.flatnonzero(np.any(maturity[:boundary] >= cutoff, axis=1))
    return int(bad[0]) if len(bad) else int(boundary)


def safe_origins(grid, maturity, start, end, history=96, horizon=4):
    """All X/Y bins inside one segment, all Y finalized before segment cutoff."""
    g = _grid(grid)
    if not 0 <= start < end <= len(g) or history < 1 or horizon < 1:
        raise ValueError('Invalid segment/window')
    origins = np.arange(start+history-1, end-horizon, dtype=np.int64)
    cutoff = g[end] if end < len(g) else g[-1]+STEP
    good = np.ones(len(origins), dtype=bool)
    for h in range(1, horizon+1):
        good &= np.all(maturity[origins+h] < cutoff, axis=1)
    return origins[good]


def fit_preprocessing(x, y, fit_end):
    if fit_end < 2 or fit_end > len(x) or fit_end > len(y):
        raise ValueError('Invalid fit prefix')
    xf, yf = x[:fit_end].astype(np.float64), y[:fit_end].astype(np.float64)
    if not np.isfinite(xf).all() or not np.isfinite(yf).all():
        raise ValueError('Nonfinite fit data')
    delta = np.abs(np.diff(xf[:, :, 2], axis=0, prepend=xf[[0], :, 2]))
    rule_components = np.stack([xf[:, :, 0], xf[:, :, 1], delta], axis=-1)
    yd = np.abs(np.diff(yf, axis=0, prepend=yf[[0]]))
    positive = yd[yd > 0]
    return {
        'feature_mean': xf.mean(axis=(0, 1)),
        'feature_std': np.where(xf.std(axis=(0, 1)) < 1e-6, 1., xf.std(axis=(0, 1))),
        'target_mean': yf.mean(axis=0),
        'target_std': np.where(yf.std(axis=0) < 1e-6, 1., yf.std(axis=0)),
        'rule_std': np.maximum(rule_components.std(axis=0), 1e-8),
        'label_jump_threshold': np.array(np.quantile(positive, .9) if len(positive) else np.inf),
    }


def rule_scores(x, rule_std):
    delta = np.abs(np.diff(x[:, :, 2], axis=0, prepend=x[[0], :, 2]))
    components = np.stack([x[:, :, 0], x[:, :, 1], delta], axis=-1)
    return (components / rule_std).sum(axis=-1)


def apply_rule(scores, thresholds, extension=2):
    if extension < 0:
        raise ValueError('Negative extension')
    points = (scores >= thresholds) & (scores > 0)
    result = points.copy()
    for offset in range(1, extension+1):
        result[offset:] |= points[:-offset]
    return result

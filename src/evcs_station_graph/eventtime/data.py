"""Strict frozen asset loader; raw records and legacy TensorBundle are not read."""
import hashlib
from pathlib import Path

import numpy as np
from torch.utils.data import Dataset

DATA_SHA256 = 'f663b510c75e203c8150f57c3765645f92b9a941e0745227c6ea078008a0dc8f'
FEATURES = ('access_count', 'departure_count', 'active_count', 'local_hour_sin',
            'local_hour_cos', 'local_weekday_sin', 'local_weekday_cos')
SEGMENTS = {'train': (0, 83198), 'tuning': (83198, 92101),
            'calibration': (92101, 101005), 'test': (101005, 118818)}


def sha256(path):
    with open(path, 'rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


class FrozenData:
    def __init__(self, path):
        self.path = Path(path)
        self.digest = sha256(path)
        if self.digest != DATA_SHA256:
            raise ValueError('Frozen dataset SHA256 mismatch; legacy or modified data refused')
        with np.load(path, allow_pickle=False) as f:
            self.arrays = {k: f[k] for k in f.files}
        a = self.arrays
        if str(a['schema']) != 'eventtime-v1-not-legacy-TensorBundle' or tuple(a['feature_names']) != FEATURES:
            raise ValueError('Feature/schema contract mismatch')
        if a['features'].shape != (118818, 10, 7) or a['targets'].shape != (118818, 10):
            raise ValueError('Frozen shape mismatch')
        if not np.isfinite(a['features']).all() or not np.isfinite(a['targets']).all():
            raise ValueError('Nonfinite data')
        if np.any(a['feature_std'] <= 0) or np.any(a['target_std'] <= 0):
            raise ValueError('Invalid train-only scalers')
        for split, (lo, hi) in SEGMENTS.items():
            k = a[split+'_origins']
            if np.any(k-95 < lo) or np.any(k+4 >= hi) or np.any(np.diff(k) <= 0):
                raise ValueError(f'Invalid split origins: {split}')
            end_ns = int(a['timestamps_ns'][hi-1]) + 900_000_000_000
            for step in range(1, 5):
                if np.any(a['label_available_at_ns'][k+step] >= end_ns):
                    raise ValueError(f'Immature labels: {split}')
        self.x = ((a['features']-a['feature_mean'])/a['feature_std']).astype('float32')
        self.y = ((a['targets']-a['target_mean'])/a['target_std']).astype('float32')

    def windows(self, split, limit=None):
        return Windows(self, split, limit)

    def masks(self, origins):
        idx = origins[:, None] + np.arange(1, 5)[None, :]
        target = self.arrays['target_event'][idx]
        trigger = np.repeat(self.arrays['rule_trigger'][origins, None, :], 4, axis=1)
        return target, trigger


class Windows(Dataset):
    def __init__(self, data, split, limit=None):
        self.data = data
        origins = data.arrays[split+'_origins']
        self.origins = origins if limit is None else origins[:limit]

    def __len__(self):
        return len(self.origins)

    def __getitem__(self, i):
        k = int(self.origins[i])
        return self.data.x[k-95:k+1], self.data.y[k+1:k+5], k

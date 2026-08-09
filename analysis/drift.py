import numpy as np

class AdvancedDriftMonitor:
    @staticmethod
    def calculate_psi(reference: np.ndarray, target: np.ndarray, num_buckets: int = 10) -> float:
        reference = reference[~np.isnan(reference)]
        target = target[~np.isnan(target)]
        if len(reference) == 0 or len(target) == 0:
            return 0.0

        percentiles = np.linspace(0, 100, num_buckets + 1)
        buckets = np.percentile(reference, percentiles)
        buckets[0] -= 1e-5
        buckets[-1] += 1e-5

        ref_counts, _ = np.histogram(reference, bins=buckets)
        tar_counts, _ = np.histogram(target, bins=buckets)

        ref_perc = np.where(ref_counts / len(reference) == 0, 1e-4, ref_counts / len(reference))
        tar_perc = np.where(tar_counts / len(target) == 0, 1e-4, tar_counts / len(target))

        return float(np.sum((tar_perc - ref_perc) * np.log(tar_perc / ref_perc)))
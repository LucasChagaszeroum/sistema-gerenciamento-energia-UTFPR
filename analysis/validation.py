import numpy as np
import scipy.stats as stats

def diebold_mariano_test(real: np.ndarray, pred1: np.ndarray, pred2: np.ndarray) -> float:
    e1 = real - pred1
    e2 = real - pred2
    d = e1**2 - e2**2
    mean_d = np.mean(d)
    var_d = np.var(d, ddof=1)
    DM_stat = mean_d / np.sqrt((var_d / len(d)) + 1e-8)
    return float(2 * (1 - stats.norm.cdf(abs(DM_stat))))

def cohens_d(x: np.ndarray, y: np.ndarray) -> float:
    nx, ny = len(x), len(y)
    dof = nx + ny - 2
    pooled_std = np.sqrt(((nx - 1) * np.std(x, ddof=1)**2 + (ny - 1) * np.std(y, ddof=1)**2) / dof)
    return float((np.mean(x) - np.mean(y)) / (pooled_std + 1e-8))
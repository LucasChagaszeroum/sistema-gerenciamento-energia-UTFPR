import numpy as np
from sklearn.base import clone
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import mean_absolute_error
from sklearn.ensemble import RandomForestRegressor
import xgboost as xgb
import lightgbm as lgb

class EnsembleModelPipeline:
    def __init__(self, seed: int = 42):
        self.models = {
            'XGBoost': xgb.XGBRegressor(random_state=seed, n_estimators=100),
            'LightGBM': lgb.LGBMRegressor(random_state=seed, n_estimators=100, verbose=-1),
            'RandomForest': RandomForestRegressor(random_state=seed, n_estimators=50)
        }
        self.weights = {}

    def fit_predict_ensemble(self, X_tr, y_tr, X_te):
        tscv = TimeSeriesSplit(n_splits=3)
        scores_mae = {m: [] for m in self.models}

        for train_cv, val_cv in tscv.split(X_tr):
            for name, model in self.models.items():
                m_fold = clone(model)
                m_fold.fit(X_tr[train_cv], y_tr[train_cv])
                preds_val = m_fold.predict(X_tr[val_cv])
                scores_mae[name].append(mean_absolute_error(y_tr[val_cv], preds_val))

        inv_errors = {m: np.exp(-np.mean(scores_mae[m])) for m in self.models}
        total_inv = sum(inv_errors.values())
        self.weights = {m: inv_errors[m] / total_inv for m in inv_errors}

        preds_dict = {}
        for name, model in self.models.items():
            model.fit(X_tr, y_tr)
            preds_dict[name] = model.predict(X_te)

        preds_dict['Ensemble_Weighted'] = sum(preds_dict[m] * self.weights[m] for m in self.models)
        return preds_dict
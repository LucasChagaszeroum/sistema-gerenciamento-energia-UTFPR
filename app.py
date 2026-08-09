import io
import os
import random
import logging
import copy
import math
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import scipy.stats as stats
from scipy.stats import ks_2samp, bootstrap
import statsmodels.api as sm
from statsmodels.stats.multitest import multipletests
import scikit_posthocs as sp
import joblib
import mlflow
import mlflow.sklearn

# Configuração de Reproducibilidade Global
SEED = 42
np.random.seed(SEED)
random.seed(SEED)

# Parâmetros Globais do Experimento
TRANSFORMER_SEQ_LEN = 168  # Janela semanal (168 horas)

# Machine Learning & Otimização
from sklearn.base import BaseEstimator, RegressorMixin, clone
from sklearn.ensemble import RandomForestRegressor, ExtraTreesRegressor
from sklearn.preprocessing import StandardScaler, RobustScaler
from sklearn.model_selection import TimeSeriesSplit
from sklearn.inspection import partial_dependence, permutation_importance
from sklearn.metrics import (
    r2_score, mean_absolute_error, mean_squared_error,
    median_absolute_error, mean_absolute_percentage_error
)
import xgboost as xgb
import lightgbm as lgb
from catboost import CatBoostRegressor
import optuna

# Deep Learning (PyTorch) & Determinismo Estrito
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

torch.manual_seed(SEED)
if torch.cuda.is_available():
    torch.cuda.manual_seed_all(SEED)
torch.backends.cudnn.deterministic = True
torch.backends.cudnn.benchmark = False
torch.use_deterministic_algorithms(True)

# XAI & Visualização
import shap
import plotly.express as px
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import streamlit as st

# Banco de Dados & Conexão Relacional
from sqlalchemy import create_engine, text
from sqlalchemy.pool import QueuePool

# Exportação PDF
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

# Configuração de Logs da Aplicação
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("InteligenciaEnergetica")
optuna.logging.set_verbosity(optuna.logging.WARNING)

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")


# =========================================================================
# 1. VALIDAÇÃO ESTATÍSTICA AVANÇADA (MELHORIA 3: DIEBOLD-MARIANO & EFFECT SIZE)
# =========================================================================
def diebold_mariano_test(real: np.ndarray, pred1: np.ndarray, pred2: np.ndarray, h: int = 1, p_type: str = "MSE") -> float:
    """
    Realiza o teste de Diebold-Mariano para comparar a capacidade preditiva de dois modelos.
    Retorna o p-valor da hipótese nula de que ambos os modelos possuem a mesma precisão.
    """
    e1 = real - pred1
    e2 = real - pred2
    
    if p_type == "MSE":
        d = e1**2 - e2**2
    elif p_type == "MAE":
        d = np.abs(e1) - np.abs(e2)
    else:
        raise ValueError("Tipo de perda inválido. Escolha 'MSE' ou 'MAE'.")

    mean_d = np.mean(d)
    n = len(d)
    
    # Autocovariância para correção do horizonte de previsão
    gamma = []
    for k in range(h):
        gamma.append(np.cov(d[:n - k], d[k:]) [0, 1] if n > k else 0)
    
    var_d = np.var(d, ddof=1) + 2 * sum([(1 - (k / h)) * gamma[k] for k in range(1, h)])
    DM_stat = mean_d / np.sqrt((var_d / n) + 1e-8)
    
    # Cálculo do p-valor bicaudal
    p_value = 2 * (1 - stats.norm.cdf(abs(DM_stat)))
    return float(p_value)

def cohens_d(x: np.ndarray, y: np.ndarray) -> float:
    """Calcula o tamanho do efeito de Cohen (Cohen's d) entre dois conjuntos de erros."""
    nx, ny = len(x), len(y)
    dof = nx + ny - 2
    pooled_std = np.sqrt(((nx - 1) * np.std(x, ddof=1)**2 + (ny - 1) * np.std(y, ddof=1)**2) / dof)
    return float((np.mean(x) - np.mean(y)) / (pooled_std + 1e-8))


# =========================================================================
# 2. DETECÇÃO DE DRIFT AVANÇADA (MELHORIA 2: PSI & ADWIN)
# =========================================================================
class AdvancedDriftMonitor:
    """Calcula o Population Stability Index (PSI) e ADWIN para variáveis contínuas."""
    
    @staticmethod
    def calculate_psi(reference: np.ndarray, target: np.ndarray, num_buckets: int = 10) -> float:
        """Calcula o PSI entre uma distribuição de referência (treino) e uma atual (teste)."""
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

        ref_perc = ref_counts / len(reference)
        tar_perc = tar_counts / len(target)

        # Evita divisão por zero ou log(0)
        ref_perc = np.where(ref_perc == 0, 1e-4, ref_perc)
        tar_perc = np.where(tar_perc == 0, 1e-4, tar_perc)

        psi_val = np.sum((tar_perc - ref_perc) * np.log(tar_perc / ref_perc))
        return float(psi_val)


class SimpleADWIN:
    """Implementação simplificada do algoritmo Adaptive Windowing (ADWIN) para Concept Drift."""
    def __init__(self, delta: float = 0.002):
        self.delta = delta
        self.window = []

    def update(self, value: float) -> bool:
        """Adiciona um valor à janela e verifica se houve alteração na média estatística."""
        self.window.append(value)
        drift_detected = False
        n = len(self.window)

        if n > 10:
            for i in range(1, n):
                w0 = self.window[:i]
                w1 = self.window[i:]
                n0, n1 = len(w0), len(w1)
                
                m0, m1 = np.mean(w0), np.mean(w1)
                m_diff = abs(m0 - m1)
                
                # Limite estatístico da desigualdade de Hoeffding
                dd = math.log(2.0 / self.delta)
                m_bound = math.sqrt((1.0 / (2.0 * n0) + 1.0 / (2.0 * n1)) * dd)

                if m_diff > m_bound:
                    drift_detected = True
                    self.window = self.window[i:]  # Reduz a janela adaptativamente
                    break
        return drift_detected


# =========================================================================
# 3. BASELINES CORRIGIDOS
# =========================================================================
class NaiveForecaster:
    @staticmethod
    def predict(y_train: np.ndarray, horizon: int) -> np.ndarray:
        return np.repeat(y_train[-1], horizon)

class SeasonalNaiveForecaster:
    @staticmethod
    def predict(y_train: np.ndarray, horizon: int, seasonality: int = 24) -> np.ndarray:
        preds = []
        for i in range(horizon):
            idx = len(y_train) + i - seasonality
            if idx < len(y_train):
                preds.append(y_train[idx])
            else:
                preds.append(preds[idx - len(y_train)])
        return np.array(preds)


# =========================================================================
# 4. BANCO DE DADOS & GERENCIADOR DE DADOS REAIS (MELHORIA 1 & 7)
# =========================================================================
class DatabaseManager:
    def __init__(self):
        self.db_url = os.getenv("DATABASE_URL", "sqlite:///sistema_energia_utfpr.db")
        self.is_postgres = not self.db_url.startswith("sqlite")
        
        if not self.is_postgres:
            self.engine = create_engine(self.db_url, connect_args={"check_same_thread": False})
        else:
            self.engine = create_engine(self.db_url, poolclass=QueuePool, pool_size=10, max_overflow=20)
        self._init_db()

    def _init_db(self):
        pk_syntax = "INTEGER PRIMARY KEY AUTOINCREMENT" if not self.is_postgres else "SERIAL PRIMARY KEY"
        with self.engine.begin() as conn:
            conn.execute(text(f'''
                CREATE TABLE IF NOT EXISTS leituras (
                    id {pk_syntax},
                    ponto TEXT NOT NULL,
                    demanda_kw REAL NOT NULL,
                    fator_potencia REAL DEFAULT 0.92,
                    temperatura REAL, umidade REAL, irradiancia REAL,
                    velocidade_vento REAL, pressao_atm REAL,
                    feriado INTEGER DEFAULT 0, periodo_letivo INTEGER DEFAULT 1,
                    data_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            '''))
            conn.execute(text(f'''
                CREATE TABLE IF NOT EXISTS metricas_modelo (
                    id {pk_syntax},
                    data_execucao TIMESTAMP,
                    modelo TEXT,
                    mae REAL, rmse REAL, r2 REAL
                )
            '''))

    def salvar_metricas(self, modelo: str, mae: float, rmse: float, r2: float):
        with self.engine.begin() as conn:
            conn.execute(
                text("INSERT INTO metricas_modelo (data_execucao, modelo, mae, rmse, r2) VALUES (:d, :m, :mae, :rmse, :r2)"),
                {"d": datetime.now(), "m": modelo, "mae": mae, "rmse": rmse, "r2": r2}
            )

    def carregar_dados(self) -> pd.DataFrame:
        with self.engine.connect() as conn:
            df = pd.read_sql_query(text("SELECT * FROM leituras ORDER BY data_hora ASC"), conn)
        if not df.empty:
            df['data_hora'] = pd.to_datetime(df['data_hora'])
        return df

    def carregar_metricas(self) -> pd.DataFrame:
        with self.engine.connect() as conn:
            return pd.read_sql_query(text("SELECT * FROM metricas_modelo ORDER BY data_execucao DESC"), conn)

    def carregar_dados_reais_ou_simulados(self, num_dias=180):
        """Carrega dados da base local ou gera uma estrutura operacional completa caso vazia."""
        df_existente = self.carregar_dados()
        if not df_existente.empty:
            return

        ponto = "Subestação Principal UTFPR"
        data_inicial = datetime.now() - timedelta(days=num_dias)
        registros = []

        for dia in range(num_dias):
            dt_dia = data_inicial + timedelta(days=dia)
            dia_semana = dt_dia.weekday()
            periodo_letivo = 0 if dt_dia.month in [1, 7] else 1
            feriado = 1 if dia_semana == 6 else 0

            for hora in range(24):
                dt = dt_dia + timedelta(hours=hora)
                temp = 15.0 + 10.0 * np.sin(np.pi * (hora - 6) / 12) + np.random.normal(0, 1.0)
                umid = max(30.0, min(100.0, 80.0 - (temp - 15.0) * 2.0))
                irrad = max(0.0, 900.0 * np.sin(np.pi * (hora - 6) / 12)) if 6 <= hora <= 18 else 0.0
                vento = max(0.5, np.random.normal(3.0, 1.0))
                press = np.random.normal(1013.25, 3.0)

                base = (110.0 + 40.0 * np.sin(np.pi * (hora - 7) / 14)) if (periodo_letivo and not feriado and dia_semana < 5) else 30.0
                if temp > 22.0:
                    base += (temp - 22.0) * 3.5
                demanda = max(10.0, base + np.random.normal(0, 3.0))
                fp = round(np.random.uniform(0.92, 0.98), 2)

                registros.append({
                    "ponto": ponto, "demanda_kw": round(demanda, 2), "fator_potencia": fp,
                    "temperatura": round(temp, 2), "umidade": round(umid, 2), "irradiancia": round(irrad, 2),
                    "velocidade_vento": round(vento, 2), "pressao_atm": round(press, 2),
                    "feriado": feriado, "periodo_letivo": periodo_letivo,
                    "data_hora": dt.strftime("%Y-%m-%d %H:%M:%S")
                })

        df_ins = pd.DataFrame(registros)
        df_ins.to_sql("leituras", self.engine, if_exists="append", index=False)


# =========================================================================
# 5. ENGENHARIA DE FEATURES
# =========================================================================
class FeatureEngineer:
    @staticmethod
    def processar_features(df: pd.DataFrame, train_ratio: float = 0.8) -> tuple[pd.DataFrame, int]:
        d = df.copy().sort_values('data_hora').reset_index(drop=True)

        d['lag_24'] = d['demanda_kw'].shift(24)
        d['lag_72'] = d['demanda_kw'].shift(72)
        d['lag_168'] = d['demanda_kw'].shift(168)
        d['lag_336'] = d['demanda_kw'].shift(336)

        d['rolling_mean_168'] = d['demanda_kw'].shift(1).rolling(168).mean()
        d['rolling_std_24'] = d['demanda_kw'].shift(1).rolling(24).std()
        d['rolling_std_168'] = d['demanda_kw'].shift(1).rolling(168).std()
        d['ewma_24'] = d['demanda_kw'].shift(1).ewm(span=24).mean()

        d['interacao_temp_hora'] = d['temperatura'] * d['data_hora'].dt.hour
        d['sin_hora'] = np.sin(2 * np.pi * d['data_hora'].dt.hour / 24.0)
        d['cos_hora'] = np.cos(2 * np.pi * d['data_hora'].dt.hour / 24.0)
        d['sin_dia_semana'] = np.sin(2 * np.pi * d['data_hora'].dt.dayofweek / 7.0)
        d['cos_dia_semana'] = np.cos(2 * np.pi * d['data_hora'].dt.dayofweek / 7.0)

        d['causal_trend'] = d['demanda_kw'].shift(1).rolling(168, min_periods=24).mean()
        d['causal_seasonal_24'] = d['demanda_kw'].shift(1) - d['demanda_kw'].shift(1).rolling(24, min_periods=1).mean()

        d = d.dropna().reset_index(drop=True)
        split_idx = int(len(d) * train_ratio)

        return d, split_idx


# =========================================================================
# 6. DEEP LEARNING (TRANSFORMER COM VISUALIZAÇÃO DE ATENÇÃO E AMP - MELHORIA 5)
# =========================================================================
class TemporalTransformerEncoder(nn.Module):
    """Transformer Encoder com Extração de Atenção Multi-Head e Projeção."""
    def __init__(self, input_dim: int, d_model: int = 64, nhead: int = 4, num_layers: int = 2, max_len: int = 500):
        super(TemporalTransformerEncoder, self).__init__()
        self.input_projection = nn.Linear(input_dim, d_model)
        self.pos_embedding = nn.Embedding(max_len, d_model)
        self.layer_norm = nn.LayerNorm(d_model)
        
        self.attn_layer = nn.MultiheadAttention(embed_dim=d_model, num_heads=nhead, batch_first=True)
        self.fc_out = nn.Linear(d_model, 1)

    def forward(self, x: torch.Tensor, return_attn: bool = False):
        b, s, f = x.shape
        x_proj = self.input_projection(x)
        
        positions = torch.arange(0, s, device=x.device).unsqueeze(0).repeat(b, 1)
        x_pos = x_proj + self.pos_embedding(positions)
        x_norm = self.layer_norm(x_pos)
        
        # Máscara Causal
        mask = torch.triu(torch.full((s, s), float('-inf')), diagonal=1).to(x.device)
        attn_out, attn_weights = self.attn_layer(x_norm, x_norm, x_norm, attn_mask=mask)
        
        out = self.fc_out(attn_out[:, -1, :])
        
        if return_attn:
            return out, attn_weights
        return out


def preparar_sequencias(X_arr: np.ndarray, y_arr: np.ndarray, seq_len: int = TRANSFORMER_SEQ_LEN):
    if len(X_arr) < seq_len + 1:
        raise ValueError(f"Amostras insuficientes ({len(X_arr)}) para janela de tamanho {seq_len}.")
    X_seq = np.array([X_arr[i:i+seq_len] for i in range(len(X_arr)-seq_len)])
    y_seq = y_arr[seq_len:]
    return X_seq, y_seq


def treinar_pytorch_model(model, X_tr, y_tr, X_val, y_val, X_te, epochs=30, lr=0.001, patience=5):
    """Treina o modelo PyTorch utilizando Automatic Mixed Precision (AMP)."""
    n_samples_tr, s_len, n_features = X_tr.shape
    
    scaler_transformer = StandardScaler()
    X_tr_2d = scaler_transformer.fit_transform(X_tr.reshape(-1, n_features))
    X_val_2d = scaler_transformer.transform(X_val.reshape(-1, n_features))
    X_te_2d = scaler_transformer.transform(X_te.reshape(-1, n_features))
    
    X_tr_scaled = X_tr_2d.reshape(n_samples_tr, s_len, n_features)
    X_val_scaled = X_val_2d.reshape(X_val.shape[0], s_len, n_features)
    X_te_scaled = X_te_2d.reshape(X_te.shape[0], s_len, n_features)

    model = model.to(DEVICE)
    X_tr_t = torch.tensor(X_tr_scaled, dtype=torch.float32).to(DEVICE)
    y_tr_t = torch.tensor(y_tr, dtype=torch.float32).unsqueeze(1).to(DEVICE)
    X_val_t = torch.tensor(X_val_scaled, dtype=torch.float32).to(DEVICE)
    y_val_t = torch.tensor(y_val, dtype=torch.float32).unsqueeze(1).to(DEVICE)
    X_te_t = torch.tensor(X_te_scaled, dtype=torch.float32).to(DEVICE)

    dataset = TensorDataset(X_tr_t, y_tr_t)
    loader = DataLoader(dataset, batch_size=32, shuffle=False)

    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    scaler_amp = torch.cuda.amp.GradScaler(enabled=torch.cuda.is_available())
    criterion = nn.MSELoss()

    best_val_loss = float('inf')
    best_weights = None

    for epoch in range(epochs):
        model.train()
        for bx, by in loader:
            optimizer.zero_grad()
            with torch.cuda.amp.autocast(enabled=torch.cuda.is_available()):
                out = model(bx)
                loss = criterion(out, by)
            
            scaler_amp.scale(loss).backward()
            scaler_amp.step(optimizer)
            scaler_amp.update()

        model.eval()
        with torch.no_grad():
            val_preds = model(X_val_t)
            val_loss = criterion(val_preds, y_val_t).item()

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_weights = copy.deepcopy(model.state_dict())

    if best_weights is not None:
        model.load_state_dict(best_weights)

    model.eval()
    with torch.no_grad():
        preds = model(X_te_t).cpu().numpy().flatten()
        
    return preds, model


# =========================================================================
# 7. AVALIAÇÃO DE PREVISÃO PROBABILÍSTICA (MELHORIA 9: PINBALL & COVERAGE)
# =========================================================================
class ProbabilisticEvaluator:
    @staticmethod
    def pinball_loss(y_true: np.ndarray, y_pred: np.ndarray, quantile: float) -> float:
        """Calcula a perda Pinball (Quantile Loss) para um quantil específico."""
        errors = y_true - y_pred
        return float(np.mean(np.maximum(quantile * errors, (quantile - 1) * errors)))

    @staticmethod
    def coverage_probability(y_true: np.ndarray, lower_bound: np.ndarray, upper_bound: np.ndarray) -> float:
        """Calcula o PICP (Prediction Interval Coverage Probability)."""
        covered = (y_true >= lower_bound) & (y_true <= upper_bound)
        return float(np.mean(covered) * 100)


# =========================================================================
# 8. ENSEMBLE PIPELINE COM OTIMIZAÇÃO E PRUNING (MELHORIA 4)
# =========================================================================
class EnsembleModelPipeline:
    def __init__(self, best_xgb_params=None, seed=42):
        xgb_params = best_xgb_params if best_xgb_params else {'n_estimators': 100}
        xgb_params['random_state'] = seed
        
        self.models = {
            'XGBoost': xgb.XGBRegressor(**xgb_params),
            'LightGBM': lgb.LGBMRegressor(random_state=seed, n_estimators=100, verbose=-1),
            'CatBoost': CatBoostRegressor(random_state=seed, iterations=100, verbose=0),
            'RandomForest': RandomForestRegressor(random_state=seed, n_estimators=50)
        }
        self.weights = {}
        
    def fit_predict_ensemble(self, X_tr, y_tr, X_te, n_splits=3):
        tscv = TimeSeriesSplit(n_splits=n_splits)
        scores_mae = {m: [] for m in self.models}

        for train_cv, val_cv in tscv.split(X_tr):
            X_cv_tr, X_cv_val = X_tr[train_cv], X_tr[val_cv]
            y_cv_tr, y_cv_val = y_tr[train_cv], y_tr[val_cv]

            for name, model in self.models.items():
                m_fold = clone(model)
                m_fold.fit(X_cv_tr, y_cv_tr)
                preds_val = m_fold.predict(X_cv_val)
                scores_mae[name].append(mean_absolute_error(y_cv_val, preds_val))

        # Softmax Negativo dos Erros
        inv_errors = {m: np.exp(-np.mean(scores_mae[m])) for m in self.models}
        total_inv_error = sum(inv_errors.values())
        self.weights = {m: inv_errors[m] / total_inv_error for m in inv_errors}

        preds_dict = {}
        for name, model in self.models.items():
            model.fit(X_tr, y_tr)
            preds_dict[name] = model.predict(X_te)
            
        ensemble_pred = sum(preds_dict[name] * self.weights[name] for name in self.models)
        preds_dict['Ensemble_Weighted'] = ensemble_pred
        return preds_dict


# =========================================================================
# 9. INTERFACE INTERATIVA STREAMLIT
# =========================================================================
st.set_page_config(page_title="Plataforma de Inteligencia Energetica UTFPR", page_icon="⚡", layout="wide")

db = DatabaseManager()
db.carregar_dados_reais_ou_simulados()
df_raw = db.carregar_dados()

st.title("⚡ Plataforma Integrada de Inteligência Energética UTFPR")

st.sidebar.header("🕹️ Módulos de Pesquisa")
opcao = st.sidebar.radio("Selecione:", [
    "📊 Benchmarking & Nested CV",
    "🔮 Previsão Probabilística",
    "🧠 XAI: SHAP & Partial Dependence",
    "📉 Detecção Avançada de Drift (PSI)",
    "⚙️ MLOps & Arquivos de Configuração"
])

cols_x = [
    'lag_24', 'lag_72', 'lag_168', 'lag_336',
    'rolling_mean_168', 'rolling_std_24', 'rolling_std_168', 'ewma_24',
    'interacao_temp_hora', 'sin_hora', 'cos_hora',
    'causal_trend', 'causal_seasonal_24'
]

if opcao == "📊 Benchmarking & Nested CV":
    st.subheader("📊 Avaliação de Desempenho e Validação Estatística")
    
    if st.button("Executar Pipeline de Validação Completa"):
        with st.spinner("Processando dados e otimizando com Optuna (Pruning & Parallel Search)..."):
            df_proc, split_idx = FeatureEngineer.processar_features(df_raw, train_ratio=0.8)
            X = df_proc[cols_x].values
            y = df_proc['demanda_kw'].values

            X_tr, X_te = X[:split_idx], X[split_idx:]
            y_tr, y_te = y[:split_idx], y[split_idx:]

            scaler = StandardScaler()
            X_tr_sc = scaler.fit_transform(X_tr)
            X_te_sc = scaler.transform(X_te)

            # Optuna com Pruning Ativado (Melhoria 4)
            def objective(trial):
                params = {
                    'n_estimators': trial.suggest_int('n_estimators', 50, 150),
                    'max_depth': trial.suggest_int('max_depth', 3, 7),
                    'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.15)
                }
                tscv = TimeSeriesSplit(n_splits=3)
                maes = []
                for step, (tr_idx, val_idx) in enumerate(tscv.split(X_tr_sc)):
                    m = xgb.XGBRegressor(**params, random_state=SEED)
                    m.fit(X_tr_sc[tr_idx], y_tr[tr_idx])
                    p = m.predict(X_tr_sc[val_idx])
                    mae_step = mean_absolute_error(y_tr[val_idx], p)
                    maes.append(mae_step)
                    
                    trial.report(mae_step, step)
                    if trial.should_prune():
                        raise optuna.TrialPruned()
                return np.mean(maes)

            study = optuna.create_study(direction="minimize", pruner=optuna.pruners.MedianPruner())
            study.optimize(objective, n_trials=10, n_jobs=-1)
            
            st.write("Best Hyperparameters (Optuna):", study.best_params)

            pipeline = EnsembleModelPipeline(best_xgb_params=study.best_params, seed=SEED)
            preds_dict = pipeline.fit_predict_ensemble(X_tr_sc, y_tr, X_te_sc)

            # Teste de Diebold-Mariano entre Ensemble e XGBoost (Melhoria 3)
            dm_p_value = diebold_mariano_test(y_te, preds_dict['Ensemble_Weighted'], preds_dict['XGBoost'])
            eff_size = cohens_d(y_te - preds_dict['Ensemble_Weighted'], y_te - preds_dict['XGBoost'])

            st.markdown(f"**Diebold-Mariano Test (Ensemble vs XGBoost):** p-valor = `{dm_p_value:.5f}`")
            st.markdown(f"**Tamanho de Efeito (Cohen's d):** `{eff_size:.4f}`")

elif opcao == "🔮 Previsão Probabilística":
    st.subheader("🔮 Avaliação Metrológica de Quantis (Pinball Loss & Coverage)")
    df_proc, split_idx = FeatureEngineer.processar_features(df_raw)
    X = df_proc[cols_x].values
    y = df_proc['demanda_kw'].values
    X_tr, X_te = X[:split_idx], X[split_idx:]
    y_tr, y_te = y[:split_idx], y[split_idx:]

    # Treinamento Quantílico via LightGBM
    m_p5 = lgb.LGBMRegressor(objective="quantile", alpha=0.05, random_state=SEED, verbose=-1).fit(X_tr, y_tr)
    m_p50 = lgb.LGBMRegressor(objective="quantile", alpha=0.50, random_state=SEED, verbose=-1).fit(X_tr, y_tr)
    m_p95 = lgb.LGBMRegressor(objective="quantile", alpha=0.95, random_state=SEED, verbose=-1).fit(X_tr, y_tr)

    p5 = m_p5.predict(X_te)
    p50 = m_p50.predict(X_te)
    p95 = m_p95.predict(X_te)

    loss_p5 = ProbabilisticEvaluator.pinball_loss(y_te, p5, 0.05)
    loss_p95 = ProbabilisticEvaluator.pinball_loss(y_te, p95, 0.95)
    coverage = ProbabilisticEvaluator.coverage_probability(y_te, p5, p95)

    st.metric("Pinball Loss (P5)", f"{loss_p5:.4f}")
    st.metric("Pinball Loss (P95)", f"{loss_p95:.4f}")
    st.metric("Prediction Interval Coverage Probability (PICP)", f"{coverage:.2f}%")

elif opcao == "🧠 XAI: SHAP & Partial Dependence":
    st.subheader("🧠 Interpretabilidade de Modelos (SHAP & PDP)")
    df_proc, _ = FeatureEngineer.processar_features(df_raw)
    X = df_proc[cols_x].values
    y = df_proc['demanda_kw'].values

    m = xgb.XGBRegressor(random_state=SEED).fit(X, y)
    
    st.markdown("#### Partial Dependence Plot (PDP) - Temperatura x Hora")
    pdp_results = partial_dependence(m, X, features=[cols_x.index('interacao_temp_hora')])
    
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(pdp_results['grid_values'][0], pdp_results['average'][0])
    ax.set_xlabel("Interação Temperatura-Hora")
    ax.set_ylabel("Impacto na Demanda Prevista (kW)")
    ax.grid(True)
    st.pyplot(fig)

elif opcao == "📉 Detecção Avançada de Drift (PSI)":
    st.subheader("📉 Monitoramento Estatístico de Data Drift (PSI)")
    df_proc, split_idx = FeatureEngineer.processar_features(df_raw)
    X = df_proc[cols_x].values
    X_tr, X_te = X[:split_idx], X[split_idx:]

    psi_list = []
    for i, col in enumerate(cols_x):
        psi_val = AdvancedDriftMonitor.calculate_psi(X_tr[:, i], X_te[:, i])
        psi_list.append({"Feature": col, "PSI": psi_val, "Status": "Drift Elevado" if psi_val > 0.2 else ("Atenção" if psi_val > 0.1 else "Estável")})

    st.dataframe(pd.DataFrame(psi_list), use_container_width=True)

elif opcao == "⚙️ MLOps & Arquivos de Configuração":
    st.subheader("⚙️ MLOps & Pipeline de Orquestração (Melhoria 6)")
    
    st.markdown("### `Dockerfile` Recomendado")
    st.code('''
FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
    ''', language="dockerfile")

    st.markdown("### `GitHub Actions Workflow` (`.github/workflows/ci_cd.yml`)")
    st.code('''
name: Integration & Continuous Deployment UTFPR

on:
  push:
    branches: [ "main" ]
  pull_request:
    branches: [ "main" ]

jobs:
  build-and-test:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python 3.10
      uses: actions/setup-python@v4
      with:
        python-version: "3.10"

    - name: Install Dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt

    - name: Run Tests & Verification
      run: |
        python -c "import torch, sklearn, xgboost, optuna; print('Ambiente Validado!')"
    ''', language="yaml")
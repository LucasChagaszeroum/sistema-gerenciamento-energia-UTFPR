import numpy as np
import pandas as pd

class FeatureEngineer:
    """
    Classe para engenharia de atributos em séries temporais elétricas.
    Gera lags, estatísticas móveis e variáveis cíclicas temporais.
    """
    @staticmethod
    def processar_features(df: pd.DataFrame, train_ratio: float = 0.8) -> tuple[pd.DataFrame, int]:
        # Ordena a série temporal pelo timestamp de forma estrita
        d = df.copy().sort_values('data_hora').reset_index(drop=True)

        # Lags temporais (atrasos em horas: 24h, 72h, 168h e 336h)
        d['lag_24'] = d['demanda_kw'].shift(24)
        d['lag_72'] = d['demanda_kw'].shift(72)
        d['lag_168'] = d['demanda_kw'].shift(168)
        d['lag_336'] = d['demanda_kw'].shift(336)

        # Estatísticas móveis (média, desvio padrão e EWMA com shift para evitar data leakage)
        d['rolling_mean_168'] = d['demanda_kw'].shift(1).rolling(168).mean()
        d['rolling_std_24'] = d['demanda_kw'].shift(1).rolling(24).std()
        d['rolling_std_168'] = d['demanda_kw'].shift(1).rolling(168).std()
        d['ewma_24'] = d['demanda_kw'].shift(1).ewm(span=24).mean()

        # Volatilidade instantânea de curto prazo (últimas 6 horas)
        d['volatilidade_6h'] = d['demanda_kw'].shift(1).rolling(6).std()

        # ADICIONADO: Amplitude móvel de 24h (Max - Min) para capturar a dispersão diária
        rolling_max_24 = d['demanda_kw'].shift(1).rolling(24).max()
        rolling_min_24 = d['demanda_kw'].shift(1).rolling(24).min()
        d['range_24h'] = rolling_max_24 - rolling_min_24

        # Atributos cíclicos e interações térmicas
        d['interacao_temp_hora'] = d['temperatura'] * d['data_hora'].dt.hour
        d['sin_hora'] = np.sin(2 * np.pi * d['data_hora'].dt.hour / 24.0)
        d['cos_hora'] = np.cos(2 * np.pi * d['data_hora'].dt.hour / 24.0)

        # Componentes de tendência e sazonalidade diária
        d['causal_trend'] = d['demanda_kw'].shift(1).rolling(168, min_periods=24).mean()
        d['causal_seasonal_24'] = d['demanda_kw'].shift(1) - d['demanda_kw'].shift(1).rolling(24, min_periods=1).mean()

        # Remove nulos iniciais gerados pelos deslocamentos e define índice de divisão temporal
        d = d.dropna().reset_index(drop=True)
        split_idx = int(len(d) * train_ratio)

        return d, split_idx
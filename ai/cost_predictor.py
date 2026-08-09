import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from services.api_service import RealAPIService

class EnergyCostPredictor:
    """Modelo preditivo para simulação e projeção de custos futuros em R$."""

    @staticmethod
    def prever_gastos_futuros(df_historico: pd.DataFrame, meses_frente: int = 3, bandeira_futura: str = "VERDE") -> pd.DataFrame:
        if df_historico.empty or len(df_historico) < 2:
            return pd.DataFrame()

        # Treinamento do modelo simples de tendência temporal
        X = np.arange(len(df_historico)).reshape(-1, 1)
        y = df_historico['consumo_kwh'].values

        model = LinearRegression().fit(X, y)

        # Projeção para os próximos meses
        X_futuro = np.arange(len(df_historico), len(df_historico) + meses_frente).reshape(-1, 1)
        kwh_projetado = model.predict(X_futuro)

        projecoes = []
        # Obtém a última data do histórico para avançar os meses
        ultima_data = pd.to_datetime(df_historico['mes_referencia'].iloc[-1])

        for i, kwh in enumerate(kwh_projetado):
            prox_mes = (ultima_data + pd.DateOffset(months=i+1)).strftime('%Y-%m')
            kwh_val = max(float(kwh), 50.0) # Limite mínimo residencial
            
            # Aplica o cálculo tarifário real para a quantidade de kWh prevista
            fatura_calc = RealAPIService.calcular_fatura_copel(kwh_val, bandeira=bandeira_futura)
            
            projecoes.append({
                "mes_referencia": prox_mes,
                "consumo_projetado_kwh": round(kwh_val, 1),
                "custo_estimado_r$": fatura_calc["valor_total_r$"],
                "tarifa_efetiva": fatura_calc["tarifa_efetiva_r$_kwh"],
                "bandeira_simulada": bandeira_futura
            })

        return pd.DataFrame(projecoes)
import numpy as np
import pandas as pd

class ResidentialAnalyzer:
    """Análise estatística de faturas de energia residenciais."""
    
    @staticmethod
    def analisar_historico(df_faturas: pd.DataFrame) -> dict:
        """
        Recebe o DataFrame de faturas da unidade e calcula médias,
        tendência e detecta se o último mês é uma anomalia.
        """
        if df_faturas.empty or len(df_faturas) < 1:
            return {"status": "SEM_DADOS"}

        consumos = df_faturas['consumo_kwh'].values
        ultimo_consumo = consumos[-1]
        
        if len(consumos) == 1:
            return {
                "status": "OK",
                "consumo_atual": ultimo_consumo,
                "media_historica": ultimo_consumo,
                "variacao_percentual": 0.0,
                "tendencia": "ESTAVEL",
                "anomalia_detectada": False
            }

        # Cálculo Estatístico
        historico = consumos[:-1]  # Todos exceto o último
        media_hist = np.mean(historico)
        desvio_padrao = np.std(historico) if len(historico) > 1 else 0.0
        
        variacao_perc = ((ultimo_consumo - media_hist) / media_hist) * 100.0

        # Anomalia: Consumo acima de 2 desvios padrões da média histórica
        limite_superior = media_hist + 2 * desvio_padrao
        eh_anomalia = bool(ultimo_consumo > limite_superior) if desvio_padrao > 0 else False

        # Tendência simples via inclinação
        if variacao_perc > 5.0:
            tendencia = "CRESCIMENTO"
        elif variacao_perc < -5.0:
            tendencia = "QUEDA"
        else:
            tendencia = "ESTAVEL"

        return {
            "status": "OK",
            "consumo_atual": float(ultimo_consumo),
            "media_historica": float(media_hist),
            "variacao_percentual": float(variacao_perc),
            "tendencia": tendencia,
            "anomalia_detectada": eh_anomalia
        }
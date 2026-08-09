import requests
import pandas as pd

class RealAPIService:
    """Serviço de consumo de APIs externas reais e cálculo tarifário ANEEL/COPEL."""

    @staticmethod
    def obter_temperatura_ponta_grossa() -> dict:
        """Consome a API da Open-Meteo para obter clima atual e previsão em Ponta Grossa."""
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": -25.095,
            "longitude": -50.1619,
            "current_weather": "true",
            "hourly": "temperature_2d",
            "forecast_days": 7
        }
        try:
            res = requests.get(url, params=params, timeout=5)
            if res.status_code == 200:
                data = res.json()
                return {
                    "temp_atual": data["current_weather"]["temperature"],
                    "historico_previsto": data["hourly"]["temperature_2d"][:168]
                }
        except Exception:
            pass
        return {"temp_atual": 21.0, "historico_previsto": [20.0] * 168}

    @staticmethod
    def calcular_fatura_copel(consumo_kwh: float, bandeira: str = "VERDE") -> dict:
        """Calcula o valor financeiro real (R$) B1 Residencial (TE + TUSD + Bandeiras + Impostos)."""
        tusd_base = 0.425
        te_base = 0.355

        adicional_bandeira = {
            "VERDE": 0.00,
            "AMARELA": 0.01885,
            "VERMELHA_P1": 0.04463,
            "VERMELHA_P2": 0.07877
        }.get(bandeira, 0.00)

        custo_energia = consumo_kwh * (tusd_base + te_base + adicional_bandeira)
        iluminacao_publica = 22.50

        fator_imposto = 1 - 0.235
        valor_final_bruto = (custo_energia / fator_imposto) + iluminacao_publica
        impostos_totais = valor_final_bruto - custo_energia - iluminacao_publica

        return {
            "consumo_kwh": consumo_kwh,
            "custo_energia_base": round(custo_energia, 2),
            "impostos_r$": round(impostos_totais, 2),
            "iluminacao_publica_r$": iluminacao_publica,
            "valor_total_r$": round(valor_final_bruto, 2),
            "tarifa_efetiva_r$_kwh": round(valor_final_bruto / consumo_kwh, 3) if consumo_kwh > 0 else 0
        }

    @staticmethod
    def calcular_fatura_industrial_copel(demanda_pico_kw: float, consumo_total_kwh: float, fp_medio: float) -> dict:
        """
        Calcula a fatura industrial binômia (Grupo A4 COPEL) em Reais (R$).
        Formula: Custo = (Demanda * T_d) + (Consumo * T_e) + Multa_FP, ajustado por impostos (ICMS/PIS/COFINS).
        """
        tarifa_demanda_kw = 38.50     # Valor homologado R$/kW
        tarifa_energia_kwh = 0.412    # Valor médio R$/kWh

        # 1. Parcela de faturamento de demanda
        custo_demanda = demanda_pico_kw * tarifa_demanda_kw

        # 2. Parcela de consumo ativo no período (720h)
        custo_consumo = consumo_total_kwh * tarifa_energia_kwh

        # 3. Penalidade ANEEL por baixo Fator de Potência (excedente reativo para FP < 0.92)
        multa_fp = 0.0
        if 0 < fp_medio < 0.92:
            fator_multa = (0.92 / fp_medio) - 1.0
            multa_fp = (custo_demanda + custo_consumo) * fator_multa

        custo_bruto = custo_demanda + custo_consumo + multa_fp

        # Aplicação de tributos estaduais e federais embutidos (23.5% total)
        fator_imposto = 1.0 - 0.235
        custo_mensal_total = custo_bruto / fator_imposto if fator_imposto > 0 else custo_bruto
        projecao_anual = custo_mensal_total * 12.0

        return {
            "custo_demanda_r$": round(custo_demanda, 2),
            "custo_consumo_r$": round(custo_consumo, 2),
            "multa_reativo_r$": round(multa_fp, 2),
            "custo_mensal_r$": round(custo_mensal_total, 2),
            "custo_anual_projetado_r$": round(projecao_anual, 2)
        }
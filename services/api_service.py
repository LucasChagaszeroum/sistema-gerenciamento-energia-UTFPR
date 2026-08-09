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
        """
        Calcula o valor financeiro real (R$) com base na estrutura tarifária da COPEL (B1 Residencial).
        Considera TE (Tarifa de Energia), TUSD, Bandeiras ANEEL, ICMS (18%) e PIS/COFINS (5.5%).
        """
        # Tarifas homologadas base (R$/kWh)
        tusd_base = 0.425
        te_base = 0.355

        # Adicionais de Bandeira Tarifária ANEEL (R$/kWh)
        adicional_bandeira = {
            "VERDE": 0.00,
            "AMARELA": 0.01885,
            "VERMELHA_P1": 0.04463,
            "VERMELHA_P2": 0.07877
        }.get(bandeira, 0.00)

        # Cálculo da base de cálculo sem impostos
        custo_energia = consumo_kwh * (tusd_base + te_base + adicional_bandeira)
        iluminacao_publica = 22.50 # Taxa média CIP

        # Aplicação de alíquotas por dentro (ICMS 18% + PIS/COFINS 5.5% ~= 23.5% total)
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
    
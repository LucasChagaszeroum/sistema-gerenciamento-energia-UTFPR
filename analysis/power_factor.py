import math
import numpy as np

def calcular_banco_capacitores(potencia_ativa_kw: float, fp_atual: float, fp_alvo: float = 0.92) -> dict:
    """
    Calcula a potência reativa (kVAr) necessária para corrigir o Fator de Potência (FP)
    até o limite regulatório mínimo exigido pela ANEEL (0.92).
    """
    if fp_atual >= fp_alvo:
        return {
            "necessita_correcao": False,
            "q_capacitativo_kvar": 0.0,
            "mensagem": "Fator de potência adequado. Sem cobrança de reativo excedente."
        }
    
    if fp_atual <= 0 or fp_atual >= 1.0:
        raise ValueError("O Fator de Potência atual deve estar entre 0 e 1 (exclusivo).")

    # Calculo dos angulos phi1 (atual) e phi2 (desejado)
    phi1 = math.acos(fp_atual)
    phi2 = math.acos(fp_alvo)

    # Qc = P * (tan(phi1) - tan(phi2))
    q_capacitivo = potencia_ativa_kw * (math.tan(phi1) - math.tan(phi2))

    return {
        "necessita_correcao": True,
        "fp_atual": fp_atual,
        "fp_alvo": fp_alvo,
        "q_capacitativo_kvar": round(q_capacitivo, 2),
        "mensagem": f"Necessário banco de capacitores de {q_capacitivo:.2f} kVAr para atingir FP {fp_alvo}."
    }

def calcular_multa_excesso_reativo(consumo_kwh: float, fp_medido: float, tarifa_eim_rs: float = 0.35) -> float:
    """
    Simula a penalidade por excesso de reativo indutivo segundo a fórmula regulatória da ANEEL.
    """
    if fp_medido >= 0.92:
        return 0.0

    # Parcela de energia reativa excedente faturável
    fator_multiplicativo = (0.92 / fp_medido) - 1.0
    vadr_rs = consumo_kwh * fator_multiplicativo * tarifa_eim_rs

    return round(max(0.0, vadr_rs), 2)
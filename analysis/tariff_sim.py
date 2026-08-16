def simular_tarifas_grupo_a(
    demanda_ponta_kw: float,
    demanda_fora_ponta_kw: float,
    consumo_ponta_kwh: float,
    consumo_fora_ponta_kwh: float,
    demanda_contratada_kw: float
) -> dict:
    """
    Compara os custos estimativos do enquadramento tarifário Azul vs. Verde (Subgrupo A4 COPEL).
    """
    # Tarifas médias de referência COPEL A4 (Valores ilustrativos para simulação)
    TARIFA_VERDE = {
        "demanda_unica_kw": 28.50,
        "energia_ponta_kwh": 1.45,
        "energia_fora_ponta_kwh": 0.55
    }
    
    TARIFA_AZUL = {
        "demanda_ponta_kw": 42.10,
        "demanda_fora_ponta_kw": 18.30,
        "energia_ponta_kwh": 0.85,
        "energia_fora_ponta_kwh": 0.55
    }

    # Custo Modalidade Verde (Demanda Única + Energia Diferenciada)
    demanda_maxima = max(demanda_ponta_kw, demanda_fora_ponta_kw, demanda_contratada_kw)
    custo_verde = (
        (demanda_maxima * TARIFA_VERDE["demanda_unica_kw"]) +
        (consumo_ponta_kwh * TARIFA_VERDE["energia_ponta_kwh"]) +
        (consumo_fora_ponta_kwh * TARIFA_VERDE["energia_fora_ponta_kwh"])
    )

    # Custo Modalidade Azul (Demanda e Energia Diferenciadas em Ponta e Fora-Ponta)
    custo_azul = (
        (max(demanda_ponta_kw, demanda_contratada_kw) * TARIFA_AZUL["demanda_ponta_kw"]) +
        (max(demanda_fora_ponta_kw, demanda_contratada_kw) * TARIFA_AZUL["demanda_fora_ponta_kw"]) +
        (consumo_ponta_kwh * TARIFA_AZUL["energia_ponta_kwh"]) +
        (consumo_fora_ponta_kwh * TARIFA_AZUL["energia_fora_ponta_kwh"])
    )

    recomendacao = "VERDE" if custo_verde < custo_azul else "AZUL"
    economia_rs = abs(custo_verde - custo_azul)

    return {
        "custo_total_verde_rs": round(custo_verde, 2),
        "custo_total_azul_rs": round(custo_azul, 2),
        "modalidade_recomendada": recomendacao,
        "economia_estimada_rs": round(economia_rs, 2)
    }
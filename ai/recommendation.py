class EnergyRecommendationEngine:
    """Motor de Inteligência e Recomendações para Economia de Energia."""
    
    @staticmethod
    def gerar_recomendacoes_residenciais(diagnostico: dict) -> list[dict]:
        """Gera recomendações com categoria, evidência e grau de confiança."""
        recomendacoes = []
        
        if diagnostico.get("status") != "OK":
            return recomendacoes

        variacao = diagnostico["variacao_percentual"]
        eh_anomalia = diagnostico["anomalia_detectada"]

        if eh_anomalia:
            recomendacoes.append({
                "categoria": "Anomalia de Consumo — Prioridade Alta",
                "descricao": "O consumo deste mês ultrapassou o limite estatístico do seu histórico.",
                "evidencia": f"Aumento de {variacao:.1f}% em relação à sua média histórica ({diagnostico['media_historica']:.0f} kWh).",
                "recomendacao": "Verifique vazamentos de corrente, defeitos em vedações de refrigeradores ou uso atípico de equipamentos de alta potência (chuveiros/ar-condicionado).",
                "confianca": 88
            })
        elif variacao > 15.0:
            recomendacoes.append({
                "categoria": "Climatização e Elevação de Carga",
                "descricao": "Houve uma elevação significativa de demanda em relação ao padrão anterior.",
                "evidencia": f"Variação positiva de +{variacao:.1f}% observada no último período faturado.",
                "recomendacao": "O padrão é compatível com aumento de carga em dias mais quentes/frios. Recomenda-se ajustar o termostato de aparelhos de climatização.",
                "confianca": 75
            })
        else:
            recomendacoes.append({
                "categoria": "Eficiência Operacional",
                "descricao": "Seu perfil de consumo permanece dentro da faixa de estabilidade esperada.",
                "evidencia": f"Consumo atual ({diagnostico['consumo_atual']:.0f} kWh) alinhado à média ({diagnostico['media_historica']:.0f} kWh).",
                "recomendacao": "Mantenha as práticas atuais e avalie a substituição gradual de lâmpadas restantes por LED.",
                "confianca": 92
            })

        return recomendacoes
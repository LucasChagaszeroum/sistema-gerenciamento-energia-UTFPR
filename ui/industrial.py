import streamlit as st
import pandas as pd

from data.database import DatabaseManager
from services.api_service import RealAPIService

def render_industrial_ui(db: DatabaseManager):
    """Renderiza o painel industrial combinando monitoramento elétrico e faturamento Grupo A."""
    st.header("🏭 Módulo Industrial — Telemetria & Custos Reais (Grupo A)")

    df_raw = db.carregar_dados()
    if df_raw.empty:
        db.carregar_dados_reais_ou_simulados()
        df_raw = db.carregar_dados()

    # Grandezas técnicas extraídas do banco de dados
    demanda_maxima = float(df_raw['demanda_kw'].max())
    demanda_media = float(df_raw['demanda_kw'].mean())
    fp_medio = float(df_raw['fator_potencia'].mean())
    consumo_acumulado_kwh = float(df_raw['demanda_kw'].sum()) # Integração das 720 horas da série

    # Cálculo do faturamento em Reais via API tarifária
    custos = RealAPIService.calcular_fatura_industrial_copel(demanda_maxima, consumo_acumulado_kwh, fp_medio)

    # Bloco 1: Indicadores Financeiros
    st.subheader("💰 Impacto Financeiro (Tarifa A4 COPEL/ANEEL)")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Gasto Mensal Estimado", f"R$ {custos['custo_mensal_r$']:,.2f}")
    c2.metric("Projeção Anual", f"R$ {custos['custo_anual_projetado_r$']:,.2f}")
    c3.metric("Parcela Demanda", f"R$ {custos['custo_demanda_r$']:,.2f}")
    c4.metric(
        "Multa Fator de Potência", 
        f"R$ {custos['multa_reativo_r$']:,.2f}",
        delta="- Multa ANEEL" if custos['multa_reativo_r$'] > 0 else "Operação Ideal",
        delta_color="inverse" if custos['multa_reativo_r$'] > 0 else "normal"
    )

    st.markdown("---")

    # Bloco 2: Métricas de Operação Técnica
    st.subheader("⚡ Parâmetros Elétricos de Operação")
    col1, col2, col3 = st.columns(3)
    col1.metric("Pico de Demanda (kW)", f"{demanda_maxima:.2f} kW")
    col2.metric("Demanda Média (kW)", f"{demanda_media:.2f} kW")
    col3.metric("Fator de Potência Médio", f"{fp_medio:.2f}", delta="Ideal >= 0.92")

    # Gráfico de Curva de Carga
    st.subheader("📈 Curva de Carga Horária de Demanda (kW)")
    st.line_chart(df_raw.set_index('data_hora')['demanda_kw'].tail(168))

    if fp_medio < 0.92:
        st.error("⚠️ **Alerta Regulatório:** Fator de potência abaixo de 0.92 acionando cobrança por excedente reativo!")
    else:
        st.success("✅ Sistema operando em conformidade com as diretrizes de eficiência da ANEEL.")
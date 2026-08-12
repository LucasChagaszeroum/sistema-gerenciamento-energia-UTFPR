import streamlit as st
import pandas as pd

# Conexão com o gerenciador de banco de dados e serviço tarifário ANEEL/COPEL
from data.database import DatabaseManager
from services.api_service import RealAPIService

def render_industrial_ui(db: DatabaseManager):
    """Renderiza o painel industrial combinando monitoramento elétrico, gráficos e faturamento Grupo A4."""
    st.header("🏭 Módulo Industrial — Telemetria & Custos Reais (Grupo A4)")

    # 1. Carrega a série temporal de medições do SQLite
    df_raw = db.carregar_dados()
    if df_raw.empty:
        db.carregar_dados_reais_ou_simulados()
        df_raw = db.carregar_dados()

    # 2. Extração de parâmetros elétricos operacionais
    demanda_maxima = float(df_raw['demanda_kw'].max())
    demanda_media = float(df_raw['demanda_kw'].mean())
    fp_medio = float(df_raw['fator_potencia'].mean())
    consumo_acumulado_kwh = float(df_raw['demanda_kw'].sum())  # Integração horária (720h)

    # 3. Cálculo tarifário binômio (Demanda + Consumo + Excedente Reativo + Tributos)
    custos = RealAPIService.calcular_fatura_industrial_copel(demanda_maxima, consumo_acumulado_kwh, fp_medio)

    # --- BLOCO 1: INDICADORES FINANCEIROS ---
    st.subheader("💰 Resumo do Faturamento (Tarifa A4 COPEL)")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Gasto Mensal Estimado", f"R$ {custos['custo_mensal_r$']:,.2f}")
    c2.metric("Projeção Anual", f"R$ {custos['custo_anual_projetado_r$']:,.2f}")
    c3.metric("Parcela Demanda", f"R$ {custos['custo_demanda_r$']:,.2f}")
    c4.metric(
        "Multa Excedente Reativo", 
        f"R$ {custos['multa_reativo_r$']:,.2f}",
        delta="- Penalidade ANEEL" if custos['multa_reativo_r$'] > 0 else "Operação Ideal",
        delta_color="inverse" if custos['multa_reativo_r$'] > 0 else "normal"
    )

    st.markdown("---")

    # --- BLOCO 2: PARÂMETROS TÉCNICOS E CURVA DE CARGA ---
    st.subheader("⚡ Parâmetros Elétricos e Curva de Carga Horária")
    col1, col2, col3 = st.columns(3)
    col1.metric("Pico de Demanda", f"{demanda_maxima:.2f} kW")
    col2.metric("Demanda Média", f"{demanda_media:.2f} kW")
    col3.metric("Fator de Potência Médio", f"{fp_medio:.2f}", delta="Meta ANEEL >= 0.92")

    # Gráfico de evolução da demanda horária
    st.subheader("📈 Telemetria de Demanda Horária (Últimas 168 horas)")
    st.line_chart(df_raw.set_index('data_hora')['demanda_kw'].tail(168))

    # Diagnóstico regulatório
    if fp_medio < 0.92:
        st.error("⚠️ **Alerta de Eficiência:** Fator de potência abaixo do limite regulatório (0.92). A instalação de banco de capacitores é recomendada para eliminar multas.")
    else:
        st.success("✅ **Operação Conforme:** Fator de potência dentro dos limites de conformidade da ANEEL.")
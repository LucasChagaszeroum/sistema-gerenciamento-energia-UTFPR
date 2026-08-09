import streamlit as st
import pandas as pd
from data.database import DatabaseManager

def render_industrial_ui(db: DatabaseManager):
    """Renderiza a interface do módulo Industrial."""
    st.header("🏭 Módulo Industrial — Monitoramento de Curva de Carga")

    df_raw = db.carregar_dados()
    if df_raw.empty:
        db.carregar_dados_reais_ou_simulados()
        df_raw = db.carregar_dados()

    # Métricas de Operação Industrial
    demanda_maxima = df_raw['demanda_kw'].max()
    demanda_media = df_raw['demanda_kw'].mean()
    fp_medio = df_raw['fator_potencia'].mean()

    col1, col2, col3 = st.columns(3)
    col1.metric("Pico de Demanda (kW)", f"{demanda_maxima:.2f} kW")
    col2.metric("Demanda Média (kW)", f"{demanda_media:.2f} kW")
    col3.metric("Fator de Potência Média", f"{fp_medio:.2f}", delta="Ideal >= 0.92")

    # Gráfico da Curva de Carga Temporal
    st.subheader("📈 Curva de Carga Horária de Demanda (kW)")
    st.line_chart(df_raw.set_index('data_hora')['demanda_kw'].tail(168))

    # Alerta de Fator de Potência Indutivo/Capacitivo
    if fp_medio < 0.92:
        st.error("⚠️ **Alerta Risco de Multa:** Fator de potência médio abaixo do limite regulatório de 0.92!")
    else:
        st.success("✅ Fator de potência operando dentro dos limites normativos da ANEEL.")
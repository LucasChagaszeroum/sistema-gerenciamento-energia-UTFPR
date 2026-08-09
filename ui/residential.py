import streamlit as st
from services.api_service import RealAPIService
from ai.cost_predictor import EnergyCostPredictor
from services.report_generator import PDFReportGenerator

# Exibição do Clima em Ponta Grossa obtido via API real
clima = RealAPIService.obter_temperatura_ponta_grossa()
st.sidebar.info(f"🌡️ Temp. Atual (Ponta Grossa): **{clima['temp_atual']} °C**")

# Dentro do fluxo da interface residencial:
df_faturas = db.carregar_faturas(unidade_selecionada)

if not df_faturas.empty:
    st.subheader("🔮 Simulação e Previsão de Gastos Futuros (R$)")
    
    col_sim1, col_sim2 = st.columns(2)
    meses_sim = col_sim1.slider("Meses para simular:", 1, 6, 3)
    bandeira_sim = col_sim2.selectbox("Simular Bandeira Tarifária ANEEL:", ["VERDE", "AMARELA", "VERMELHA_P1", "VERMELHA_P2"])
    
    # Executa a predição conectando o modelo com a estrutura de tarifas
    df_projeçao = EnergyCostPredictor.prever_gastos_futuros(df_faturas, meses_frente=meses_sim, bandeira_futura=bandeira_sim)
    
    st.dataframe(df_projeçao, use_container_width=True)

    # Botão para download do relatório em PDF
    pdf_bytes = PDFReportGenerator.gerar_relatorio_pdf("Casa 1", df_faturas, df_projeçao)
    
    st.download_button(
        label="📥 Baixar Relatório Técnico Completo (PDF)",
        data=pdf_bytes,
        file_name="relatorio_diagnostico_energetico_utfpr.pdf",
        mime="application/pdf"
    )
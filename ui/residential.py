import streamlit as st
import pandas as pd

# 1. Módulos de Persistência e Parsers
from data.database import DatabaseManager
from data.invoice_parser import InvoiceParser

# 2. Módulos Estatísticos e Inteligência Artificial
from analysis.residential import ResidentialAnalyzer
from ai.recommendations import EnergyRecommendationEngine
from ai.cost_predictor import EnergyCostPredictor

# 3. Módulos de Tarifação COPEL e Gerador de PDF
from services.api_service import RealAPIService
from services.report_generator import PDFReportGenerator


def render_residential_ui(db: DatabaseManager):
    """Renderiza a interface residencial integrando OCR, estatística, IA e exportação PDF."""
    st.header("🏠 Módulo Residencial — Gestão Inteligente de Faturas (B1)")
    
    df_faturas = db.carregar_faturas_residenciais()
    if df_faturas.empty:
        db.resetar_faturas_residenciais()
        df_faturas = db.carregar_faturas_residenciais()

    # --- ABA DE AÇÕES E OCR DE FATURAS ---
    st.subheader("⚙️ Operações e Leitura de Faturas")
    c_ocr, c_del, c_reset = st.columns([2, 2, 1])

    # Leitura automatizada via InvoiceParser
    with c_ocr:
        with st.expander("📄 Upload de Fatura (OCR / Leitura Automática)", expanded=False):
            arquivo_fatura = st.file_uploader("Envie a fatura em PDF ou Imagem", type=["pdf", "png", "jpg"])
            
            if arquivo_fatura is not None:
                dados_extraidos = InvoiceParser.extrair_dados_fatura(arquivo_fatura)
                st.info(f"Consumo Detectado: **{dados_extraidos['consumo_kwh']} kWh**")
                
                with st.form("form_confirm_ocr"):
                    mes_ocr = st.text_input("Mês/Ano", value="2026-05")
                    bandeira_ocr = st.selectbox("Bandeira", ["VERDE", "AMARELA", "VERMELHA_P1", "VERMELHA_P2"])
                    
                    if st.form_submit_button("Confirmar e Salvar Fatura"):
                        calc = RealAPIService.calcular_fatura_copel(dados_extraidos['consumo_kwh'], bandeira_ocr)
                        db.adicionar_fatura_residencial(mes_ocr, dados_extraidos['consumo_kwh'], bandeira_ocr, calc["valor_total_r$"])
                        st.success("Fatura salva via OCR!")
                        st.rerun()

    # Remoção de Faturas
    with c_del:
        with st.expander("🗑️ Remover Fatura", expanded=False):
            if not df_faturas.empty:
                opcoes = {f"ID {row['id']} - {row['mes_ano']} ({row['consumo_kwh']} kWh)": row['id'] for _, row in df_faturas.iterrows()}
                fat_sel = st.selectbox("Selecione para deletar:", list(opcoes.keys()))
                if st.button("Confirmar Exclusão", type="primary"):
                    db.deletar_fatura_residencial(opcoes[fat_sel])
                    st.rerun()

    # Reset do Banco
    with c_reset:
        st.write(" ")
        if st.button("🔄 Resetar"):
            db.resetar_faturas_residenciais()
            st.rerun()

    st.markdown("---")

    # --- DIAGNÓSTICO ESTATÍSTICO E RECOMENDAÇÕES ---
    st.subheader("📊 Diagnóstico Estatístico e Recomendações de IA")
    
    diagnostico = ResidentialAnalyzer.analisar_historico(df_faturas)
    
    if diagnostico.get("status") == "OK":
        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("Consumo Atual", f"{diagnostico['consumo_atual']:.1f} kWh")
        col_m2.metric("Média Histórica", f"{diagnostico['media_historica']:.1f} kWh")
        col_m3.metric("Variação", f"{diagnostico['variacao_percentual']:.1f}%", delta_color="inverse")

        recomendas = EnergyRecommendationEngine.gerar_recomendacoes_residenciais(diagnostico)
        for rec in recomendas:
            if diagnostico["anomalia_detectada"]:
                st.error(f"⚠️ **{rec['categoria']}** (Confiança: {rec['confianca']}%)\n\n{rec['recomendacao']}")
            else:
                st.success(f"💡 **{rec['categoria']}** (Confiança: {rec['confianca']}%)\n\n{rec['recomendacao']}")

    st.markdown("---")

    # --- PROJEÇÃO PREDITIVA DE CUSTOS ---
    st.subheader("🔮 Projeção de Gastos Futuros via IA")
    
    df_hist_formatted = df_faturas.rename(columns={"mes_ano": "mes_referencia"}).sort_values("id")
    df_projecao = EnergyCostPredictor.prever_gastos_futuros(df_hist_formatted, meses_frente=3, bandeira_futura="VERDE")
    
    if not df_projecao.empty:
        st.dataframe(df_projecao.style.format({"consumo_projetado_kwh": "{:.1f} kWh", "custo_estimado_r$": "R$ {:.2f}"}), use_container_width=True)

    st.markdown("---")

    # --- RELATÓRIO TÉCNICO PDF ---
    st.subheader("📄 Emissão de Laudo Técnico")
    
    pdf_bytes = PDFReportGenerator.gerar_relatorio_pdf("Residencial - UTFPR", df_hist_formatted, df_projecao)
    st.download_button(
        label="📥 Baixar Relatório de Diagnóstico em PDF",
        data=pdf_bytes,
        file_name="diagnostico_energetico_utfpr.pdf",
        mime="application/pdf"
    )
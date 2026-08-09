import streamlit as st
import pandas as pd
from datetime import datetime
from data.database import DatabaseManager
from data.invoice_parser import InvoiceParser
from analysis.residential import ResidentialAnalyzer
from ai.recommendations import EnergyRecommendationEngine

def render_residential_ui(db: DatabaseManager):
    st.header("🏠 Módulo Residencial — Gestão de Faturas e Economia")

    # 1. Seleção ou Cadastro de Residência
    df_unidades = db.listar_unidades(tipo="RESIDENCIAL")
    
    st.sidebar.subheader("🏡 Residências")
    if df_unidades.empty:
        st.info("Nenhuma residência cadastrada. Cadastre sua primeira unidade para começar.")
        with st.form("form_nova_residencia"):
            nome = st.text_input("Nome da Residência (ex: Casa Principal, Ap 102)")
            cidade = st.text_input("Cidade", value="Ponta Grossa")
            concessionaria = st.selectbox("Concessionária", ["COPEL", "ENEL", "CEMIG", "Outra"])
            tarifa = st.number_input("Tarifa Estimada (R$/kWh)", value=0.85, step=0.01)
            btn_cadastrar = st.form_submit_button("Cadastrar Residência")
            
            if btn_cadastrar and nome:
                uid = db.cadastrar_unidade(nome, "RESIDENCIAL", cidade, concessionaria, tarifa)
                st.success(f"Residência '{nome}' cadastrada com sucesso!")
                st.rerun()
        return

    unidade_selecionada = st.sidebar.selectbox(
        "Selecione a Residência:",
        options=df_unidades['id'].tolist(),
        format_func=lambda x: df_unidades[df_unidades['id'] == x]['nome'].values[0]
    )

    # Abas do Módulo Residencial
    aba1, aba2, aba3 = st.tabs(["📊 Visão Geral & Diagnóstico", "📄 Nova Fatura (Upload)", "💡 Recomendações de IA"])

    df_faturas = db.carregar_faturas(unidade_selecionada)

    # ABA 1: VISÃO GERAL
    with aba1:
        diagnostico = ResidentialAnalyzer.analisar_historico(df_faturas)
        if diagnostico["status"] == "SEM_DADOS":
            st.warning("Nenhuma fatura cadastrada para esta residência. Acesse a aba 'Nova Fatura' para enviar seu primeiro comprovante.")
        else:
            col1, col2, col3 = st.columns(3)
            col1.metric("Consumo Atual", f"{diagnostico['consumo_atual']:.0f} kWh")
            col2.metric("Média Histórica", f"{diagnostico['media_historica']:.0f} kWh")
            col3.metric("Variação", f"{diagnostico['variacao_percentual']:.1f}%", delta_color="inverse")

            if diagnostico["anomalia_detectada"]:
                st.error("🔴 **Atenção:** O consumo atual apresentou um desvio estatístico significativo em relação ao seu histórico.")

            if not df_faturas.empty:
                st.subheader("📈 Historico de Consumo (kWh)")
                st.line_chart(df_faturas.set_index('periodo_fim')['consumo_kwh'])

    # ABA 2: UPLOAD E CONFIRMAÇÃO DE FATURA
    with aba2:
        st.subheader("Envio de Fatura de Energia")
        arquivo = st.file_uploader("Envie sua fatura (PDF ou Imagem)", type=["pdf", "png", "jpg", "jpeg"])
        
        if arquivo is not None:
            dados_extraidos = InvoiceParser.extrair_dados_fatura(arquivo)
            
            st.info("🔎 **Validação dos Dados Encontrados:** Verifique e confirme as informações abaixo antes de salvar.")
            
            with st.form("form_confirmar_fatura"):
                col_a, col_b = st.columns(2)
                consumo_confirmado = col_a.number_input("Consumo (kWh)", value=dados_extraidos["consumo_kwh"])
                valor_confirmado = col_b.number_input("Valor Total (R$)", value=dados_extraidos["valor_total"])
                
                p_inicio = st.date_input("Início do Período", value=datetime.now())
                p_fim = st.date_input("Fim do Período", value=datetime.now())
                
                btn_salvar = st.form_submit_button("Confirmar e Salvar no Banco")
                
                if btn_salvar:
                    db.salvar_fatura(unidade_selecionada, consumo_confirmado, valor_confirmado, p_inicio, p_fim)
                    st.success("Fatura registrada e integrada ao histórico da unidade!")
                    st.rerun()

    # ABA 3: RECOMENDAÇÕES DA IA
    with aba3:
        st.subheader("🤖 Recomendações Automáticas para Economia")
        diagnostico = ResidentialAnalyzer.analisar_historico(df_faturas)
        recs = EnergyRecommendationEngine.gerar_recomendacoes_residenciais(diagnostico)
        
        for r in recs:
            with st.expander(f"💡 {r['categoria']} (Confiança: {r['confianca']}%)", expanded=True):
                st.write(f"**Diagnóstico:** {r['descricao']}")
                st.write(f"**Evidência:** {r['evidencia']}")
                st.markdown(f"**Ação Recomendada:** {r['recomendacao']}")
import streamlit as st
import pandas as pd
from datetime import datetime

# Importação dos módulos internos do projeto
from data.database import DatabaseManager
from services.api_service import RealAPIService
from ai.cost_predictor import EnergyCostPredictor
from services.report_generator import PDFReportGenerator


def render_residential_ui(db: DatabaseManager):
    """Renderiza a interface do módulo residencial e gerencia faturas/simulações."""
    st.header("🏠 Módulo Residencial — Gestão de Faturas e Economia")

    # Exibe temperatura em tempo real via API da Open-Meteo no menu lateral
    clima = RealAPIService.obter_temperatura_ponta_grossa()
    st.sidebar.info(f"🌡️ Temp. Atual (Ponta Grossa): **{clima['temp_atual']} °C**")

    # 1. Busca unidades consumidoras cadastradas no SQLite3
    df_unidades = db.listar_unidades(tipo="RESIDENCIAL")
    
    st.sidebar.subheader("🏡 Residências")
    
    # Caso nenhuma unidade exista, exibe formulário de primeiro cadastro
    if df_unidades.empty:
        st.info("Nenhuma residência cadastrada. Cadastre sua primeira unidade para começar.")
        with st.form("form_nova_residencia"):
            nome = st.text_input("Nome da Residência (ex: Casa Principal, Ap 102)")
            cidade = st.text_input("Cidade", value="Ponta Grossa")
            concessionaria = st.selectbox("Concessionária", ["COPEL", "ENEL", "CEMIG", "Outra"])
            tarifa = st.number_input("Tarifa Estimada (R$/kWh)", value=0.85, step=0.01)
            btn_cadastrar = st.form_submit_button("Cadastrar Residência")
            
            if btn_cadastrar and nome:
                db.cadastrar_unidade(nome, "RESIDENCIAL", cidade, concessionaria, tarifa)
                st.success(f"Residência '{nome}' cadastrada com sucesso!")
                st.rerun()
        return

    # Seletor de unidade consumidora na barra lateral
    unidade_selecionada = st.sidebar.selectbox(
        "Selecione a Residência:",
        options=df_unidades['id'].tolist(),
        format_func=lambda x: df_unidades[df_unidades['id'] == x]['nome'].values[0]
    )

    # 2. Carrega faturas da unidade selecionada DENTRO do escopo da função
    df_faturas = db.carregar_faturas(unidade_selecionada)

    # Abas organizacionais da interface
    aba1, aba2, aba3 = st.tabs(["📊 Visão Geral & Histórico", "📄 Nova Fatura", "🔮 Simulação e PDF"])

    # ABA 1: VISÃO GERAL DE CONSUMO E CUSTOS
    with aba1:
        if df_faturas.empty:
            st.warning("Nenhuma fatura cadastrada para esta residência. Acesse a aba 'Nova Fatura'.")
        else:
            # Métricas principais calculadas a partir do histórico
            ultimo_consumo = df_faturas['consumo_kwh'].iloc[-1]
            ultimo_valor = df_faturas['valor_total'].iloc[-1]
            media_kwh = df_faturas['consumo_kwh'].mean()

            col1, col2, col3 = st.columns(3)
            col1.metric("Último Consumo", f"{ultimo_consumo:.1f} kWh")
            col2.metric("Última Fatura", f"R$ {ultimo_valor:.2f}")
            col3.metric("Média Histórica", f"{media_kwh:.1f} kWh")

            st.subheader("📈 Histórico de Consumo (kWh)")
            st.line_chart(df_faturas.set_index('periodo_fim')['consumo_kwh'])

    # ABA 2: CADASTRO MANUAL OU ENVIO DE FATURA
    with aba2:
        st.subheader("Envio de Fatura de Energia")
        with st.form("form_confirmar_fatura"):
            col_a, col_b = st.columns(2)
            consumo_confirmado = col_a.number_input("Consumo (kWh)", min_value=0.0, value=200.0)
            valor_confirmado = col_b.number_input("Valor Total (R$)", min_value=0.0, value=170.0)
            
            p_inicio = st.date_input("Início do Período", value=datetime.now())
            p_fim = st.date_input("Fim do Período", value=datetime.now())
            
            btn_salvar = st.form_submit_button("Confirmar e Salvar no Banco")
            
            if btn_salvar:
                db.salvar_fatura(unidade_selecionada, consumo_confirmado, valor_confirmado, p_inicio, p_fim)
                st.success("Fatura registrada e integrada ao histórico da unidade!")
                st.rerun()

    # ABA 3: SIMULAÇÃO PREDITIVA E DOWNLOAD DE RELATÓRIO PDF
    with aba3:
        st.subheader("🔮 Simulação de Gastos Futuros e Relatório Técnico")
        if df_faturas.empty:
            st.info("Cadastre pelo menos uma fatura para liberar as simulações preditivas.")
        else:
            col_sim1, col_sim2 = st.columns(2)
            meses_sim = col_sim1.slider("Meses para simular:", 1, 6, 3)
            bandeira_sim = col_sim2.selectbox("Bandeira Tarifária ANEEL:", ["VERDE", "AMARELA", "VERMELHA_P1", "VERMELHA_P2"])
            
            # Projeção preditiva baseada nas regras tarifárias da COPEL/ANEEL
            df_projeção = EnergyCostPredictor.prever_gastos_futuros(df_faturas, meses_frente=meses_sim, bandeira_futura=bandeira_sim)
            st.dataframe(df_projeção, use_container_width=True)

            # Geração do relatório em PDF para download
            pdf_bytes = PDFReportGenerator.gerar_relatorio_pdf("Casa 1", df_faturas, df_projeção)
            st.download_button(
                label="📥 Baixar Relatório Técnico Completo (PDF)",
                data=pdf_bytes,
                file_name="relatorio_diagnostico_energetico_utfpr.pdf",
                mime="application/pdf"
            )
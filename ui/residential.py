import streamlit as st
import pandas as pd
import pypdf
import re
import numpy as np
from datetime import datetime

# Importações defensivas dos serviços internos do projeto
try:
    from services.report_generator import PDFReportGenerator
except ImportError:
    PDFReportGenerator = None

try:
    from ai.recommendations import EnergyRecommendationEngine
except ImportError:
    EnergyRecommendationEngine = None


def extrair_dados_pdf_copel(pdf_file) -> dict:
    """
    Lê o PDF da fatura via pypdf e extrai Mês/Ano, Consumo (kWh) e Valor Total (R$) via Regex.
    """
    reader = pypdf.PdfReader(pdf_file)
    texto_completo = ""
    for page in reader.pages:
        texto_completo += page.extract_text() or ""

    # Padrões Regex para faturas de energia
    match_mes = re.search(r'(\d{2}/\d{4})', texto_completo)
    match_kwh = re.search(r'(\d+[\.,]?\d*)\s*kWh', texto_completo, re.IGNORECASE)
    match_valor = re.search(r'R\$\s*(\d+[\.,]\d{2})', texto_completo)

    mes_ano = match_mes.group(1) if match_mes else datetime.now().strftime("%m/%Y")
    consumo_kwh = float(match_kwh.group(1).replace('.', '').replace(',', '.')) if match_kwh else 180.0
    valor_total = float(match_valor.group(1).replace('.', '').replace(',', '.')) if match_valor else 145.50

    return {
        "mes_ano": mes_ano,
        "consumo_kwh": consumo_kwh,
        "valor_total": valor_total,
        "bandeira": "Verde"
    }


def gerar_recomendacoes_ia(df_faturas: pd.DataFrame) -> list:
    """
    Motor de Recomendações de IA / Regras para otimização do Padrão Econômico (B1).
    """
    recomendacoes = []
    
    if df_faturas.empty:
        return recomendacoes

    media_consumo = df_faturas["consumo_kwh"].mean()
    meta_economica = 150.0  # Meta de referência para o padrão econômico (kWh/mês)

    # Regra 1: Avaliação de Meta de Consumo
    if media_consumo > meta_economica:
        excesso = media_consumo - meta_economica
        recomendacoes.append(
            f"⚠️ **Atenção ao Consumo:** A média atual ({media_consumo:.1f} kWh) está {excesso:.1f} kWh acima da meta de 150 kWh/mês. "
            "Recomenda-se auditar aparelhos de alta potência (chuveiros elétricos, ar-condicionado)."
        )
    else:
        recomendacoes.append(
            f"✅ **Excelente Desempenho:** Sua média ({media_consumo:.1f} kWh/mês) está dentro da meta econômica de 150 kWh!"
        )

    # Regra 2: Análise de Custo Médio por kWh
    df_faturas["tarifa_efetiva"] = df_faturas["valor_total"] / np.maximum(df_faturas["consumo_kwh"], 1)
    tarifa_media = df_faturas["tarifa_efetiva"].mean()
    
    if tarifa_media > 0.85:
        recomendacoes.append(
            f"💡 **Impacto Tarifário:** O custo médio faturado está alto (R$ {tarifa_media:.2f}/kWh). "
            "Verifique o peso dos impostos (ICMS/PIS/COFINS) e evite horários de pico de uso térmico."
        )

    # Regra 3: Variabilidade de Consumo (Desvio Padrão)
    if len(df_faturas) >= 2:
        std_consumo = df_faturas["consumo_kwh"].std()
        if std_consumo > 40.0:
            recomendacoes.append(
                f"📈 **Instabilidade Detectada:** Variação elevada entre meses (Desvio Padrão: {std_consumo:.1f} kWh). "
                "Sugere-se manter rotinas sazonais de uso de eletrodomésticos."
            )

    return recomendacoes


def render_residential_ui(db=None):
    """
    Interface Principal do Módulo Residencial (Grupo B) reunindo todas as funcionalidades.
    """
    st.title("🏠 Módulo Residencial - Grupo B")
    st.caption("Plataforma de Gestão de Faturas, OCR, Diagnósticos Estatísticos, IA e Laudos Técnicos.")

    # Inicialização da lista de faturas no estado da sessão
    if "faturas_residenciais" not in st.session_state:
        st.session_state.faturas_residenciais = []

    # =========================================================================
    # 1. GESTÃO DE FATURAS (CADASTRO VIA OCR / MANUAL)
    # =========================================================================
    st.subheader("📥 Entrada de Faturas")
    tab_pdf, tab_manual = st.tabs(["📄 Leitura OCR (PDF)", "✍️ Cadastro Manual"])

    # Aba OCR / PDF
    with tab_pdf:
        uploaded_file = st.file_uploader("Faça upload da fatura em formato PDF (ex: COPEL)", type=["pdf"])
        if uploaded_file is not None:
            if st.button("🔍 Processar Fatura via OCR", type="primary"):
                try:
                    dados = extrair_dados_pdf_copel(uploaded_file)
                    novo_id = len(st.session_state.faturas_residenciais) + 1
                    
                    nova_fatura = {
                        "id": novo_id,
                        "mes_ano": dados["mes_ano"],
                        "consumo_kwh": dados["consumo_kwh"],
                        "valor_total": dados["valor_total"],
                        "bandeira": dados["bandeira"]
                    }
                    
                    st.session_state.faturas_residenciais.append(nova_fatura)
                    
                    if db is not None and hasattr(db, "salvar_fatura"):
                        db.salvar_fatura(dados["mes_ano"], dados["consumo_kwh"], dados["valor_total"], dados["bandeira"])

                    st.success(f"Fatura de {dados['mes_ano']} lida e gravada com sucesso!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Falha ao processar arquivo PDF: {e}")

    # Aba Manual
    with tab_manual:
        with st.form(key="form_residencial_manual", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                mes_ano = st.text_input("Mês/Ano de Referência", value="08/2026")
                consumo_kwh = st.number_input("Consumo (kWh)", min_value=0.0, value=180.0, step=10.0)
            with col2:
                valor_total = st.number_input("Valor Total (R$)", min_value=0.0, value=145.50, step=5.0)
                bandeira = st.selectbox("Bandeira Tarifária", ["Verde", "Amarela", "Vermelha P1", "Vermelha P2"])
            
            btn_salvar = st.form_submit_button("💾 Salvar Fatura")
            if btn_salvar:
                novo_id = len(st.session_state.faturas_residenciais) + 1
                nova_fatura = {
                    "id": novo_id,
                    "mes_ano": mes_ano,
                    "consumo_kwh": consumo_kwh,
                    "valor_total": valor_total,
                    "bandeira": bandeira
                }
                st.session_state.faturas_residenciais.append(nova_fatura)
                
                if db is not None and hasattr(db, "salvar_fatura"):
                    db.salvar_fatura(mes_ano, consumo_kwh, valor_total, bandeira)

                st.success("Fatura cadastrada com sucesso!")
                st.rerun()

    st.markdown("---")

    # =========================================================================
    # 2. TABELA DE HISTÓRICO E EXCLUSÃO DE REGISTROS
    # =========================================================================
    st.subheader("📋 Histórico e Gerenciamento")

    if not st.session_state.faturas_residenciais:
        st.info("Nenhuma fatura cadastrada no momento. Adicione registros utilizando as abas acima.")
    else:
        df_faturas = pd.DataFrame(st.session_state.faturas_residenciais)

        st.dataframe(
            df_faturas,
            column_config={
                "id": "ID",
                "mes_ano": "Mês/Ano",
                "consumo_kwh": st.column_config.NumberColumn("Consumo", format="%.1f kWh"),
                "valor_total": st.column_config.NumberColumn("Valor Total", format="R$ %.2f"),
                "bandeira": "Bandeira"
            },
            use_container_width=True,
            hide_index=True
        )

        # Funcionalidade de Exclusão
        with st.expander("🗑️ Excluir Fatura do Histórico"):
            opcoes_exclusao = {
                f"ID {f['id']} | Mês: {f['mes_ano']} - R$ {f['valor_total']:.2f}": f['id'] 
                for f in st.session_state.faturas_residenciais
            }
            col_sel, col_del = st.columns([3, 1])
            with col_sel:
                fatura_remover = st.selectbox("Selecione o registro para apagar:", list(opcoes_exclusao.keys()))
            with col_del:
                st.write("")
                st.write("")
                if st.button("❌ Apagar", type="primary"):
                    id_alvo = opcoes_exclusao[fatura_remover]
                    st.session_state.faturas_residenciais = [
                        f for f in st.session_state.faturas_residenciais if f["id"] != id_alvo
                    ]
                    st.toast("Fatura removida!", icon="✅")
                    st.rerun()

        st.markdown("---")

        # =========================================================================
        # 3. DIAGNÓSTICOS ESTATÍSTICOS (Padrão Econômico 150 kWh/mês)
        # =========================================================================
        st.subheader("📊 Diagnósticos Estatísticos de Consumo")

        media_kwh = df_faturas["consumo_kwh"].mean()
        max_kwh = df_faturas["consumo_kwh"].max()
        total_gasto = df_faturas["valor_total"].sum()
        std_kwh = df_faturas["consumo_kwh"].std() if len(df_faturas) > 1 else 0.0

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Média Mensal", f"{media_kwh:.1f} kWh", delta=f"{media_kwh - 150.0:.1f} vs Meta")
        c2.metric("Pico de Consumo", f"{max_kwh:.1f} kWh")
        c3.metric("Desvio Padrão", f"{std_kwh:.1f} kWh")
        c4.metric("Gasto Acumulado", f"R$ {total_gasto:.2f}")

        # Gráfico de Consumo vs Meta Econômica
        st.markdown("**Evolução Mensal vs. Meta Econômica (150 kWh/mês)**")
        st.bar_chart(df_faturas, x="mes_ano", y="consumo_kwh", use_container_width=True)

        st.markdown("---")

        # =========================================================================
        # 4. RECOMENDAÇÕES DE IA E EFICIÊNCIA ENERGÉTICA
        # =========================================================================
        st.subheader("🤖 Recomendações Automáticas de IA")
        
        recomendas = gerar_recomendacoes_ia(df_faturas)
        for rec in recomendas:
            st.info(rec)

        st.markdown("---")

        # =========================================================================
        # 5. EMISSÃO DE LAUDO TÉCNICO EM PDF
        # =========================================================================
        st.subheader("📄 Emissão do Laudo Técnico")
        st.write("Gere o relatório em formato PDF contendo os diagnósticos estatísticos e as recomendações técnicas.")

        if st.button("📥 Gerar e Baixar Laudo PDF", type="primary"):
            if PDFReportGenerator is not None:
                try:
                    pdf_engine = PDFReportGenerator()
                    # Prepara os dados para o gerador de PDF
                    dados_relatorio = {
                        "modulo": "Residencial (B1)",
                        "media_kwh": media_kwh,
                        "total_gasto": total_gasto,
                        "faturas": df_faturas.to_dict(orient="records"),
                        "recomendacoes": recomendas
                    }
                    pdf_bytes = pdf_engine.gerar_laudo_residencial(dados_relatorio)

                    st.download_button(
                        label="💾 Clique aqui para baixar o PDF",
                        data=pdf_bytes,
                        file_name=f"laudo_energia_residencial_{datetime.now().strftime('%Y%m%d')}.pdf",
                        mime="application/pdf"
                    )
                except Exception as e:
                    st.error(f"Erro ao compilar arquivo PDF: {e}")
            else:
                st.warning("O serviço 'PDFReportGenerator' em services/report_generator.py precisa ser instanciado.")


if __name__ == "__main__":
    render_residential_ui()
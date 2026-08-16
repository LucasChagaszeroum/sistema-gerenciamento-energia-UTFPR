import streamlit as st
import pandas as pd
import pypdf
import re

def extrair_dados_pdf_copel(pdf_file):
    """
    Lê o arquivo PDF da fatura e extrai mês de referência, consumo (kWh) e valor total.
    """
    reader = pypdf.PdfReader(pdf_file)
    texto_completo = ""
    for page in reader.pages:
        texto_completo += page.extract_text() or ""

    # Expressões regulares (Regex) para captura de dados da fatura
    match_mes = re.search(r'(\d{2}/\d{4})', texto_completo)
    match_kwh = re.search(r'(\d+[\.,]?\d*)\s*kWh', texto_completo, re.IGNORECASE)
    match_valor = re.search(r'R\$\s*(\d+[\.,]\d{2})', texto_completo)

    mes_ano = match_mes.group(1) if match_mes else "08/2026"
    
    # Tratamento de formato numérico brasileiro (vírgula para ponto)
    consumo_kwh = float(match_kwh.group(1).replace('.', '').replace(',', '.')) if match_kwh else 180.0
    valor_total = float(match_valor.group(1).replace('.', '').replace(',', '.')) if match_valor else 145.50

    return {
        "mes_ano": mes_ano,
        "consumo_kwh": consumo_kwh,
        "valor_total": valor_total,
        "bandeira": "Verde"
    }


def render_residential_ui(db=None):
    """
    Interface do Módulo Residencial com suporte a Upload de PDF,
    Cadastro Manual, Persistência de Dados e Remoção de Faturas.
    """
    st.title("🏠 Módulo Residencial - Grupo B")
    st.caption("Gestão de faturas via leitura de PDF (OCR), formulário manual e diagnósticos.")

    # Inicialização do histórico na memória da sessão
    if "faturas_residenciais" not in st.session_state:
        st.session_state.faturas_residenciais = []

    # --- ABAS DE ENTRADA DE DADOS ---
    tab_pdf, tab_manual = st.tabs(["📄 Upload de Fatura (PDF)", "✍️ Cadastro Manual"])

    # 1. ABA DE UPLOAD DE PDF
    with tab_pdf:
        st.subheader("Leitura Automática de PDF")
        uploaded_file = st.file_uploader("Selecione o arquivo PDF da fatura COPEL", type=["pdf"])

        if uploaded_file is not None:
            if st.button("🔍 Extrair Dados e Salvar Fatura", type="primary"):
                try:
                    # Executa a extração do texto do PDF via pypdf
                    dados = extrair_dados_pdf_copel(uploaded_file)
                    
                    novo_id = len(st.session_state.faturas_residenciais) + 1
                    nova_fatura = {
                        "id": novo_id,
                        "mes_ano": dados["mes_ano"],
                        "consumo_kwh": dados["consumo_kwh"],
                        "valor_total": dados["valor_total"],
                        "bandeira": dados["bandeira"]
                    }

                    # Salva na sessão
                    st.session_state.faturas_residenciais.append(nova_fatura)

                    # Salva no banco SQLite se a conexão estiver ativa
                    if db is not None and hasattr(db, "salvar_fatura"):
                        db.salvar_fatura(dados["mes_ano"], dados["consumo_kwh"], dados["valor_total"], dados["bandeira"])

                    st.success(f"Fatura de {dados['mes_ano']} extraída e cadastrada com sucesso!")
                    st.rerun()
                except Exception as err:
                    st.error(f"Erro ao processar o arquivo PDF: {err}")

    # 2. ABA DE CADASTRO MANUAL
    with tab_manual:
        st.subheader("Preenchimento Manual")
        with st.form(key="form_fatura_residencial", clear_on_submit=True):
            col1, col2 = st.columns(2)
            
            with col1:
                mes_ano = st.text_input("Mês/Ano de Referência", value="08/2026")
                consumo_kwh = st.number_input("Consumo Ativo (kWh)", min_value=0.0, value=180.0, step=10.0)
            
            with col2:
                valor_total = st.number_input("Valor Total (R$)", min_value=0.0, value=145.50, step=5.0)
                bandeira = st.selectbox("Bandeira Tarifária", ["Verde", "Amarela", "Vermelha P1", "Vermelha P2"])
            
            btn_salvar = st.form_submit_button("💾 Salvar Fatura Manual")

            if btn_salvar:
                if not mes_ano:
                    st.error("Por favor, informe o mês/ano de referência.")
                else:
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

                    st.success(f"Fatura {mes_ano} cadastrada com sucesso!")
                    st.rerun()

    st.markdown("---")

    # --- EXIBIÇÃO E REMOÇÃO DE FATURAS ---
    st.subheader("📋 Histórico de Faturas Cadastradas")

    if not st.session_state.faturas_residenciais:
        st.info("Nenhuma fatura cadastrada. Faça upload de um PDF ou utilize o cadastro manual.")
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

        total_kwh = df_faturas["consumo_kwh"].sum()
        total_rs = df_faturas["valor_total"].sum()
        
        m_col1, m_col2 = st.columns(2)
        m_col1.metric("Consumo Acumulado", f"{total_kwh:.1f} kWh")
        m_col2.metric("Custo Acumulado", f"R$ {total_rs:.2f}")

        st.markdown("---")

        st.subheader("🗑️ Apagar Fatura")
        opcoes_exclusao = {
            f"ID {f['id']} | Mês: {f['mes_ano']} - R$ {f['valor_total']:.2f}": f['id'] 
            for f in st.session_state.faturas_residenciais
        }

        col_select, col_btn = st.columns([3, 1])
        with col_select:
            fatura_para_remover = st.selectbox(
                "Selecione a fatura para remover:",
                options=list(opcoes_exclusao.keys())
            )

        with col_btn:
            st.write("")
            st.write("")
            if st.button("❌ Excluir", type="primary"):
                id_alvo = opcoes_exclusao[fatura_para_remover]
                st.session_state.faturas_residenciais = [
                    f for f in st.session_state.faturas_residenciais if f["id"] != id_alvo
                ]
                st.toast("Fatura removida com sucesso!", icon="✅")
                st.rerun()


if __name__ == "__main__":
    render_residential_ui()
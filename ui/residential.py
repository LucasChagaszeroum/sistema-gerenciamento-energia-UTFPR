import streamlit as st
import pandas as pd

def render_residential_ui(db=None):
    """
    Interface principal do Módulo Residencial (Grupo B).
    Aceita o objeto 'db' para persistência no SQLite e utiliza 'st.session_state'
    para gerenciamento de estado reativo na tela.
    """
    st.title("🏠 Módulo Residencial - Grupo B")
    st.caption("Gerenciamento, histórico de faturas e diagnóstico de consumo.")

    # 1. INICIALIZAÇÃO DO ESTADO DA SESSÃO
    # Mantém o histórico em memória enquanto a aplicação está rodando
    if "faturas_residenciais" not in st.session_state:
        st.session_state.faturas_residenciais = []

    # --- CADASTRAR NOVA FATURA ---
    with st.expander("➕ Cadastrar Nova Fatura", expanded=True):
        with st.form(key="form_fatura_residencial", clear_on_submit=True):
            col1, col2 = st.columns(2)
            
            with col1:
                mes_ano = st.text_input("Mês/Ano de Referência", value="08/2026", help="Exemplo: 08/2026")
                consumo_kwh = st.number_input("Consumo Ativo (kWh)", min_value=0.0, value=180.0, step=10.0)
            
            with col2:
                valor_total = st.number_input("Valor Total (R$)", min_value=0.0, value=145.50, step=5.0)
                bandeira = st.selectbox("Bandeira Tarifária", ["Verde", "Amarela", "Vermelha P1", "Vermelha P2"])
            
            btn_salvar = st.form_submit_button("💾 Salvar Fatura")

            if btn_salvar:
                if not mes_ano:
                    st.error("Por favor, preencha o mês/ano de referência.")
                else:
                    # Gera identificador local
                    novo_id = len(st.session_state.faturas_residenciais) + 1
                    
                    nova_fatura = {
                        "id": novo_id,
                        "mes_ano": mes_ano,
                        "consumo_kwh": consumo_kwh,
                        "valor_total": valor_total,
                        "bandeira": bandeira
                    }
                    
                    # 1. Persistência em memória no Streamlit
                    st.session_state.faturas_residenciais.append(nova_fatura)
                    
                    # 2. Persistência no SQLite (caso o objeto db esteja ativo)
                    if db is not None and hasattr(db, "salvar_fatura"):
                        try:
                            db.salvar_fatura(mes_ano, consumo_kwh, valor_total, bandeira)
                        except Exception as err:
                            st.warning(f"Salvo na sessão, mas houve falha ao gravar no SQLite: {err}")

                    st.success(f"Fatura de {mes_ano} cadastrada com sucesso!")
                    st.rerun()  # Atualiza a interface imediatamente

    st.markdown("---")

    # --- HISTÓRICO E METRICAS DE CONSUMO ---
    st.subheader("📋 Histórico de Faturas Cadastradas")

    if not st.session_state.faturas_residenciais:
        st.info("Nenhuma fatura cadastrada no momento. Utilize o formulário acima para adicionar registros.")
    else:
        # Conversão para DataFrame do Pandas para renderização tabular
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

        # Cálculo de grandezas agregadas via Pandas
        total_kwh = df_faturas["consumo_kwh"].sum()
        total_rs = df_faturas["valor_total"].sum()
        
        m_col1, m_col2 = st.columns(2)
        m_col1.metric("Consumo Acumulado", f"{total_kwh:.1f} kWh")
        m_col2.metric("Custo Acumulado", f"R$ {total_rs:.2f}")

        st.markdown("---")

        # --- EXCLUSÃO DE REGISTROS ---
        st.subheader("🗑️ Apagar Fatura")
        
        # Criação de um dicionário de mapeamento para o selectbox
        opcoes_exclusao = {
            f"ID {f['id']} | Mês: {f['mes_ano']} - R$ {f['valor_total']:.2f}": f['id'] 
            for f in st.session_state.faturas_residenciais
        }

        col_select, col_btn = st.columns([3, 1])

        with col_select:
            fatura_para_remover = st.selectbox(
                "Selecione a fatura para remoção:",
                options=list(opcoes_exclusao.keys())
            )

        with col_btn:
            st.write("")
            st.write("")
            if st.button("❌ Excluir", type="primary"):
                id_alvo = opcoes_exclusao[fatura_para_remover]
                
                # Filtra a lista removendo apenas o elemento selecionado
                st.session_state.faturas_residenciais = [
                    f for f in st.session_state.faturas_residenciais if f["id"] != id_alvo
                ]
                
                st.toast("Fatura removida com sucesso!", icon="✅")
                st.rerun()

# Suporte para execução direta do módulo
if __name__ == "__main__":
    render_residential_ui()
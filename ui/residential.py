import streamlit as st
import pandas as pd

def render_modulo_residencial():
    st.title("🏠 Módulo Residencial - Grupo B")
    st.caption("Gerenciamento e histórico de faturas de energia elétrica.")

    # 1. INICIALIZAÇÃO DO SESSION STATE
    # Garante que a lista de faturas persista entre as reexecuções da página
    if "faturas_residenciais" not in st.session_state:
        st.session_state.faturas_residenciais = []

    # --- ABA DE NAVEGAÇÃO INTERNA OU EXPANDER ---
    with st.expander("➕ Cadastrar Nova Fatura", expanded=True):
        # 2. FORMULÁRIO DE ENTRADA DE DADOS
        # O st.form evita que a página recarregue a cada caractere digitado
        with st.form(key="form_fatura_residencial", clear_on_submit=True):
            col1, col2 = st.columns(2)
            
            with col1:
                mes_ano = st.text_input("Mês/Ano de Referência", value="08/2026", help="Exemplo: 08/2026")
                consumo_kwh = st.number_input("Consumo Ativo (kWh)", min_value=0.0, value=180.0, step=10.0)
            
            with col2:
                valor_total = st.number_input("Valor Total da Fatura (R$)", min_value=0.0, value=145.50, step=5.0)
                bandeira = st.selectbox("Bandeira Tarifária", ["Verde", "Amarela", "Vermelha P1", "Vermelha P2"])
            
            # Botão de submissão do formulário
            btn_salvar = st.form_submit_button("💾 Salvar Fatura")

            if btn_salvar:
                # Validação básica
                if not mes_ano:
                    st.error("Por favor, preencha o mês/ano de referência.")
                else:
                    # Gera um ID único baseado no número atual de itens
                    novo_id = len(st.session_state.faturas_residenciais) + 1
                    
                    # Cria o dicionário com a estrutura da fatura
                    nova_fatura = {
                        "id": novo_id,
                        "mes_ano": mes_ano,
                        "consumo_kwh": consumo_kwh,
                        "valor_total": valor_total,
                        "bandeira": bandeira
                    }
                    
                    # Adiciona a fatura à memória da sessão
                    st.session_state.faturas_residenciais.append(nova_fatura)
                    st.success(f"Fatura do mês {mes_ano} salva com sucesso!")
                    st.rerun()  # Força a atualização da interface para exibir os novos dados

    st.markdown("---")

    # 3. EXIBIÇÃO DAS FATURAS SALVAS
    st.subheader("📋 Histórico de Faturas Cadastradas")

    if not st.session_state.faturas_residenciais:
        st.info("Nenhuma fatura cadastrada até o momento. Preencha o formulário acima para adicionar.")
    else:
        # Transforma a lista de dicionários em um DataFrame do Pandas para exibição
        df_faturas = pd.DataFrame(st.session_state.faturas_residenciais)

        # Renderiza a tabela formatada com visualização do Streamlit
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

        # Métrica de resumo automático do consumo total salvo
        total_kwh = df_faturas["consumo_kwh"].sum()
        total_rs = df_faturas["valor_total"].sum()
        
        m_col1, m_col2 = st.columns(2)
        m_col1.metric("Consumo Acumulado", f"{total_kwh:.1f} kWh")
        m_col2.metric("Custo Acumulado", f"R$ {total_rs:.2f}")

        st.markdown("---")

        # 4. FUNCIONALIDADE DE APAGAR FATURA
        st.subheader("🗑️ Apagar Fatura")
        
        # Mapeia as faturas para uma exibição amigável na caixa de seleção
        opcoes_exclusao = {
            f"ID {f['id']} | Mês: {f['mes_ano']} - R$ {f['valor_total']:.2f}": f['id'] 
            for f in st.session_state.faturas_residenciais
        }

        col_select, col_btn = st.columns([3, 1])

        with col_select:
            fatura_para_remover = st.selectbox(
                "Selecione a fatura que deseja excluir:",
                options=list(opcoes_exclusao.keys())
            )

        with col_btn:
            st.write("")  # Ajuste vertical do alinhamento do botão
            st.write("")
            if st.button("❌ Excluir", type="primary"):
                id_alvo = opcoes_exclusao[fatura_para_remover]
                
                # Reconstrói a lista mantendo apenas os itens com ID diferente do selecionado
                st.session_state.faturas_residenciais = [
                    f for f in st.session_state.faturas_residenciais if f["id"] != id_alvo
                ]
                
                st.toast("Fatura removida com sucesso!", icon="✅")
                st.rerun()  # Atualiza a página imediatamente

# Para rodar diretamente se este arquivo for executado
if __name__ == "__main__":
    render_modulo_residencial()
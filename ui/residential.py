import streamlit as st
import pandas as pd
from data.database import DatabaseManager
from services.api_service import RealAPIService

def render_residential_ui(db: DatabaseManager):
    """Renderiza a interface do Módulo Residencial com opções de gestão de faturas (CRUD) e Reset."""
    st.header("🏠 Módulo Residencial — Gestão de Consumo & Faturas (B1)")
    
    # 1. Carrega o histórico atual de faturas do banco
    df_faturas = db.carregar_faturas_residenciais()
    
    # Se estiver vazio na primeira execução, popula com os dados padrões
    if df_faturas.empty:
        db.resetar_faturas_residenciais()
        df_faturas = db.carregar_faturas_residenciais()

    # --- BLOCO DE AÇÕES: ADICIONAR, REMOVER E RESETAR ---
    st.subheader("⚙️ Painel de Gerenciamento de Faturas")
    
    col_add, col_del, col_reset = st.columns([2, 2, 1])

    # AÇÃO 1: Adicionar Nova Fatura
    with col_add:
        with st.expander("➕ Adicionar Nova Fatura", expanded=False):
            with st.form("form_add_fatura", clear_on_submit=True):
                mes_input = st.text_input("Mês/Ano (ex: 2026-05)", value="2026-05")
                consumo_input = st.number_input("Consumo (kWh)", min_value=1.0, value=300.0, step=10.0)
                bandeira_input = st.selectbox("Bandeira Tarifária", ["VERDE", "AMARELA", "VERMELHA_P1", "VERMELHA_P2"])
                
                btn_salvar = st.form_submit_button("Salvar Fatura")
                
                if btn_salvar:
                    # Calcula o valor estimado via API Copel/ANEEL
                    calculo = RealAPIService.calcular_fatura_copel(consumo_input, bandeira_input)
                    valor_total = calculo["valor_total_r$"]
                    
                    # Salva no SQLite
                    db.adicionar_fatura_residencial(mes_input, consumo_input, bandeira_input, valor_total)
                    st.success(f"Fatura de {mes_input} adicionada com sucesso!")
                    st.rerun() # Recarrega a página para atualizar os gráficos

    # AÇÃO 2: Remover Fatura Existente
    with col_del:
        with st.expander("🗑️ Remover Fatura", expanded=False):
            if not df_faturas.empty:
                # Prepara opções formatadas para o selectbox
                opcoes_fatura = {
                    f"ID {row['id']} - {row['mes_ano']} ({row['consumo_kwh']} kWh)": row['id']
                    for _, row in df_faturas.iterrows()
                }
                fatura_selecionada = st.selectbox("Selecione a fatura para deletar:", list(opcoes_fatura.keys()))
                
                if st.button("Confirmar Exclusão", type="primary"):
                    id_para_deletar = opcoes_fatura[fatura_selecionada]
                    db.deletar_fatura_residencial(id_para_deletar)
                    st.warning("Fatura removida com sucesso!")
                    st.rerun()
            else:
                st.info("Nenhuma fatura cadastrada para exclusão.")

    # AÇÃO 3: Resetar Dados (Botão de Limpeza)
    with col_reset:
        st.write(" ") # Espaçamento para alinhar com os expanders
        if st.button("🔄 Resetar", help="Restaura o histórico para os valores padrões"):
            db.resetar_faturas_residenciais()
            st.toast("Banco de dados residencial resetado para os valores padrões!", icon="🧹")
            st.rerun()

    st.markdown("---")

    # --- BLOCO DE DASHBOARD E EXIBIÇÃO DE DADOS ---
    st.subheader("📊 Resumo do Histórico Residencial")

    if not df_faturas.empty:
        # Métricas Consolidadas
        m1, m2, m3, m4 = st.columns(4)
        total_kwh = df_faturas["consumo_kwh"].sum()
        total_gasto = df_faturas["valor_total"].sum()
        media_kwh = df_faturas["consumo_kwh"].mean()
        media_gasto = df_faturas["valor_total"].mean()

        m1.metric("Consumo Acumulado", f"{total_kwh:,.1f} kWh")
        m2.metric("Gasto Acumulado", f"R$ {total_gasto:,.2f}")
        m3.metric("Média Mensal (kWh)", f"{media_kwh:.1f} kWh")
        m4.metric("Média Mensal (R$)", f"R$ {media_gasto:,.2f}")

        # Tabela e Gráfico
        st.subheader("📈 Evolução de Consumo e Custos")
        
        tab1, tab2 = st.tabs(["📊 Gráfico de Consumo", "📋 Tabela Detalhada"])
        
        with tab1:
            # Gráfico de barras simples usando o próprio Streamlit
            df_chart = df_faturas.sort_values(by="id", ascending=True)
            st.bar_chart(df_chart.set_index("mes_ano")[["consumo_kwh", "valor_total"]])
            
        with tab2:
            st.dataframe(
                df_faturas.style.format({
                    "consumo_kwh": "{:.1f} kWh",
                    "valor_total": "R$ {:.2f}"
                }),
                use_container_width=True
            )
    else:
        st.info("Nenhuma fatura encontrada. Utilize o painel acima para adicionar ou clique em Resetar.")
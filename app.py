import streamlit as st
from data.database import DatabaseManager
from ui.residential import render_residential_ui

# Configuração da Página
st.set_page_config(page_title="Plataforma de Inteligência Energética UTFPR", page_icon="⚡", layout="wide")

# Inicializa Banco de Dados
db = DatabaseManager()

# Session State para controle de navegação
if 'perfil' not in st.session_state:
    st.session_state['perfil'] = None

# Sidebar — Navegação Global
st.sidebar.title("⚡ Inteligência Energética")
if st.sidebar.button("🏠 Página Inicial"):
    st.session_state['perfil'] = None
    st.rerun()

# ROUTING DE PERFIS
perfil_atual = st.session_state['perfil']

if perfil_atual is None:
    st.title("⚡ Plataforma Integrada de Inteligência Energética — UTFPR")
    st.markdown("### Selecione o perfil de operação:")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.info("### 🏠 RESIDENCIAL")
        st.write("Gestão de faturas, histórico mensal de consumo, detecção de anomalias e recomendações de economia.")
        if st.button("Acessar Residencial", use_container_width=True):
            st.session_state['perfil'] = "RESIDENCIAL"
            st.rerun()

    with col2:
        st.warning("### 🏭 INDUSTRIAL")
        st.write("Monitoramento de demanda horária, fator de potência, curvas de carga e prevenção de multas.")
        if st.button("Acessar Industrial", use_container_width=True):
            st.session_state['perfil'] = "INDUSTRIAL"
            st.rerun()

    with col3:
        st.success("### 🔬 PESQUISA (IC)")
        st.write("Modelos preditivos, Ensemble, Transformers PyTorch, SHAP, Drift (PSI) e validação Diebold-Mariano.")
        if st.button("Acessar Pesquisa", use_container_width=True):
            st.session_state['perfil'] = "PESQUISA"
            st.rerun()

elif perfil_atual == "RESIDENCIAL":
    render_residential_ui(db)

elif perfil_atual == "INDUSTRIAL":
    st.title("🏭 Módulo Industrial — Curva de Carga e Demanda")
    st.info("Modulo Industrial pronto para integração com o pipeline avançado de Machine Learning.")

elif perfil_atual == "PESQUISA":
    st.title("🔬 Módulo de Pesquisa & Experimentos (Iniciação Científica)")
    st.info("Aqui permanecem o Optuna, Ensemble, Transformer PyTorch, Diebold-Mariano e XAI.")
import sys
import os

# Adiciona o diretório raiz do projeto ao PYTHONPATH para evitar ModuleNotFoundError na nuvem
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
from data.database import DatabaseManager
from ui.residential import render_residential_ui

# Configuração global da página
st.set_page_config(page_title="Plataforma de Inteligência Energética UTFPR", page_icon="⚡", layout="wide")

# Inicialização do banco de dados relacional
db = DatabaseManager()

# Gerenciamento de estado de navegação (session_state)
if 'perfil' not in st.session_state:
    st.session_state['perfil'] = None

# Barra lateral para controle global
st.sidebar.title("⚡ Inteligência Energética")
if st.sidebar.button("🏠 Página Inicial"):
    st.session_state['perfil'] = None
    st.rerun()  # Reinicia o fluxo do script para voltar à tela principal

# Resgate do perfil ativo
perfil_atual = st.session_state['perfil']

# Roteamento principal da aplicação
if perfil_atual is None:
    st.title("⚡ Plataforma Integrada de Inteligência Energética — UTFPR")
    st.markdown("### Selecione o perfil de operação:")

    # Divisão da tela principal em três colunas operacionais
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
    # Renderização da interface residencial
    render_residential_ui(db)

elif perfil_atual == "INDUSTRIAL":
    st.title("🏭 Módulo Industrial — Curva de Carga e Demanda")
    st.info("Módulo Industrial pronto para integração com o pipeline avançado de Machine Learning.")

elif perfil_atual == "PESQUISA":
    st.title("🔬 Módulo de Pesquisa & Experimentos (Iniciação Científica)")
    st.info("Aqui permanecem o Optuna, Ensemble, Transformer PyTorch, Diebold-Mariano e XAI.")
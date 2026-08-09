import sys
import os

# Adiciona a raiz do projeto ao PYTHONPATH
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
from data.database import DatabaseManager
from ui.residential import render_residential_ui
from ui.industrial import render_industrial_ui
from ui.research import render_research_ui

st.set_page_config(page_title="Plataforma de Inteligência Energética UTFPR", page_icon="⚡", layout="wide")

db = DatabaseManager()

if 'perfil' not in st.session_state:
    st.session_state['perfil'] = None

st.sidebar.title("⚡ Inteligência Energética")
if st.sidebar.button("🏠 Página Inicial"):
    st.session_state['perfil'] = None
    st.rerun()

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
    render_industrial_ui(db)

elif perfil_atual == "PESQUISA":
    render_research_ui(db)
import sys
import os

# Adiciona o diretório raiz ao PYTHONPATH do sistema
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
from data.database import DatabaseManager
from ui.residential import render_residential_ui
from ui.industrial import render_industrial_ui
from ui.research import render_research_ui

# Configuração da página web no Streamlit
st.set_page_config(
    page_title="Plataforma Integrada de Inteligência Energética — UTFPR",
    page_icon="⚡",
    layout="wide"
)

# Inicializa o banco de dados SQLite
db = DatabaseManager()

# Gerenciamento de estado de navegação
if 'perfil' not in st.session_state:
    st.session_state['perfil'] = None

# Barra Lateral
st.sidebar.title("⚡ Inteligência Energética")
if st.sidebar.button("🏠 Página Inicial", use_container_width=True):
    st.session_state['perfil'] = None
    st.rerun()

perfil_atual = st.session_state['perfil']

# Roteamento de telas
if perfil_atual is None:
    st.title("⚡ Plataforma Integrada de Inteligência Energética — UTFPR")
    st.markdown("### Selecione o perfil de operação:")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.info("### 🏠 RESIDENCIAL")
        st.write("Gestão de faturas (B1), leitura via OCR, diagnósticos estatísticos, recomendações de IA e laudo em PDF.")
        if st.button("Acessar Residencial", use_container_width=True):
            st.session_state['perfil'] = "RESIDENCIAL"
            st.rerun()

    with col2:
        st.warning("### 🏭 INDUSTRIAL")
        st.write("Telemetria de demanda horária em kW, fator de potência, curvas de carga e prevenção de multas da ANEEL.")
        if st.button("Acessar Industrial", use_container_width=True):
            st.session_state['perfil'] = "INDUSTRIAL"
            st.rerun()

    with col3:
        st.success("### 🔬 PESQUISA (IC)")
        st.write("Modelos em Ensemble, previsão quantílica, XAI (SHAP/PDP), Data Drift (PSI) e teste de Diebold-Mariano.")
        if st.button("Acessar Pesquisa", use_container_width=True):
            st.session_state['perfil'] = "PESQUISA"
            st.rerun()

elif perfil_atual == "RESIDENCIAL":
    render_residential_ui(db)

elif perfil_atual == "INDUSTRIAL":
    render_industrial_ui(db)

elif perfil_atual == "PESQUISA":
    render_research_ui(db)
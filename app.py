import sqlite3
import os
import requests
from bs4 import BeautifulSoup

import pandas as pd
import numpy as np
from scipy import stats
import sympy as sp

# Algoritmos de Aprendizado de Máquina (Previsão de Demanda e Anomalias)
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import IsolationForest

# Bibliotecas para gráficos técnicos e interface web
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Módulos do ReportLab para geração de laudos formais em PDF
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors


# =========================================================================
# 1. CAMADA DE BANCO DE DADOS (SQLite + Pandas)
# =========================================================================
class EnergyDatabase:
    """Gerencia a persistência relacional, operações CRUD e importação de planilhas."""
    
    def __init__(self, db_name: str = "sistema_energia.db"):
        self.db_name = db_name  # Define o nome do arquivo do banco SQLite
        self._init_db()         # Garante a criação da tabela na inicialização

    def _get_connection(self):
        # Estabelece conexão com o banco de dados local SQLite
        return sqlite3.connect(self.db_name)

    def _init_db(self):
        # Cria a tabela principal de medições se ela ainda não existir
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS leituras (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ponto TEXT NOT NULL,
                    demanda_kw REAL NOT NULL,
                    fator_potencia REAL DEFAULT 0.92,
                    data_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()

    def inserir_leitura(self, ponto: str, demanda_kw: float, fator_potencia: float = 0.92, data_hora: str = None):
        # Permite salvar leituras manuais indicando data/hora específica ou valor padrão
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if data_hora:
                cursor.execute(
                    "INSERT INTO leituras (ponto, demanda_kw, fator_potencia, data_hora) VALUES (?, ?, ?, ?)",
                    (ponto, demanda_kw, fator_potencia, data_hora)
                )
            else:
                cursor.execute(
                    "INSERT INTO leituras (ponto, demanda_kw, fator_potencia) VALUES (?, ?, ?)",
                    (ponto, demanda_kw, fator_potencia)
                )
            conn.commit()

    def importar_dados_csv_excel(self, df_upload: pd.DataFrame) -> bool:
        """Sanitiza colunas e insere medições em lote no banco SQLite."""
        df_upload.columns = [c.lower().strip() for c in df_upload.columns]
        
        if 'ponto' in df_upload.columns and 'demanda_kw' in df_upload.columns:
            if 'fator_potencia' not in df_upload.columns:
                df_upload['fator_potencia'] = 0.92

            df_upload['demanda_kw'] = pd.to_numeric(df_upload['demanda_kw'], errors='coerce')
            df_upload['fator_potencia'] = pd.to_numeric(df_upload['fator_potencia'], errors='coerce').fillna(0.92)
            
            df_upload = df_upload.dropna(subset=['demanda_kw'])

            cols = ['ponto', 'demanda_kw', 'fator_potencia']
            if 'data_hora' in df_upload.columns:
                cols.append('data_hora')

            with self._get_connection() as conn:
                df_upload[cols].to_sql('leituras', conn, if_exists='append', index=False)
            return True
        return False

    def carregar_dados_df(self) -> pd.DataFrame:
        """Carrega medições do banco, converte timestamps e executa o triângulo de potências."""
        with self._get_connection() as conn:
            query = "SELECT id, ponto, demanda_kw, fator_potencia, data_hora FROM leituras"
            df = pd.read_sql_query(query, conn)
        
        if not df.empty:
            # Converte a coluna temporal para o tipo datetime do Pandas
            df['data_hora'] = pd.to_datetime(df['data_hora'], errors='coerce')
            
            # S = P / FP (kVA) - Potência Aparente Vetorial
            df['potencia_aparente_kva'] = df['demanda_kw'] / df['fator_potencia']
            
            # Q = sqrt(S^2 - P^2) (kvar) - Potência Reativa Vetorial
            df['potencia_reativa_kvar'] = np.sqrt(
                np.maximum(0, df['potencia_aparente_kva']**2 - df['demanda_kw']**2)
            )
        else:
            df['potencia_aparente_kva'] = pd.Series(dtype='float64')
            df['potencia_reativa_kvar'] = pd.Series(dtype='float64')
            
        return df

    def atualizar_leitura(self, id_registro: int, novo_valor_kw: float, novo_fp: float):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE leituras SET demanda_kw = ?, fator_potencia = ? WHERE id = ?", 
                (novo_valor_kw, novo_fp, id_registro)
            )
            conn.commit()

    def deletar_leitura(self, id_registro: int):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM leituras WHERE id = ?", (id_registro,))
            conn.commit()


# =========================================================================
# 2. ANÁLISE CIENTÍFICA, MACHINE LEARNING & ÁLGEBRA SIMBÓLICA
# =========================================================================
class EnergyAnalytics:
    """Módulo responsável por estatística, previsão por IA e detecção de anomalias."""

    @staticmethod
    def analise_estatistica(df: pd.DataFrame) -> dict:
        if df.empty:
            return {}

        demandas = df['demanda_kw'].to_numpy()
        fps = df['fator_potencia'].to_numpy()

        media_p = float(np.mean(demandas))
        desvio_p = float(np.std(demandas, ddof=1)) if len(demandas) > 1 else 0.0
        pico_p = float(np.max(demandas))
        min_p = float(np.min(demandas))
        
        fator_carga = media_p / pico_p if pico_p > 0 else 0.0
        media_fp = float(np.mean(fps))

        return {
            "total_amostras": len(demandas),
            "media_kw": media_p,
            "desvio_padrao": desvio_p,
            "pico_kw": pico_p,
            "minimo_kw": min_p,
            "fator_carga": fator_carga,
            "fp_medio": media_fp
        }

    @staticmethod
    def prever_demanda_futura(df: pd.DataFrame, dias_previsao: int = 30) -> pd.DataFrame:
        """Aplica Regressão Linear para projetar a tendência de consumo nos próximos N dias."""
        df_temp = df.dropna(subset=['data_hora']).sort_values('data_hora').copy()
        
        if len(df_temp) < 3:
            return pd.DataFrame()  # Requer pelo menos 3 registros para ajuste de tendência

        # Converte datas em valores numéricos sequenciais (dias desde a primeira medição)
        data_minima = df_temp['data_hora'].min()
        df_temp['dias_num'] = (df_temp['data_hora'] - data_minima).dt.total_seconds() / (24 * 3600)

        X = df_temp[['dias_num']].values
        y = df_temp['demanda_kw'].values

        # Treinamento do modelo de regressão linear do Scikit-Learn
        modelo = LinearRegression()
        modelo.fit(X, y)

        # Criação do vetor de tempo futuro para projeção
        ultimo_dia_num = df_temp['dias_num'].max()
        dias_futuros = np.linspace(ultimo_dia_num + 1, ultimo_dia_num + dias_previsao, dias_previsao).reshape(-1, 1)
        predicoes_kw = modelo.predict(dias_futuros)

        # Reconstrução das datas futuras para montagem da tabela e gráfico
        datas_futuras = [data_minima + pd.Timedelta(days=float(d[0])) for d in dias_futuros]

        df_previsao = pd.DataFrame({
            'data_hora': datas_futuras,
            'demanda_prevista_kw': np.maximum(0, predicoes_kw)  # Evita demanda negativa em projeções
        })
        
        return df_previsao

    @staticmethod
    def detectar_anomalias(df: pd.DataFrame, contaminacao: float = 0.05) -> pd.DataFrame:
        """Utiliza Isolation Forest para identificar fugas de corrente e surtos operacionais fora do padrão."""
        df_anom = df.copy()
        if len(df_anom) < 5:
            df_anom['anomalia'] = 1  # Retorna padrão normal se houver amostras insuficientes
            return df_anom

        X = df_anom[['demanda_kw', 'fator_potencia']].values

        # Inicializa o detector de anomalias com a taxa de contaminação estimada
        detector = IsolationForest(contamination=contaminacao, random_state=42)
        
        # Predição: 1 representa padrão normal e -1 representa anomalia identificada
        df_anom['anomalia'] = detector.fit_predict(X)
        return df_anom

    @staticmethod
    def modelar_triangulo_potencias_simbolico() -> dict:
        P, FP = sp.symbols('P FP')
        S = P / FP
        Q = sp.sqrt(S**2 - P**2)
        dQ_dFP = sp.diff(Q, FP)
        
        return {
            "potencia_aparente_latex": sp.latex(S),
            "potencia_reativa_latex": sp.latex(sp.simplify(Q)),
            "sensibilidade_fp_latex": sp.latex(sp.simplify(dQ_dFP))
        }

    @staticmethod
    def calcular_tarifacao_dupla(df: pd.DataFrame, tarifa_kwh: float) -> dict:
        if df.empty:
            return {}

        p_media_kw = float(df['demanda_kw'].mean())

        consumo_ind_hora_kwh = p_media_kw * 1.0
        custo_ind_hora = consumo_ind_hora_kwh * tarifa_kwh

        consumo_ind_mes_kwh = p_media_kw * 24 * 30
        custo_ind_mes = consumo_ind_mes_kwh * tarifa_kwh

        consumo_ind_ano_kwh = p_media_kw * 24 * 365
        custo_ind_ano = consumo_ind_ano_kwh * tarifa_kwh

        return {
            "p_media_kw": p_media_kw,
            "custo_ind_hora": custo_ind_hora,
            "custo_ind_mes": custo_ind_mes,
            "custo_ind_ano": custo_ind_ano,
            "consumo_ind_ano_kwh": consumo_ind_ano_kwh
        }


# =========================================================================
# 3. SCRAPING E PARSER TARIFÁRIO DA ANEEL
# =========================================================================
class TariffScraper:
    """Obtém e processa planilhas e dados tarifários oficiais da ANEEL."""

    @staticmethod
    def processar_planilha_aneel(df_aneel: pd.DataFrame) -> float:
        """Extrai o valor médio da tarifa residencial B1 (R$/kWh) de uma planilha da ANEEL."""
        df_aneel.columns = [str(c).lower().strip() for c in df_aneel.columns]
        
        # Procura por colunas que contenham termos referentes a tarifa ou valor
        col_tarifa = [c for c in df_aneel.columns if 'vlr' in c or 'tarifa' in c or 'kwh' in c]
        
        if col_tarifa:
            valores_validos = pd.to_numeric(df_aneel[col_tarifa[0]], errors='coerce').dropna()
            if not valores_validos.empty:
                return float(valores_validos.mean())
        
        return 0.75  # Retorna o valor de referência padrão em caso de ausência dos dados

    @staticmethod
    def obter_cotacao_web() -> dict:
        url = "https://www.epe.gov.br/pt"
        headers = {'User-Agent': 'Mozilla/5.0'}
        try:
            response = requests.get(url, headers=headers, timeout=3)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                title = soup.title.string.strip() if soup.title else "EPE Brasil"
                return {"status": "Online", "fonte": title, "tarifa_estimada_kwh": 0.75}
        except Exception:
            pass
        
        return {"status": "Simulado (Offline)", "fonte": "Tabela Referência ANEEL", "tarifa_estimada_kwh": 0.75}


# =========================================================================
# 4. AUTOMAÇÃO DE RELATÓRIOS PDF (ReportLab)
# =========================================================================
class PDFReportGenerator:
    """Gera relatórios técnicos formais em PDF com diagnósticos do sistema."""

    @staticmethod
    def gerar_relatorio_pdf(filename: str, estatisticas: dict, total_anomalias: int = 0) -> str:
        doc = SimpleDocTemplate(filename, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []

        title = Paragraph("<b>RELATÓRIO DE ANÁLISE DE CARGA E INTELIGÊNCIA - UTFPR</b>", styles['Title'])
        story.append(title)
        story.append(Spacer(1, 15))

        sub = Paragraph("Iniciação Científica - Automação e Gerenciamento Energético", styles['Heading2'])
        story.append(sub)
        story.append(Spacer(1, 20))

        data = [
            ["Métrica Analisada", "Valor Apurado"],
            ["Total de Medições", str(estatisticas.get('total_amostras', 0))],
            ["Média da Demanda (kW)", f"{estatisticas.get('media_kw', 0):.2f}"],
            ["Demanda de Pico (kW)", f"{estatisticas.get('pico_kw', 0):.2f}"],
            ["Fator de Potência Médio", f"{estatisticas.get('fp_medio', 0):.2f}"],
            ["Anomalias Detectadas (Isolation Forest)", str(total_anomalias)]
        ]

        tabela = Table(data, colWidths=[240, 160])
        tabela.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#003366')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f5f5f5')),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey)
        ]))

        story.append(tabela)
        story.append(Spacer(1, 20))

        doc.build(story)
        return filename


# =========================================================================
# 5. INTERFACE DASHBOARD (Streamlit)
# =========================================================================
st.set_page_config(page_title="Sistema de Energia - IC UTFPR", page_icon="⚡", layout="wide")

db = EnergyDatabase()

st.title("⚡ Sistema Integrado de Gerenciamento de Energia & Inteligência")
st.caption("Projeto de Iniciação Científica — Autor: Lucas Chagas | UTFPR")

st.sidebar.header("🔧 Operações do Sistema")
menu_op = st.sidebar.selectbox(
    "Escolha uma Ação:",
    [
        "Dashboard & Analytics", 
        "Análise Temporal & IA", 
        "Inserir Leitura Única", 
        "Importar CSV/Excel", 
        "Gerenciar Registros", 
        "Tarifação & Dados ANEEL"
    ]
)

df = db.carregar_dados_df()

# -------------------------------------------------------------------------
# TELAS DO SISTEMA
# -------------------------------------------------------------------------
if menu_op == "Dashboard & Analytics":
    st.subheader("📊 Painel Geral de Consumo e Detecção de Anomalias")
    
    if df.empty:
        st.info("Nenhum dado cadastrado. Cadastre medições usando o menu lateral.")
    else:
        stats_data = EnergyAnalytics.analise_estatistica(df)
        
        # Processa a detecção automática de anomalias com Isolation Forest
        df_anomalia = EnergyAnalytics.detectar_anomalias(df)
        num_anomalias = (df_anomalia['anomalia'] == -1).sum()

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Demanda Média", f"{stats_data['media_kw']:.2f} kW")
        c2.metric("Demanda Máxima", f"{stats_data['pico_kw']:.2f} kW")
        c3.metric("FP Médio", f"{stats_data['fp_medio']:.2f}")
        c4.metric(
            "Anomalias de Carga", 
            f"{num_anomalias} ponto(s)", 
            delta="Atenção" if num_anomalias > 0 else "Operação Normal",
            delta_color="inverse" if num_anomalias > 0 else "normal"
        )

        st.divider()

        col_graf, col_sym = st.columns([2, 1])

        with col_graf:
            st.markdown("### Monitoramento de Anomalias na Curva de Potência")
            
            # Adiciona identificação visual para anomalias detectadas
            df_anomalia['status'] = df_anomalia['anomalia'].map({1: 'Operação Normal', -1: 'Anomalia Detectada'})
            
            fig = px.scatter(
                df_anomalia,
                x='demanda_kw',
                y='fator_potencia',
                color='status',
                hover_data=['ponto'],
                color_discrete_map={'Operação Normal': '#003366', 'Anomalia Detectada': '#FF0000'},
                title="Dispersão: Demanda vs. Fator de Potência"
            )
            st.plotly_chart(fig, use_container_width=True)

        with col_sym:
            st.markdown("### 🧮 Modelagem Matemática (SymPy)")
            simb = EnergyAnalytics.modelar_triangulo_potencias_simbolico()
            st.latex(r"S = \frac{P}{FP}, \quad Q = \sqrt{S^2 - P^2}")
            st.write("**Potência Reativa Simbólica ($Q$):**")
            st.latex(f"Q = {simb['potencia_reativa_latex']}")

        st.divider()

        if st.button("Gerar Relatório Técnico PDF"):
            pdf_name = "Relatorio_Energia_UTFPR.pdf"
            PDFReportGenerator.gerar_relatorio_pdf(pdf_name, stats_data, total_anomalias=int(num_anomalias))
            
            with open(pdf_name, "rb") as pdf_file:
                st.download_button("📥 Baixar Relatório Técnico PDF", data=pdf_file, file_name=pdf_name, mime="application/pdf")

elif menu_op == "Análise Temporal & IA":
    st.subheader("📈 Séries Temporais e Predição de Demanda Futura com IA")
    
    if df.empty or df['data_hora'].dropna().empty:
        st.warning("É necessário possuir registros cadastrados com data e hora para habilitar os módulos de inteligência temporal.")
    else:
        st.markdown("### 1. Histórico e Curva de Carga no Tempo")
        
        # Agrupamento e resampling temporal
        df_temporal = df.dropna(subset=['data_hora']).sort_values('data_hora')
        
        fig_temp = px.line(
            df_temporal, 
            x='data_hora', 
            y='demanda_kw', 
            color='ponto', 
            markers=True,
            title="Evolução Temporal da Demanda Ativa (kW)"
        )
        st.plotly_chart(fig_temp, use_container_width=True)

        st.divider()

        st.markdown("### 2. Previsão de Demanda Futura (Machine Learning - Scikit-Learn)")
        dias_proj = st.slider("Selecione o horizonte de projeção em dias:", min_value=7, max_value=60, value=30)
        
        df_prev = EnergyAnalytics.prever_demanda_futura(df_temporal, dias_previsao=dias_proj)
        
        if not df_prev.empty:
            fig_prev = go.Figure()
            
            # Adiciona linha com dados históricos
            fig_prev.add_trace(go.Scatter(
                x=df_temporal['data_hora'], y=df_temporal['demanda_kw'],
                mode='lines+markers', name='Histórico Real', line=dict(color='#003366')
            ))
            
            # Adiciona linha com a projeção futura do modelo
            fig_prev.add_trace(go.Scatter(
                x=df_prev['data_hora'], y=df_prev['demanda_prevista_kw'],
                mode='lines+markers', name='Projeção IA', line=dict(color='#FF7F0E', dash='dash')
            ))
            
            fig_prev.update_layout(title="Tendência e Previsão de Carga para os Próximos Dias", xaxis_title="Data", yaxis_title="Demanda (kW)")
            st.plotly_chart(fig_prev, use_container_width=True)
        else:
            st.info("Cadastre pelo menos 3 leituras em datas distintas para habilitar a projeção por Inteligência Artificial.")

elif menu_op == "Inserir Leitura Única":
    st.subheader("➕ Novo Registro Manual de Demanda")
    
    with st.form("form_inserir"):
        ponto = st.text_input("Nome da Subestação / Ponto de Medição", placeholder="Ex: SE-01 Bloco A")
        demanda = st.number_input("Demanda Consumida (kW)", min_value=0.0, step=0.1)
        fp = st.number_input("Fator de Potência (FP)", min_value=0.01, max_value=1.0, value=0.92, step=0.01)
        data_custom = st.date_input("Data da Medição")
        
        btn_submit = st.form_submit_button("Salvar Registro")
        
        if btn_submit:
            if ponto and demanda > 0:
                data_str = data_custom.strftime("%Y-%m-%d 12:00:00")
                db.inserir_leitura(ponto, demanda, fp, data_str)
                st.success(f"Leitura registrada com sucesso para {data_str}!")
                st.rerun()

elif menu_op == "Importar CSV/Excel":
    st.subheader("📁 Importação Massiva de Arquivos de Medição")
    st.markdown("Envie planilhas contendo as colunas: **`ponto`**, **`demanda_kw`**, **`fator_potencia`** e **`data_hora`**.")
    
    arquivo_carregado = st.file_uploader("Selecione o arquivo de medições", type=["csv", "xlsx"])
    
    if arquivo_carregado is not None:
        try:
            df_import = pd.read_csv(arquivo_carregado) if arquivo_carregado.name.endswith('.csv') else pd.read_excel(arquivo_carregado)
            st.dataframe(df_import.head(), use_container_width=True)
            
            if st.button("Gravar Registros no Banco SQLite"):
                if db.importar_dados_csv_excel(df_import):
                    st.success("Dados salvos com sucesso!")
                    st.rerun()
        except Exception as e:
            st.error(f"Erro no processamento: {e}")

elif menu_op == "Gerenciar Registros":
    st.subheader("⚙️ Visualização e Edição de Registros (CRUD)")
    if not df.empty:
        st.dataframe(df, use_container_width=True)
        
        col_ed, col_del = st.columns(2)
        with col_ed:
            id_edit = st.selectbox("ID para editar", df['id'].tolist())
            novo_val = st.number_input("Novo Valor (kW)", min_value=0.0, step=0.1)
            novo_fp = st.number_input("Novo FP", min_value=0.01, max_value=1.0, value=0.92, step=0.01)
            if st.button("Atualizar"):
                db.atualizar_leitura(id_edit, novo_val, novo_fp)
                st.rerun()

        with col_del:
            id_del = st.selectbox("ID para remover", df['id'].tolist(), key="del_sel")
            if st.button("Excluir", type="primary"):
                db.deletar_leitura(id_del)
                st.rerun()

elif menu_op == "Tarifação & Dados ANEEL":
    st.subheader("🏛️ Integração Tarifária Oficial (ANEEL e Mercado)")
    st.markdown("Carregue uma planilha oficial de tarifas publicadas pela **ANEEL** ou concessionárias para atualizar a precificação do sistema.")
    
    planilha_aneel = st.file_uploader("Upload da Tabela Tarifária ANEEL (.xlsx / .csv)", type=["xlsx", "csv"])
    
    tarifa_aplicada = 0.75  # Valor padrão de referência
    
    if planilha_aneel is not None:
        try:
            df_aneel = pd.read_csv(planilha_aneel) if planilha_aneel.name.endswith('.csv') else pd.read_excel(planilha_aneel)
            tarifa_calculada = TariffScraper.processar_planilha_aneel(df_aneel)
            
            if tarifa_calculada > 0:
                tarifa_aplicada = tarifa_calculada
                st.success(f"Tarifa média extraída com sucesso da planilha da ANEEL: **R$ {tarifa_aplicada:.4f} / kWh**")
        except Exception as e:
            st.warning(f"Não foi possível ler a planilha automaticamente. Mantendo tarifa padrão. Erro: {e}")

    st.divider()
    
    if not df.empty:
        custos = EnergyAnalytics.calcular_tarifacao_dupla(df, tarifa_aplicada)
        st.markdown(f"### Custos Operacionais Atualizados (Tarifa Base: R$ {tarifa_aplicada:.4f}/kWh)")
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Custo Horário", f"R$ {custos['custo_ind_hora']:,.2f}/h")
        c2.metric("Projeção Mensal", f"R$ {custos['custo_ind_mes']:,.2f}/mês")
        c3.metric("Projeção Anual", f"R$ {custos['custo_ind_ano']:,.2f}/ano")
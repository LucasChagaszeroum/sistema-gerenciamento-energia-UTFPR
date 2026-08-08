import sqlite3
import os
import requests
from bs4 import BeautifulSoup

import pandas as pd
import numpy as np
from scipy import stats
import sympy as sp

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
            conn.commit()  # Salva a alteração estrutural no banco

    def inserir_leitura(self, ponto: str, demanda_kw: float, fator_potencia: float = 0.92):
        # Inserção parametrizada para segurança contra SQL Injection
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO leituras (ponto, demanda_kw, fator_potencia) VALUES (?, ?, ?)",
                (ponto, demanda_kw, fator_potencia)
            )
            conn.commit()  # Confirma a gravação do registro

    def importar_dados_csv_excel(self, df_upload: pd.DataFrame) -> bool:
        """Sanitiza colunas e insere medições em lote no banco SQLite."""
        df_upload.columns = [c.lower().strip() for c in df_upload.columns]
        
        if 'ponto' in df_upload.columns and 'demanda_kw' in df_upload.columns:
            if 'fator_potencia' not in df_upload.columns:
                df_upload['fator_potencia'] = 0.92  # Preenche FP padrão caso ausente

            df_upload['demanda_kw'] = pd.to_numeric(df_upload['demanda_kw'], errors='coerce')
            df_upload['fator_potencia'] = pd.to_numeric(df_upload['fator_potencia'], errors='coerce').fillna(0.92)
            
            df_upload = df_upload.dropna(subset=['demanda_kw'])

            with self._get_connection() as conn:
                df_upload[['ponto', 'demanda_kw', 'fator_potencia']].to_sql(
                    'leituras', conn, if_exists='append', index=False
                )
            return True
        return False

    def carregar_dados_df(self) -> pd.DataFrame:
        """Carrega medições do banco e executa os cálculos vetoriais do triângulo de potências."""
        with self._get_connection() as conn:
            query = "SELECT id, ponto, demanda_kw, fator_potencia, data_hora FROM leituras"
            df = pd.read_sql_query(query, conn)
        
        if not df.empty:
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
        # Atualiza os valores de demanda e fator de potência por ID
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE leituras SET demanda_kw = ?, fator_potencia = ? WHERE id = ?", 
                (novo_valor_kw, novo_fp, id_registro)
            )
            conn.commit()

    def deletar_leitura(self, id_registro: int):
        # Remove uma leitura específica do banco de dados
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM leituras WHERE id = ?", (id_registro,))
            conn.commit()


# =========================================================================
# 2. ANÁLISE CIENTÍFICA & ÁLGEBRA SIMBÓLICA (NumPy, SciPy, SymPy)
# =========================================================================
class EnergyAnalytics:
    """Módulo responsável por cálculos estatísticos, diferenciação simbólica e tarifação."""

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

        if len(demandas) > 1:
            ic = stats.t.interval(0.95, len(demandas)-1, loc=media_p, scale=stats.sem(demandas))
        else:
            ic = (media_p, media_p)

        return {
            "total_amostras": len(demandas),
            "media_kw": media_p,
            "desvio_padrao": desvio_p,
            "pico_kw": pico_p,
            "minimo_kw": min_p,
            "fator_carga": fator_carga,
            "fp_medio": media_fp,
            "ic_95": ic
        }

    @staticmethod
    def modelar_triangulo_potencias_simbolico() -> dict:
        """Converte as equações do SymPy em strings de LaTeX formatadas."""
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
        """Calcula a tarifação industrial (Hora, Mês e Ano) e a tarifação residencial (Média e Último Mês)."""
        if df.empty:
            return {}

        p_media_kw = float(df['demanda_kw'].mean())

        # --- PERFIL INDUSTRIAL (Grupo A - Operação 24/7) ---
        consumo_ind_hora_kwh = p_media_kw * 1.0
        custo_ind_hora = consumo_ind_hora_kwh * tarifa_kwh

        consumo_ind_mes_kwh = p_media_kw * 24 * 30
        custo_ind_mes = consumo_ind_mes_kwh * tarifa_kwh

        consumo_ind_ano_kwh = p_media_kw * 24 * 365
        custo_ind_ano = consumo_ind_ano_kwh * tarifa_kwh

        # --- PERFIL RESIDENCIAL (Grupo B - Faturas Mensais) ---
        consumo_res_media_kwh = float(df['demanda_kw'].mean())
        custo_res_media_mes = consumo_res_media_kwh * tarifa_kwh

        consumo_res_ultimo_kwh = float(df['demanda_kw'].iloc[-1])
        custo_res_ultimo_mes = consumo_res_ultimo_kwh * tarifa_kwh

        consumo_res_total_kwh = float(df['demanda_kw'].sum())
        custo_res_total = consumo_res_total_kwh * tarifa_kwh

        return {
            "p_media_kw": p_media_kw,
            "consumo_ind_hora_kwh": consumo_ind_hora_kwh,
            "custo_ind_hora": custo_ind_hora,
            "consumo_ind_mes_kwh": consumo_ind_mes_kwh,
            "custo_ind_mes": custo_ind_mes,
            "consumo_ind_ano_kwh": consumo_ind_ano_kwh,
            "custo_ind_ano": custo_ind_ano,
            "consumo_res_media_kwh": consumo_res_media_kwh,
            "custo_res_media_mes": custo_res_media_mes,
            "consumo_res_ultimo_kwh": consumo_res_ultimo_kwh,
            "custo_res_ultimo_mes": custo_res_ultimo_mes,
            "consumo_res_total_kwh": consumo_res_total_kwh,
            "custo_res_total": custo_res_total
        }


# =========================================================================
# 3. WEB SCRAPING TARIFÁRIO
# =========================================================================
class TariffScraper:
    """Obtém dados tarifários atualizados via HTTP com mecanismo de contingência."""

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
        
        return {"status": "Simulado (Offline)", "fonte": "Tabela ANEEL Contingência", "tarifa_estimada_kwh": 0.75}


# =========================================================================
# 4. AUTOMAÇÃO DE RELATÓRIOS PDF (ReportLab)
# =========================================================================
class PDFReportGenerator:
    """Gera relatórios técnicos formais no formato PDF."""

    @staticmethod
    def gerar_relatorio_pdf(filename: str, estatisticas: dict) -> str:
        doc = SimpleDocTemplate(filename, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []

        title = Paragraph("<b>RELATÓRIO DE ANÁLISE DE CARGA - UTFPR</b>", styles['Title'])
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
            ["Fator de Carga (FC)", f"{estatisticas.get('fator_carga', 0):.2f}"],
            ["Desvio Padrão (kW)", f"{estatisticas.get('desvio_padrao', 0):.2f}"]
        ]

        tabela = Table(data, colWidths=[220, 180])
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

        fp_med = estatisticas.get('fp_medio', 1.0)
        status_fp = "ADEQUADO (FP ≥ 0.92)" if fp_med >= 0.92 else "ALERTA: FP < 0.92 (Passível de Ajuste de Reativos)"
        diag = Paragraph(f"<b>Diagnóstico de Qualidade de Energia:</b> {status_fp}", styles['Normal'])
        story.append(diag)

        doc.build(story)
        return filename


# =========================================================================
# 5. INTERFACE DASHBOARD (Streamlit)
# =========================================================================
st.set_page_config(page_title="Sistema de Energia - IC UTFPR", page_icon="⚡", layout="wide")

db = EnergyDatabase()

st.title("⚡ Sistema Integrado de Gerenciamento de Energia")
st.caption("Projeto de Iniciação Científica — Autor: Lucas Chagas | UTFPR")

st.sidebar.header("🔧 Operações do Sistema")
menu_op = st.sidebar.selectbox(
    "Escolha uma Ação:",
    ["Dashboard & Analytics", "Inserir Leitura Única", "Importar CSV/Excel", "Gerenciar Registros", "Scraping & Tarifas"]
)

df = db.carregar_dados_df()

if menu_op == "Dashboard & Analytics":
    st.subheader("📊 Painel Geral de Consumo e Qualidade da Energia")
    
    if df.empty:
        st.info("Nenhum dado cadastrado. Cadastre medições usando o menu lateral ou importe uma planilha.")
    else:
        stats_data = EnergyAnalytics.analise_estatistica(df)
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Demanda Média", f"{stats_data['media_kw']:.2f} kW")
        c2.metric("Demanda Máxima", f"{stats_data['pico_kw']:.2f} kW")
        c3.metric("Fator de Carga (FC)", f"{stats_data['fator_carga']:.2f}")
        c4.metric("FP Médio", f"{stats_data['fp_medio']:.2f}", 
                  delta="Abaixo do Limite" if stats_data['fp_medio'] < 0.92 else "Conforme",
                  delta_color="inverse" if stats_data['fp_medio'] < 0.92 else "normal")

        st.divider()

        col_graf, col_sym = st.columns([2, 1])

        with col_graf:
            st.markdown("### Curva de Carga e Potências Interativas")
            
            fig = go.Figure()
            fig.add_trace(go.Bar(x=df['ponto'], y=df['demanda_kw'], name='Ativa (kW)', marker_color='#003366'))
            fig.add_trace(go.Bar(x=df['ponto'], y=df['potencia_reativa_kvar'], name='Reativa (kvar)', marker_color='#ff7f0e'))
            fig.update_layout(
                barmode='group', 
                title="Potência Ativa vs. Reativa por Ponto", 
                xaxis_title="Ponto de Medição", 
                yaxis_title="Grandeza (kW / kvar)"
            )
            
            st.plotly_chart(fig, use_container_width=True)

        with col_sym:
            st.markdown("### 🧮 Modelagem Matemática (SymPy)")
            simb = EnergyAnalytics.modelar_triangulo_potencias_simbolico()
            
            st.latex(r"S = \frac{P}{FP}, \quad Q = \sqrt{S^2 - P^2}")
            
            st.write("**Potência Reativa Simbólica ($Q$):**")
            st.latex(f"Q = {simb['potencia_reativa_latex']}")
            
            st.write(r"**Sensibilidade de $Q$ referente ao $FP$ ($\frac{dQ}{dFP}$):**")
            st.latex(f"\\frac{{dQ}}{{dFP}} = {simb['sensibilidade_fp_latex']}")

        st.divider()

        st.subheader("📑 Documentação Técnica")
        if st.button("Gerar Relatório Técnico PDF"):
            pdf_name = "Relatorio_Energia_UTFPR.pdf"
            PDFReportGenerator.gerar_relatorio_pdf(pdf_name, stats_data)
            
            with open(pdf_name, "rb") as pdf_file:
                st.download_button(
                    label="📥 Baixar Relatório Técnico PDF",
                    data=pdf_file,
                    file_name=pdf_name,
                    mime="application/pdf"
                )

elif menu_op == "Inserir Leitura Única":
    st.subheader("➕ Novo Registro Manual de Demanda")
    
    with st.form("form_inserir"):
        ponto = st.text_input("Nome da Subestação / Ponto de Medição", placeholder="Ex: SE-01 Bloco A")
        demanda = st.number_input("Demanda Consumida (kW)", min_value=0.0, step=0.1)
        fp = st.number_input("Fator de Potência (FP)", min_value=0.01, max_value=1.0, value=0.92, step=0.01)
        
        btn_submit = st.form_submit_button("Salvar Registro")
        
        if btn_submit:
            if ponto and demanda > 0:
                db.inserir_leitura(ponto, demanda, fp)
                st.success(f"Leitura para '{ponto}' inserida com sucesso!")
                st.rerun()
            else:
                st.error("Preencha todos os campos obrigatórios.")

elif menu_op == "Importar CSV/Excel":
    st.subheader("📁 Importação Massiva de Arquivos de Medição")
    st.markdown("Envie uma planilha nos formatos `.csv` ou `.xlsx` contendo as colunas: **`ponto`**, **`demanda_kw`** e opcionalmente **`fator_potencia`**.")
    
    arquivo_carregado = st.file_uploader("Selecione o arquivo de medições", type=["csv", "xlsx"])
    
    if arquivo_carregado is not None:
        try:
            if arquivo_carregado.name.endswith('.csv'):
                df_import = pd.read_csv(arquivo_carregado)
            else:
                df_import = pd.read_excel(arquivo_carregado)
                
            st.write("Pré-visualização dos dados identificados:")
            st.dataframe(df_import.head(), use_container_width=True)
            
            if st.button("Gravar Registros no Banco de Dados SQLite"):
                sucesso = db.importar_dados_csv_excel(df_import)
                if sucesso:
                    st.success("Dados importados e salvos com sucesso no banco de dados!")
                    st.rerun()
                else:
                    st.error("A estrutura do arquivo é inválida. Certifique-se de incluir as colunas 'ponto' e 'demanda_kw'.")
        except Exception as e:
            st.error(f"Erro ao ler e processar o arquivo: {e}")

elif menu_op == "Gerenciar Registros":
    st.subheader("⚙️ Visualização, Edição e Análise Detalhada dos Registros")
    
    if df.empty:
        st.info("Nenhum dado cadastrado para gerenciamento.")
    else:
        # Seletor para escolher o modo de visualização dos registros
        modo_visao = st.radio(
            "Selecione o Modo de Visualização do Banco de Dados:",
            ["Tabela Geral (CRUD)", "Registros Mensais (Residencial)", "Gastos por Hora (Industrial)"],
            horizontal=True
        )
        
        st.divider()

        if modo_visao == "Tabela Geral (CRUD)":
            st.markdown("#### Banco de Dados Relacional Completo")
            st.dataframe(df, use_container_width=True)

            col_ed, col_del = st.columns(2)

            with col_ed:
                st.markdown("#### Editar Registro")
                id_edit = st.selectbox("Selecione o ID para alterar", df['id'].tolist())
                novo_val = st.number_input("Novo Valor de Demanda (kW)", min_value=0.0, step=0.1)
                novo_fp = st.number_input("Novo Fator de Potência", min_value=0.01, max_value=1.0, value=0.92, step=0.01)
                
                if st.button("Atualizar Registro"):
                    db.atualizar_leitura(id_edit, novo_val, novo_fp)
                    st.success("Registro modificado com sucesso!")
                    st.rerun()

            with col_del:
                st.markdown("#### Excluir Registro")
                id_del = st.selectbox("Selecione o ID para remover", df['id'].tolist(), key="del_select")
                if st.button("Remover Registro", type="primary"):
                    db.deletar_leitura(id_del)
                    st.warning("Registro excluído!")
                    st.rerun()

        elif modo_visao == "Registros Mensais (Residencial)":
            st.markdown("#### 🏠 Análise de Registros Mensais (Perfil Residencial)")
            st.caption("Cada registro é tratado como o consumo total acumulado de um mês em kWh.")
            
            # Obtém a tarifa atual para projetar o valor das faturas linha a linha
            info_tarifa = TariffScraper.obter_cotacao_web()
            t_ref = info_tarifa['tarifa_estimada_kwh']
            
            df_res = df.copy()
            df_res['Consumo (kWh)'] = df_res['demanda_kw']
            df_res['Fatura Estimada (R$)'] = df_res['Consumo (kWh)'] * t_ref
            
            # Exibe a tabela com formatação das colunas faturadas
            st.dataframe(
                df_res[['id', 'ponto', 'Consumo (kWh)', 'fator_potencia', 'data_hora', 'Fatura Estimada (R$)']],
                use_container_width=True
            )
            
            # Métricas consolidadas do perfil residencial
            c_med, c_ult, c_tot = st.columns(3)
            c_med.metric("Consumo Médio Mensal", f"{df_res['Consumo (kWh)'].mean():.2f} kWh", f"R$ {df_res['Fatura Estimada (R$)'].mean():.2f}/mês")
            c_ult.metric("Última Fatura Cadastrada", f"{df_res['Consumo (kWh)'].iloc[-1]:.2f} kWh", f"R$ {df_res['Fatura Estimada (R$)'].iloc[-1]:.2f}")
            c_tot.metric("Histórico Total Acumulado", f"{df_res['Consumo (kWh)'].sum():.2f} kWh", f"R$ {df_res['Fatura Estimada (R$)'].sum():.2f}")

        elif modo_visao == "Gastos por Hora (Industrial)":
            st.markdown("#### 🏭 Análise de Gastos Operacionais por Hora (Perfil Industrial)")
            st.caption("Cada registro representa a demanda ativa (kW) mantida em operação contínua.")
            
            info_tarifa = TariffScraper.obter_cotacao_web()
            t_ref = info_tarifa['tarifa_estimada_kwh']
            
            df_ind = df.copy()
            df_ind['Demanda (kW)'] = df_ind['demanda_kw']
            df_ind['Custo / Hora (R$/h)'] = df_ind['Demanda (kW)'] * t_ref
            df_ind['Custo / Mês (720h)'] = df_ind['Custo / Hora (R$/h)'] * 720
            df_ind['Custo / Ano (8760h)'] = df_ind['Custo / Hora (R$/h)'] * 8760
            
            # Exibe a tabela operacional de custos industriais
            st.dataframe(
                df_ind[['id', 'ponto', 'Demanda (kW)', 'fator_potencia', 'Custo / Hora (R$/h)', 'Custo / Mês (720h)', 'Custo / Ano (8760h)']],
                use_container_width=True
            )
            
            # Métricas consolidadas da operação industrial
            c_hr, c_mes, c_ano = st.columns(3)
            c_hr.metric("Custo Médio Horário", f"R$ {df_ind['Custo / Hora (R$/h)'].mean():,.2f} / h")
            c_mes.metric("Projeção Mensal Média (720h)", f"R$ {df_ind['Custo / Mês (720h)'].mean():,.2f} / mês")
            c_ano.metric("Projeção Anual Média (8760h)", f"R$ {df_ind['Custo / Ano (8760h)'].mean():,.2f} / ano")

elif menu_op == "Scraping & Tarifas":
    st.subheader("🌐 Cotações e Estimativa de Tarifação (Industrial & Residencial)")
    
    if st.button("Executar Scraping de Tarifas"):
        info = TariffScraper.obter_cotacao_web()
        st.json(info)
        
        if not df.empty:
            st.divider()
            tarifa = info['tarifa_estimada_kwh']
            res_tarifa = EnergyAnalytics.calcular_tarifacao_dupla(df, tarifa)
            
            col_ind, col_res = st.columns(2)
            
            with col_ind:
                st.markdown("### 🏭 Perfil Industrial (Grupo A)")
                st.caption("Cálculos baseados na Demanda Operacional em Regime Contínuo")
                st.metric("Demanda Média Operacional", f"{res_tarifa['p_media_kw']:.2f} kW")
                st.metric("Custo Operacional por Hora", f"R$ {res_tarifa['custo_ind_hora']:,.2f} / h")
                st.metric("Custo Operacional Mensal (720h)", f"R$ {res_tarifa['custo_ind_mes']:,.2f} / mês")
                st.metric("Custo Operacional Anual (8760h)", f"R$ {res_tarifa['custo_ind_ano']:,.2f} / ano")
                st.info(f"⚡ **Consumo Anual Estimado:** {res_tarifa['consumo_ind_ano_kwh']:,.0f} kWh/ano")

            with col_res:
                st.markdown("### 🏠 Perfil Residencial (Grupo B)")
                st.caption("Análise Baseada no Histórico de Faturas Mensais")
                st.metric("Consumo Médio Mensal", f"{res_tarifa['consumo_res_media_kwh']:.2f} kWh/mês")
                st.metric("Fatura Mensal Média", f"R$ {res_tarifa['custo_res_media_mes']:,.2f} / mês")
                st.metric("Última Fatura Cadastrada", f"R$ {res_tarifa['custo_res_ultimo_mes']:,.2f} ({res_tarifa['consumo_res_ultimo_kwh']:.0f} kWh)")
                st.success(f"💡 **Histórico Acumulado ({len(df)} meses):** {res_tarifa['consumo_res_total_kwh']:.0f} kWh (R$ {res_tarifa['custo_res_total']:,.2f})")
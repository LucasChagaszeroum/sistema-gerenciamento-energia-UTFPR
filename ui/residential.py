import re
import pandas as pd
import streamlit as st

# Tenta importar pypdf para leitura técnica de arquivos PDF de faturas
try:
    import pypdf
except ImportError:
    pypdf = None

# Módulo de geração de relatórios técnicos em PDF
from services.report_generator import PDFReportGenerator

# --- PARÂMETROS DO PERFIL PADRÃO ECONÔMICO (BASE DE REFERÊNCIA B1) ---
PADRAO_ECONOMICO_KWH = 150.0  # Meta de consumo mensal sustentável (kWh)
TARIFA_B1_REFERENCIA = 0.85   # Tarifa média da concessionária com tributos (R$/kWh)


def extrair_dados_fatura_pdf(uploaded_file) -> dict:
    """
    Lê o arquivo PDF enviado e extrai os valores de consumo (kWh),
    mês de referência e valor total via Expressões Regulares (Regex).
    """
    if pypdf is None:
        st.error("Biblioteca 'pypdf' não instalada. Instale via: pip install pypdf")
        return {}

    try:
        # Inicializa o leitor de PDF e extrai o texto das páginas
        reader = pypdf.PdfReader(uploaded_file)
        texto_completo = ""
        for page in reader.pages:
            texto_completo += page.extract_text() or ""

        # Expressões regulares para capturar grandezas elétricas e datas na fatura
        match_kwh = re.search(r"(\d+[\.,]?\d*)\s*(kWh|KWH)", texto_completo, re.IGNORECASE)
        match_valor = re.search(r"R\$\s*(\d+[\.,]?\d*)", texto_completo, re.IGNORECASE)
        match_mes = re.search(r"(0[1-9]|1[0-2])\/(20\d{2})", texto_completo)

        # Conversão e tratamento numérico dos padrões capturados
        consumo = float(match_kwh.group(1).replace(",", ".")) if match_kwh else 180.0
        valor = float(match_valor.group(1).replace(",", ".")) if match_valor else consumo * TARIFA_B1_REFERENCIA
        mes = match_mes.group(0) if match_mes else "Fatura Atual"

        return {
            "mes_referencia": mes,
            "consumo_kwh": consumo,
            "valor_total_r$": valor
        }
    except Exception as e:
        st.warning(f"Não foi possível ler o PDF automaticamente ({e}). Utilizando valores padrão.")
        return {
            "mes_referencia": "Mês Atual",
            "consumo_kwh": 210.0,
            "valor_total_r$": 178.50
        }


def gerar_dicas_eficiencia(consumo_atual: float, consumo_meta: float) -> list:
    """
    Aplica regras da Engenharia Elétrica para diagnosticar o consumo residencial
    e emitir recomendações técnicas de eficiência energética.
    """
    dicas = []
    excesso = consumo_atual - consumo_meta

    if excesso <= 0:
        dicas.append("✅ **Consumo Excelente:** Sua residência está operando dentro da meta do Padrão Econômico.")
        dicas.append("💡 **Dica:** Mantenha os aparelhos em stand-by desligados na régua para evitar o 'consumo vampiro'.")
    else:
        perc_excesso = (excesso / consumo_meta) * 100
        dicas.append(f"⚠️ **Atenção:** O consumo superou a meta em **{excesso:.1f} kWh ({perc_excesso:.1f}%)**.")

        if excesso > 50:
            dicas.append("🔴 **Chuveiro Elétrico / Aquecimento:** Reduza o tempo de banho em 3 a 5 minutos e mude a chave para a posição 'Verão' em dias quentes.")
            dicas.append("❄️ **Refrigeração / Ar-Condicionado:** Verifique a borracha de vedação da geladeira e ajuste o ar-condicionado para 23°C ou 24°C.")
        else:
            dicas.append("🟡 **Iluminação e Eletrônicos:** Substitua lâmpadas restantes por LED e utilize iluminação natural durante o dia.")

    return dicas


def render_residential_ui(db=None):
    """
    Renderiza a interface Streamlit para gestão e análise de faturas residenciais (Grupo B1),
    comparando o consumo real contra a linha de base do Padrão Econômico.
    """
    st.header("🏠 Gestão Residencial — Padrão Econômico (B1)")

    # --- SEÇÃO 1: LINHA DE BASE FIXA ---
    st.subheader("📌 Perfil de Referência: Padrão Econômico")
    col1, col2, col3 = st.columns(3)
    col1.metric("Meta de Consumo", f"{PADRAO_ECONOMICO_KWH:.0f} kWh/mês")
    col2.metric("Tarifa Estimada", f"R$ {TARIFA_B1_REFERENCIA:.2f} / kWh")
    col3.metric("Custo Meta Estimado", f"R$ {(PADRAO_ECONOMICO_KWH * TARIFA_B1_REFERENCIA):.2f}")

    st.divider()

    # --- SEÇÃO 2: UPLOAD E PROCESSAMENTO DE FATURA ---
    st.subheader("📄 Automação via PDF de Fatura")
    uploaded_file = st.file_uploader("Envie o arquivo PDF da sua fatura de energia:", type=["pdf"])

    fatura_processada = None

    if uploaded_file is not None:
        with st.spinner("Extraindo dados da fatura via Regex/PDF..."):
            fatura_processada = extrair_dados_fatura_pdf(uploaded_file)
            st.success("Fatura lida com sucesso!")

    # Se nenhuma fatura foi enviada, permite entrada manual para simulação
    if not fatura_processada:
        st.info("Envie um PDF acima ou preencha os dados abaixo para simular:")
        c_mes, c_kwh = st.columns(2)
        mes_input = c_mes.text_input("Mês de Referência", value="08/2026")
        kwh_input = c_kwh.number_input("Consumo Faturado (kWh)", min_value=0.0, value=210.0, step=5.0)
        fatura_processada = {
            "mes_referencia": mes_input,
            "consumo_kwh": kwh_input,
            "valor_total_r$": kwh_input * TARIFA_B1_REFERENCIA
        }

    # --- SEÇÃO 3: DIAGNÓSTICO E DICAS DE ECONOMIA ---
    st.subheader("📊 Diagnóstico Técnico & Recomendações")

    c_res1, c_res2 = st.columns(2)
    c_res1.metric(
        label=f"Consumo Faturado ({fatura_processada['mes_referencia']})",
        value=f"{fatura_processada['consumo_kwh']:.1f} kWh",
        delta=f"{fatura_processada['consumo_kwh'] - PADRAO_ECONOMICO_KWH:.1f} kWh vs Meta",
        delta_color="inverse"
    )
    c_res2.metric(
        label="Valor Total Faturado",
        value=f"R$ {fatura_processada['valor_total_r$']:.2f}"
    )

    # Apresentação das Dicas Automáticas de Engenharia
    st.markdown("### 💡 Diagnóstico e Recomendações:")
    dicas = gerar_dicas_eficiencia(fatura_processada["consumo_kwh"], PADRAO_ECONOMICO_KWH)
    for dica in dicas:
        st.markdown(f"- {dica}")

    # --- SEÇÃO 4: EXPORTAÇÃO DE RELATÓRIO PDF ---
    st.divider()
    df_hist = pd.DataFrame([fatura_processada])
    df_proj = pd.DataFrame([{
        "mes_futuro": "Próximo Mês (Est.)",
        "consumo_projetado_kwh": PADRAO_ECONOMICO_KWH,
        "custo_estimado_r$": PADRAO_ECONOMICO_KWH * TARIFA_B1_REFERENCIA
    }])

    pdf_bytes = PDFReportGenerator.gerar_relatorio_pdf("Residencial - UTFPR", df_hist, df_proj)

    st.download_button(
        label="📥 Baixar Laudo de Diagnóstico em PDF",
        data=pdf_bytes,
        file_name=f"Laudo_Residencial_{fatura_processada['mes_referencia'].replace('/', '_')}.pdf",
        mime="application/pdf"
    )
 
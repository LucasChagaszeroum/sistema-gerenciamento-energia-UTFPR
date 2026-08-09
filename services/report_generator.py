from fpdf import FPDF
import pandas as pd
import io

class PDFReportGenerator:
    """Módulo gerador de relatórios técnicos em PDF."""

    @staticmethod
    def gerar_relatorio_pdf(nome_unidade: str, df_faturas: pd.DataFrame, df_projeçao: pd.DataFrame) -> bytes:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)

        # Cabeçalho Institucional
        pdf.cell(0, 10, f"Relatório de Diagnóstico Energético - UTFPR", ln=True, align='C')
        pdf.set_font("Arial", '', 11)
        pdf.cell(0, 8, f"Unidade Consumidora: {nome_unidade}", ln=True, align='C')
        pdf.ln(10)

        # Seção 1: Histórico
        pdf.set_font("Arial", 'B', 13)
        pdf.cell(0, 8, "1. Historico de Consumo e Custos Reais", ln=True)
        pdf.set_font("Arial", '', 10)

        pdf.cell(40, 7, "Mes", 1)
        pdf.cell(50, 7, "Consumo (kWh)", 1)
        pdf.cell(50, 7, "Valor Total (R$)", 1)
        pdf.ln()

        for _, row in df_faturas.iterrows():
            pdf.cell(40, 6, str(row['mes_referencia']), 1)
            pdf.cell(50, 6, f"{row['consumo_kwh']:.1f}", 1)
            pdf.cell(50, 6, f"R$ {row['valor_total']:.2f}", 1)
            pdf.ln()

        pdf.ln(8)

        # Seção 2: Projeção Preditiva
        if not df_projeçao.empty:
            pdf.set_font("Arial", 'B', 13)
            pdf.cell(0, 8, "2. Simulacao e Projecao de Gastos Futuros (IA)", ln=True)
            pdf.set_font("Arial", '', 10)

            pdf.cell(40, 7, "Mes Previsto", 1)
            pdf.cell(45, 7, "Consumo (kWh)", 1)
            pdf.cell(45, 7, "Custo Estimado", 1)
            pdf.cell(40, 7, "Bandeira", 1)
            pdf.ln()

            for _, row in df_projeçao.iterrows():
                pdf.cell(40, 6, str(row['mes_referencia']), 1)
                pdf.cell(45, 6, f"{row['consumo_projetado_kwh']:.1f}", 1)
                pdf.cell(45, 6, f"R$ {row['custo_estimado_r$']:.2f}", 1)
                pdf.cell(40, 6, str(row['bandeira_simulada']), 1)
                pdf.ln()

        # Retorna o arquivo gerado em bytes para download via Streamlit
        return pdf.output(dest='S').encode('latin-1')
    
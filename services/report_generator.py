from fpdf import FPDF
import pandas as pd

class PDFReportGenerator:
    """Módulo gerador de relatórios técnicos em PDF utilizando a biblioteca fpdf2."""

    @staticmethod
    def gerar_relatorio_pdf(nome_unidade: str, df_faturas: pd.DataFrame, df_projecao: pd.DataFrame) -> bytes:
        # Inicializa o documento PDF em formato A4
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Helvetica", 'B', 16)

        # Cabeçalho Institucional
        pdf.cell(0, 10, "Relatorio de Diagnostico Energetico - UTFPR", new_x="LMARGIN", new_y="NEXT", align='C')
        pdf.set_font("Helvetica", '', 11)
        pdf.cell(0, 8, f"Unidade Consumidora: {nome_unidade}", new_x="LMARGIN", new_y="NEXT", align='C')
        pdf.ln(5)

        # Seção 1: Histórico de Consumo
        pdf.set_font("Helvetica", 'B', 12)
        pdf.cell(0, 8, "1. Historico de Consumo e Custos Reais", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", '', 10)

        # Cabeçalho da Tabela de Histórico
        pdf.cell(40, 7, "Mes", border=1)
        pdf.cell(50, 7, "Consumo (kWh)", border=1)
        pdf.cell(50, 7, "Valor Total (R$)", border=1, new_x="LMARGIN", new_y="NEXT")

        # Iteração sobre o DataFrame de faturas cadastradas
        for _, row in df_faturas.iterrows():
            pdf.cell(40, 6, str(row['mes_referencia']), border=1)
            pdf.cell(50, 6, f"{row['consumo_kwh']:.1f}", border=1)
            pdf.cell(50, 6, f"R$ {row['valor_total']:.2f}", border=1, new_x="LMARGIN", new_y="NEXT")

        pdf.ln(5)

        # Seção 2: Projeção Preditiva via Inteligência Artificial
        if not df_projecao.empty:
            pdf.set_font("Helvetica", 'B', 12)
            pdf.cell(0, 8, "2. Simulacao e Projecao de Gastos Futuros (IA)", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", '', 10)

            # Cabeçalho da Tabela de Projeções
            pdf.cell(40, 7, "Mes Previsto", border=1)
            pdf.cell(45, 7, "Consumo (kWh)", border=1)
            pdf.cell(45, 7, "Custo Estimado", border=1)
            pdf.cell(40, 7, "Bandeira", border=1, new_x="LMARGIN", new_y="NEXT")

            # Iteração sobre o DataFrame de estimativas da IA
            for _, row in df_projecao.iterrows():
                pdf.cell(40, 6, str(row['mes_referencia']), border=1)
                pdf.cell(45, 6, f"{row['consumo_projetado_kwh']:.1f}", border=1)
                pdf.cell(45, 6, f"R$ {row['custo_estimado_r$']:.2f}", border=1)
                pdf.cell(40, 6, str(row['bandeira_simulada']), border=1, new_x="LMARGIN", new_y="NEXT")

        # Converte o bytearray gerado pelo fpdf2 em um objeto bytes compativel com st.download_button
        return bytes(pdf.output())
    
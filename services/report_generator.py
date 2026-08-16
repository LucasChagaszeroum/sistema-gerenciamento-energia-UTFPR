import unicodedata
from fpdf import FPDF
import pandas as pd

class PDFReportGenerator:
    """
    Classe utilitária para formatação e exportação de laudos técnicos em PDF.
    Aplica tratamento de codificação Latin-1 e busca defensiva de chaves do Pandas.
    """

    @staticmethod
    def sanitizar_texto(texto: str) -> str:
        """Converte caracteres Unicode incompatíveis para o padrão aceito pelo FPDF."""
        if not isinstance(texto, str):
            texto = str(texto)
            
        substituicoes = {
            "—": "-", "–": "-", "“": '"', "”": '"', "’": "'", "…": "...", "ª": "a.", "º": "o."
        }
        for original, substituto in substituicoes.items():
            texto = texto.replace(original, substituto)
            
        return texto.encode('latin-1', 'replace').decode('latin-1')

    @staticmethod
    def gerar_relatorio_pdf(nome_unidade: str, df_historico: pd.DataFrame, df_projecao: pd.DataFrame) -> bytes:
        """Gera o laudo de diagnóstico de energia em PDF para download no Streamlit."""
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Helvetica", size=12)

        # Cabeçalho do Laudo Técnico
        unidade_limpa = PDFReportGenerator.sanitizar_texto(nome_unidade)
        pdf.set_font("Helvetica", 'B', 16)
        pdf.cell(0, 10, PDFReportGenerator.sanitizar_texto("SISTEMA DE GESTÃO DE ENERGIA - UTFPR"), new_x="LMARGIN", new_y="NEXT", align='C')
        
        pdf.set_font("Helvetica", size=12)
        pdf.cell(0, 8, f"Unidade Consumidora: {unidade_limpa}", new_x="LMARGIN", new_y="NEXT", align='C')
        pdf.ln(5)

        # 1. Histórico de Consumo Faturado
        pdf.set_font("Helvetica", 'B', 12)
        pdf.cell(0, 8, PDFReportGenerator.sanitizar_texto("1. Histórico de Consumo Faturado"), new_x="LMARGIN", new_y="NEXT", align='L')
        pdf.set_font("Helvetica", size=10)

        if not df_historico.empty:
            for _, row in df_historico.iterrows():
                # Busca flexível usando .get() para prevenir KeyError em diferentes padrões de nome
                mes = row.get('mes_referencia', row.get('mes_ano', 'Mês Atual'))
                consumo = row.get('consumo_kwh', 0.0)
                valor = row.get('valor_total_r$', row.get('valor_total', 0.0))
                
                linha_txt = f"Mês: {mes} | Consumo: {consumo:.1f} kWh | Valor: R$ {valor:.2f}"
                pdf.cell(0, 6, PDFReportGenerator.sanitizar_texto(linha_txt), new_x="LMARGIN", new_y="NEXT", align='L')

        pdf.ln(5)

        # 2. Projeções Preditivas
        pdf.set_font("Helvetica", 'B', 12)
        pdf.cell(0, 8, PDFReportGenerator.sanitizar_texto("2. Projeção de Gastos (Próximos Meses)"), new_x="LMARGIN", new_y="NEXT", align='L')
        pdf.set_font("Helvetica", size=10)

        if not df_projecao.empty:
            for _, row in df_projecao.iterrows():
                mes_futuro = row.get('mes_futuro', 'Próximo Mês')
                consumo_proj = row.get('consumo_projetado_kwh', 0.0)
                custo_est = row.get('custo_estimado_r$', row.get('valor_total', 0.0))
                
                proj_txt = f"Mês Futuro: {mes_futuro} | Consumo Estimado: {consumo_proj:.1f} kWh | Custo Estimado: R$ {custo_est:.2f}"
                pdf.cell(0, 6, PDFReportGenerator.sanitizar_texto(proj_txt), new_x="LMARGIN", new_y="NEXT", align='L')

        # Retorna o relatório formatado em array de bytes
        return bytes(pdf.output())
    
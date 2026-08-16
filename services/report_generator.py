from fpdf import FPDF
from datetime import datetime

class PDFReportGenerator:
    """
    Classe responsável pela geração automatizada de relatórios e laudos técnicos
    de eficiência energética em formato PDF.
    """
    def __init__(self):
        # Inicializa a estrutura base do documento FPDF
        self.pdf = FPDF(orientation='P', unit='mm', format='A4')
        self.pdf.set_auto_page_break(auto=True, margin=15)

    def gerar_laudo_residencial(self, dados: dict) -> bytes:
        """
        Gera o laudo técnico do Módulo Residencial (Grupo B) e retorna os bytes do PDF.
        """
        self.pdf.add_page()
        
        # 1. CABEÇALHO DO LAUDO TÉCNICO
        self.pdf.set_font("Helvetica", style="B", size=16)
        self.pdf.cell(0, 10, "LAUDO TÉCNICO DE EFICIÊNCIA ENERGÉTICA", ln=True, align="C")
        self.pdf.set_font("Helvetica", style="I", size=10)
        self.pdf.cell(0, 6, f"Módulo: {dados.get('modulo', 'Residencial B1')} | Emissão: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True, align="C")
        self.pdf.ln(8)

        # 2. RESUMO EXECUTIVO E MÉTRICAS
        self.pdf.set_font("Helvetica", style="B", size=12)
        self.pdf.cell(0, 8, "1. Resumo do Consumo Acumulado", ln=True)
        self.pdf.set_font("Helvetica", size=10)
        
        media_kwh = dados.get("media_kwh", 0.0)
        total_gasto = dados.get("total_gasto", 0.0)
        
        self.pdf.cell(0, 6, f"- Consumo Médio Mensal: {media_kwh:.1f} kWh", ln=True)
        self.pdf.cell(0, 6, f"- Custo Total Acumulado: R$ {total_gasto:.2f}", ln=True)
        self.pdf.cell(0, 6, f"- Meta de Referência (Padrão Econômico): 150.0 kWh/mês", ln=True)
        self.pdf.ln(6)

        # 3. RECOMENDAÇÕES DE EFICIÊNCIA ENERGÉTICA (IA)
        self.pdf.set_font("Helvetica", style="B", size=12)
        self.pdf.cell(0, 8, "2. Diagnósticos e Recomendações Técnicas", ln=True)
        self.pdf.set_font("Helvetica", size=10)
        
        recomendacoes = dados.get("recomendacoes", [])
        if recomendacoes:
            for rec in recomendacoes:
                # Sanitização de marcações markdown/emojis para evitar erros de encoding no FPDF
                texto_limpo = rec.replace("**", "").replace("⚠️", "[ALERTA]").replace("✅", "[OK]").replace("💡", "[DICA]").replace("📈", "[VARIAÇÃO]")
                self.pdf.multi_cell(0, 6, f"• {texto_limpo}")
                self.pdf.ln(2)
        else:
            self.pdf.cell(0, 6, "Nenhum diagnóstico registrado até o momento.", ln=True)
            
        self.pdf.ln(6)

        # 4. TABELA DE FATURAS PROCESSADAS
        self.pdf.set_font("Helvetica", style="B", size=12)
        self.pdf.cell(0, 8, "3. Histórico de Faturas Registradas", ln=True)
        
        # Cabeçalho da Tabela
        self.pdf.set_font("Helvetica", style="B", size=9)
        self.pdf.cell(35, 7, "Mês/Ano", border=1, align="C")
        self.pdf.cell(45, 7, "Consumo (kWh)", border=1, align="C")
        self.pdf.cell(45, 7, "Valor Total (R$)", border=1, align="C")
        self.pdf.cell(55, 7, "Bandeira Tarifária", border=1, align="C", ln=True)

        # Linhas da Tabela
        self.pdf.set_font("Helvetica", size=9)
        faturas = dados.get("faturas", [])
        for fatura in faturas:
            self.pdf.cell(35, 6, str(fatura.get("mes_ano", "-")), border=1, align="C")
            self.pdf.cell(45, 6, f"{fatura.get('consumo_kwh', 0.0):.1f} kWh", border=1, align="C")
            self.pdf.cell(45, 6, f"R$ {fatura.get('valor_total', 0.0):.2f}", border=1, align="C")
            self.pdf.cell(55, 6, str(fatura.get("bandeira", "Verde")), border=1, align="C", ln=True)

        # Retorna o PDF compilado em bytes (compatível com o st.download_button do Streamlit)
        return bytes(self.pdf.output())
    
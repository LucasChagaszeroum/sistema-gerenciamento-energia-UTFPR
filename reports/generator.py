import io
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

class TechnicalReportGenerator:
    """
    Módulo para geração automática de relatórios técnicos em PDF 
    para documentação de experimentos de Iniciação Científica (UTFPR).
    """
    @staticmethod
    def gerar_pdf_experimento(
        modelo_campeao: str,
        mae: float,
        custo_mensal: float,
        custo_anual: float,
        picp: float,
        loss_p5: float,
        loss_p95: float
    ) -> bytes:
        # Buffer de memória para armazenar o PDF gerado sem salvar em disco
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36
        )

        elements = []
        styles = getSampleStyleSheet()

        # Estilos customizados para formatação técnica
        title_style = ParagraphStyle(
            'TitleStyle',
            parent=styles['Heading1'],
            fontSize=18,
            textColor=colors.HexColor("#003366"),
            spaceAfter=12
        )
        
        body_style = ParagraphStyle(
            'BodyStyle',
            parent=styles['Normal'],
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#333333")
        )

        # Cabeçalho do Relatório
        elements.append(Paragraph("<b>UTFPR - Universidade Tecnológica Federal do Paraná</b>", body_style))
        elements.append(Paragraph("<b>Sistema de Gerenciamento e Previsão de Carga Elétrica</b>", body_style))
        elements.append(Spacer(1, 10))
        elements.append(Paragraph("📄 Relatório Técnico de Experimentos e Validação Metrológica", title_style))
        elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#003366"), spaceAfter=15))

        # Seção 1: Resumo do Modelo Selecionado e Impacto Financeiro
        elements.append(Paragraph("<b>1. Desempenho Operacional & Tradução Financeira</b>", styles['Heading2']))
        
        dados_tabela_1 = [
            ["Métrica / Parâmetro", "Valor Estimado"],
            ["Modelo Campeão Selecionado", modelo_campeao],
            ["Erro Médio Absoluto (MAE)", f"{mae:.2f} kW"],
            ["Custo Mensal do Erro (Tarifa A4 COPEL)", f"R$ {custo_mensal:,.2f}"],
            ["Risco Financeiro Anual Projetado", f"R$ {custo_anual:,.2f}"]
        ]

        tabela_1 = Table(dados_tabela_1, colWidths=[250, 250])
        tabela_1.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#003366")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor("#F5F5F5")),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
        ]))
        elements.append(tabela_1)
        elements.append(Spacer(1, 15))

        # Seção 2: Validação Probabilística do Intervalo de Predição (PICP)
        elements.append(Paragraph("<b>2. Avaliação Metrológica de Quantis (Incerteza)</b>", styles['Heading2']))
        
        dados_tabela_2 = [
            ["Métrica Metrológica", "Resultado", "Meta Nominal"],
            ["Perda Pinball (Quantil P5)", f"{loss_p5:.4f}", "Minimização"],
            ["Perda Pinball (Quantil P95)", f"{loss_p95:.4f}", "Minimização"],
            ["Cobertura Empírica (PICP)", f"{picp:.2f}%", ">= 85.0%"]
        ]

        tabela_2 = Table(dados_tabela_2, colWidths=[200, 150, 150])
        tabela_2.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#003366")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor("#F5F5F5")),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
        ]))
        elements.append(tabela_2)
        elements.append(Spacer(1, 15))

        # Parecer Técnico Conclusivo
        status_picp = "VALIDADO" if picp >= 85.0 else "SUBESTIMADO"
        parecer_texto = (
            f"<b>Parecer Técnico Final:</b> O modelo quantílico foi classificado como <b>{status_picp}</b>. "
            f"Com uma cobertura empírica de <b>{picp:.2f}%</b>, as bandas preditivas englobam adequadamente "
            f"as flutuações de demanda na rede elétrica, assegurando previsibilidade operacional."
        )
        elements.append(Paragraph(parecer_texto, body_style))

        # Construção final do arquivo em memória
        doc.build(elements)
        buffer.seek(0)
        return buffer.getvalue()
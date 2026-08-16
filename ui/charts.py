import plotly.graph_objects as go
import pandas as pd

def gerar_curva_carga_interativa(df_telemetria: pd.DataFrame, demanda_contratada_kw: float) -> go.Figure:
    """
    Gera um gráfico interativo de curva de carga diária com destaque para o
    Horário de Ponta (18h as 21h) e a linha limite de Demanda Contratada.
    """
    fig = go.Figure()

    # Linha principal de Demanda Medida (kW)
    fig.add_trace(go.Scatter(
        x=df_telemetria['horario'],
        y=df_telemetria['demanda_kw'],
        mode='lines',
        name='Demanda Medida (kW)',
        line=dict(color='#0066CC', width=2)
    ))

    # Linha limite de Demanda Contratada
    fig.add_hline(
        y=demanda_contratada_kw,
        line_dash="dash",
        line_color="red",
        annotation_text=f"Demanda Contratada ({demanda_contratada_kw} kW)",
        annotation_position="top right"
    )

    # Sombreamento visual para o Horário de Ponta (18:00 as 21:00)
    fig.add_vrect(
        x0="18:00", x1="21:00",
        fillcolor="orange", opacity=0.2,
        layer="below", line_width=0,
        annotation_text="Horário de Ponta (Tarifa Elevada)",
        annotation_position="top left"
    )

    fig.update_layout(
        title="Curva de Carga Diária de Telemetria (Intervalos de 15 min)",
        xaxis_title="Horário do Dia",
        yaxis_title="Demanda de Potência (kW)",
        template="plotly_white",
        hovermode="x unified"
    )

    return fig
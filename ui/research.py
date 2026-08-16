import lightgbm as lgb
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shap
import streamlit as st
import xgboost as xgb
from sklearn.inspection import partial_dependence
from sklearn.preprocessing import StandardScaler

# Importação dos pacotes internos da aplicação (IC - UTFPR)
from analysis.drift import AdvancedDriftMonitor
from analysis.validation import cohens_d, diebold_mariano_test
from data.database import DatabaseManager
from features.feature_engineering import (
    FeatureEngineer,  # Importação única e oficial da pasta features/
)
from models.ensemble import EnsembleModelPipeline


def calcular_pinball_loss(
    y_true: np.ndarray, y_pred: np.ndarray, alpha: float
) -> float:
  """Calcula o Pinball Loss para avaliação metrológica de quantis em previsão de carga."""
  erro = y_true - y_pred
  # Função de perda assimétrica para quantis (P5, P95)
  return float(np.mean(np.maximum(alpha * erro, (alpha - 1) * erro)))


def render_research_ui(db: DatabaseManager):
  """Renderiza a interface do módulo de Pesquisa e Iniciação Científica (UTFPR)."""
  st.header("🔬 Módulo de Pesquisa & Experimentos (UTFPR)")

  # Carrega os dados de telemetria do banco SQLite
  df_raw = db.carregar_dados()
  if df_raw.empty:
    db.carregar_dados_reais_ou_simulados()
    df_raw = db.carregar_dados()

  st.sidebar.subheader("🕹️ Experimentos de IC")
  opcao = st.sidebar.radio(
      "Selecione o experimento:",
      [
          "📊 Benchmarking & Validação Estatística",
          "🔮 Previsão Probabilística (Quantis)",
          "🧠 XAI: Importância de Atributos & PDP",
          "📉 Detecção de Data Drift (PSI)",
      ],
  )

  # Preditores explicativos selecionados para as séries temporais
  cols_x = [
      "lag_24",
      "lag_72",
      "lag_168",
      "lag_336",
      "rolling_mean_168",
      "rolling_std_24",
      "rolling_std_168",
      "ewma_24",
      "interacao_temp_hora",
      "sin_hora",
      "cos_hora",
      "causal_trend",
      "causal_seasonal_24",
  ]

  # EXPERIMENTO 1: BENCHMARKING E VALIDAÇÃO FINANCEIRA
  if opcao == "📊 Benchmarking & Validação Estatística":
    st.subheader("📊 Validação Estatística e Tradução Financeira do Erro")
    if st.button("Executar Pipeline de Validação Completa", type="primary"):
      with st.spinner(
          "Processando features, treinando Ensemble e executando testes"
          " estatísticos..."
      ):
        # 1. Engenharia de Atributos e Split Temporal
        df_proc, split_idx = FeatureEngineer.processar_features(df_raw)
        X = df_proc[cols_x].values
        y = df_proc["demanda_kw"].values

        X_tr, X_te = X[:split_idx], X[split_idx:]
        y_tr, y_te = y[:split_idx], y[split_idx:]

        # 2. Padronização Z-score das variáveis preditoras
        scaler = StandardScaler()
        X_tr_sc = scaler.fit_transform(X_tr)
        X_te_sc = scaler.transform(X_te)

        # 3. Treinamento do Ensemble
        pipeline = EnsembleModelPipeline(seed=42)
        preds_dict = pipeline.fit_predict_ensemble(X_tr_sc, y_tr, X_te_sc)

        # 4. Avaliação Metrológica e Financeira (Tarifa A4 COPEL)
        mae_kw = float(np.mean(np.abs(y_te - preds_dict["Ensemble_Weighted"])))
        tarifa_demanda_anual = 38.50 * 12  # R$/kW/ano
        custo_erro_anual = mae_kw * tarifa_demanda_anual

        # Testes de Hipótese Estatística
        dm_p_value = diebold_mariano_test(
            y_te, preds_dict["Ensemble_Weighted"], preds_dict["XGBoost"]
        )
        eff_size = cohens_d(
            y_te - preds_dict["Ensemble_Weighted"],
            y_te - preds_dict["XGBoost"],
        )

        st.success("Validação concluída com sucesso!")

        m1, m2, m3 = st.columns(3)
        m1.metric("Erro Médio (MAE)", f"{mae_kw:.2f} kW")
        m2.metric("Custo do Erro (Mensal)", f"R$ {(custo_erro_anual/12):,.2f}")
        m3.metric("Risco Financeiro (Anual)", f"R$ {custo_erro_anual:,.2f}")

        st.markdown(
            "**Diebold-Mariano Test (Ensemble vs XGBoost):** p-valor ="
            f" `{dm_p_value:.5f}`"
        )
        st.markdown(f"**Tamanho de Efeito (Cohen's d):** `{eff_size:.4f}`")

  # EXPERIMENTO 2: PREVISÃO PROBABILÍSTICA
  elif opcao == "🔮 Previsão Probabilística (Quantis)":
    st.subheader("🔮 Avaliação Metrológica de Quantis (Pinball Loss & Coverage)")

    with st.spinner("Treinando regressors quantílicos via LightGBM..."):
      df_proc, split_idx = FeatureEngineer.processar_features(df_raw)
      X = df_proc[cols_x].values
      y = df_proc["demanda_kw"].values
      X_tr, X_te = X[:split_idx], X[split_idx:]
      y_tr, y_te = y[:split_idx], y[split_idx:]

      # Regressores quantílicos de P5 e P95
      m_p5 = lgb.LGBMRegressor(
          objective="quantile", alpha=0.05, random_state=42, verbose=-1
      ).fit(X_tr, y_tr)
      m_p95 = lgb.LGBMRegressor(
          objective="quantile", alpha=0.95, random_state=42, verbose=-1
      ).fit(X_tr, y_tr)

      p5 = m_p5.predict(X_te)
      p95 = m_p95.predict(X_te)

      loss_p5 = calcular_pinball_loss(y_te, p5, 0.05)
      loss_p95 = calcular_pinball_loss(y_te, p95, 0.95)
      picp = np.mean((y_te >= p5) & (y_te <= p95)) * 100

      c1, c2, c3 = st.columns(3)
      c1.metric("Pinball Loss (P5)", f"{loss_p5:.4f}")
      c2.metric("Pinball Loss (P95)", f"{loss_p95:.4f}")
      c3.metric("Cobertura de Intervalo (PICP)", f"{picp:.2f}%")

  # EXPERIMENTO 3: INTERPRETABILIDADE (XAI)
  elif opcao == "🧠 XAI: Importância de Atributos & PDP":
    st.subheader(
        "🧠 Interpretabilidade do Modelo via SHAP e Dependência Parcial (PDP)"
    )

    with st.spinner("Calculando valores de SHAP e curvas de dependência..."):
      df_proc, _ = FeatureEngineer.processar_features(df_raw)
      X = df_proc[cols_x].values
      y = df_proc["demanda_kw"].values

      model = xgb.XGBRegressor(random_state=42).fit(X, y)

      tab_shap, tab_pdp = st.tabs([
          "🔥 Relevância das Variáveis (SHAP)",
          "📈 Gráfico de Dependência Parcial (PDP)",
      ])

      with tab_shap:
        explainer = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(X)

        fig_shap, ax_shap = plt.subplots(figsize=(8, 5))
        shap.summary_plot(shap_values, df_proc[cols_x], show=False)
        st.pyplot(fig_shap)
        plt.close(fig_shap)

      with tab_pdp:
        pdp_results = partial_dependence(
            model, X, features=[cols_x.index("interacao_temp_hora")]
        )
        fig_pdp, ax_pdp = plt.subplots(figsize=(8, 4))
        ax_pdp.plot(
            pdp_results["grid_values"][0],
            pdp_results["average"][0],
            color="tab:blue",
            lw=2,
        )
        ax_pdp.set_xlabel("Interação Temperatura x Hora")
        ax_pdp.set_ylabel("Impacto na Demanda Prevista (kW)")
        ax_pdp.grid(True)
        st.pyplot(fig_pdp)
        plt.close(fig_pdp)

  # EXPERIMENTO 4: DATA DRIFT (PSI)
  elif opcao == "📉 Detecção de Data Drift (PSI)":
    st.subheader("📉 Monitoramento Estatístico de Instabilidade de Dados (PSI)")
    df_proc, split_idx = FeatureEngineer.processar_features(df_raw)
    X = df_proc[cols_x].values
    X_tr, X_te = X[:split_idx], X[split_idx:]

    psi_list = []
    for i, col in enumerate(cols_x):
      psi_val = AdvancedDriftMonitor.calculate_psi(X_tr[:, i], X_te[:, i])
      psi_list.append({
          "Variável": col,
          "Índice PSI": round(psi_val, 4),
          "Status": "⚠️ Drift Elevado (>0.2)" if psi_val > 0.2 else "✅ Estável",
      })

    st.dataframe(pd.DataFrame(psi_list), use_container_width=True)
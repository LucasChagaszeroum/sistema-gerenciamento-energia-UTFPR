import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import mean_absolute_error
from sklearn.inspection import partial_dependence
import xgboost as xgb
import lightgbm as lgb

# Importações dos módulos internos
from data.database import DatabaseManager
from features.feature_engineering import FeatureEngineer
from models.ensemble import EnsembleModelPipeline
from analysis.drift import AdvancedDriftMonitor
from analysis.validation import diebold_mariano_test, cohens_d

def render_research_ui(db: DatabaseManager):
    """Renderiza a interface do módulo de Pesquisa e Iniciação Científica."""
    st.header("🔬 Módulo de Pesquisa & Experimentos (UTFPR)")

    # Carrega os dados reais ou simulados do banco
    df_raw = db.carregar_dados()
    if df_raw.empty:
        st.warning("Nenhum dado encontrado no banco. Gerando base de simulação...")
        db.carregar_dados_reais_ou_simulados()
        df_raw = db.carregar_dados()

    # Menu lateral interno para navegação de experimentos
    st.sidebar.subheader("🕹️ Ferramentas de Pesquisa")
    opcao = st.sidebar.radio("Selecione o experimento:", [
        "📊 Benchmarking & Validacao Estatistica",
        "🔮 Previsao Probabilistica",
        "🧠 XAI: SHAP & PDP",
        "📉 Detecao de Drift (PSI)"
    ])

    cols_x = [
        'lag_24', 'lag_72', 'lag_168', 'lag_336',
        'rolling_mean_168', 'rolling_std_24', 'rolling_std_168', 'ewma_24',
        'interacao_temp_hora', 'sin_hora', 'cos_hora',
        'causal_trend', 'causal_seasonal_24'
    ]

    # Experimento 1: Benchmarking e Diebold-Mariano
    if opcao == "📊 Benchmarking & Validacao Estatistica":
        st.subheader("📊 Avaliação de Desempenho e Validação Estatística")
        if st.button("Executar Pipeline de Validação Completa"):
            with st.spinner("Processando dados e otimizando modelos..."):
                df_proc, split_idx = FeatureEngineer.processar_features(df_raw)
                X = df_proc[cols_x].values
                y = df_proc['demanda_kw'].values

                X_tr, X_te = X[:split_idx], X[split_idx:]
                y_tr, y_te = y[:split_idx], y[split_idx:]

                scaler = StandardScaler()
                X_tr_sc = scaler.fit_transform(X_tr)
                X_te_sc = scaler.transform(X_te)

                # Treina pipeline Ensemble
                pipeline = EnsembleModelPipeline(seed=42)
                preds_dict = pipeline.fit_predict_ensemble(X_tr_sc, y_tr, X_te_sc)

                # Teste estatístico de Diebold-Mariano
                dm_p_value = diebold_mariano_test(y_te, preds_dict['Ensemble_Weighted'], preds_dict['XGBoost'])
                eff_size = cohens_d(y_te - preds_dict['Ensemble_Weighted'], y_te - preds_dict['XGBoost'])

                st.success("Otimização e validação concluídas!")
                st.markdown(f"**Diebold-Mariano Test (Ensemble vs XGBoost):** p-valor = `{dm_p_value:.5f}`")
                st.markdown(f"**Tamanho de Efeito (Cohen's d):** `{eff_size:.4f}`")

    # Experimento 2: Previsão Probabilística
    elif opcao == "🔮 Previsao Probabilistica":
        st.subheader("🔮 Avaliação Metrológica de Quantis")
        df_proc, split_idx = FeatureEngineer.processar_features(df_raw)
        X = df_proc[cols_x].values
        y = df_proc['demanda_kw'].values
        X_tr, X_te = X[:split_idx], X[split_idx:]
        y_tr, y_te = y[:split_idx], y[split_idx:]

        m_p5 = lgb.LGBMRegressor(objective="quantile", alpha=0.05, random_state=42, verbose=-1).fit(X_tr, y_tr)
        m_p95 = lgb.LGBMRegressor(objective="quantile", alpha=0.95, random_state=42, verbose=-1).fit(X_tr, y_tr)

        p5 = m_p5.predict(X_te)
        p95 = m_p95.predict(X_te)

        st.metric("Intervalo de Cobertura (PICP)", f"{np.mean((y_te >= p5) & (y_te <= p95)) * 100:.2f}%")

    # Experimento 3: Interpretabilidade (XAI)
    elif opcao == "🧠 XAI: SHAP & PDP":
        st.subheader("🧠 Interpretabilidade de Modelos")
        df_proc, _ = FeatureEngineer.processar_features(df_raw)
        X = df_proc[cols_x].values
        y = df_proc['demanda_kw'].values

        m = xgb.XGBRegressor(random_state=42).fit(X, y)
        pdp_results = partial_dependence(m, X, features=[cols_x.index('interacao_temp_hora')])
        
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.plot(pdp_results['grid_values'][0], pdp_results['average'][0])
        ax.set_xlabel("Interação Temperatura-Hora")
        ax.set_ylabel("Impacto na Demanda Prevista (kW)")
        ax.grid(True)
        st.pyplot(fig)

    # Experimento 4: Monitoramento de Data Drift
    elif opcao == "📉 Detecao de Drift (PSI)":
        st.subheader("📉 Monitoramento Estatístico de Data Drift (PSI)")
        df_proc, split_idx = FeatureEngineer.processar_features(df_raw)
        X = df_proc[cols_x].values
        X_tr, X_te = X[:split_idx], X[split_idx:]

        psi_list = []
        for i, col in enumerate(cols_x):
            psi_val = AdvancedDriftMonitor.calculate_psi(X_tr[:, i], X_te[:, i])
            psi_list.append({"Feature": col, "PSI": psi_val, "Status": "Drift Elevado" if psi_val > 0.2 else "Estável"})

        st.dataframe(pd.DataFrame(psi_list), use_container_width=True)
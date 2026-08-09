# Função para cálculo do erro assimétrico de quantil (Pinball Loss / Quantile Loss)
def calcular_pinball_loss(y_true: np.ndarray, y_pred: np.ndarray, alpha: float) -> float:
    """
    Calcula o Pinball Loss para avaliação metrológica de quantis.
    L(y, y_hat) = max(alpha * (y - y_hat), (alpha - 1) * (y - y_hat))
    """
    erro = y_true - y_pred
    return float(np.mean(np.maximum(alpha * erro, (alpha - 1) * erro)))

# Experimento 2: Previsão Probabilística e Avaliação Metrológica
elif opcao == "🔮 Previsao Probabilistica":
    st.subheader("🔮 Avaliação Metrológica de Quantis (Pinball Loss & Coverage)")

    with st.spinner("Treinando regressão quantílica para P5 e P95..."):
        # Processamento de lags e divisão da série temporal
        df_proc, split_idx = FeatureEngineer.processar_features(df_raw)
        X = df_proc[cols_x].values
        y = df_proc['demanda_kw'].values
        X_tr, X_te = X[:split_idx], X[split_idx:]
        y_tr, y_te = y[:split_idx], y[split_idx:]

        # Modelo LightGBM otimizado para o quantil de 5% (Limite Inferior)
        m_p5 = lgb.LGBMRegressor(objective="quantile", alpha=0.05, random_state=42, verbose=-1)
        m_p5.fit(X_tr, y_tr)

        # Modelo LightGBM otimizado para o quantil de 95% (Limite Superior)
        m_p95 = lgb.LGBMRegressor(objective="quantile", alpha=0.95, random_state=42, verbose=-1)
        m_p95.fit(X_tr, y_tr)

        # Gera predições para os conjuntos de teste
        p5 = m_p5.predict(X_te)
        p95 = m_p95.predict(X_te)

        # Métricas metrológicas
        loss_p5 = calcular_pinball_loss(y_te, p5, 0.05)
        loss_p95 = calcular_pinball_loss(y_te, p95, 0.95)
        picp = np.mean((y_te >= p5) & (y_te <= p95)) * 100

        # Exibição dos três indicadores em colunas
        c1, c2, c3 = st.columns(3)
        c1.metric("Pinball Loss (P5)", f"{loss_p5:.4f}")
        c2.metric("Pinball Loss (P95)", f"{loss_p95:.4f}")
        c3.metric("Prediction Interval Coverage Probability (PICP)", f"{picp:.2f}%")
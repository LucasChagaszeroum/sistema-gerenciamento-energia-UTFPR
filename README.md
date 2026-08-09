# ⚡ Plataforma Integrada de Inteligência Energética (UTFPR)

Plataforma avançada de previsão de carga elétrica, monitoramento estatístico de estabilidade de dados e explicabilidade de modelos (XAI), desenvolvida para aplicações em sistemas de energia elétrica na **Universidade Tecnológica Federal do Paraná (UTFPR)**.

---

## 🚀 Funcionalidades do Sistema

1. **Benchmarking e Validação Cruzada Aninhada (Nested CV):**
   - Combinação de modelos de Machine Learning (XGBoost, LightGBM, CatBoost e Random Forest) via Ensemble com pesos ponderados por Softmax Negativo.
   - Otimização de hiperparâmetros automatizada com **Optuna** (incluindo *Pruning* e busca paralela).
   - Validação estatística de desempenho utilizando o **Teste de Diebold-Mariano** e tamanho de efeito (*Cohen's d*).

2. **Deep Learning Temporal:**
   - Implementação de arquitetura baseada em **Transformer Encoder** com atenção multi-head e máscara causal em PyTorch, suportando *Automatic Mixed Precision (AMP)*.

3. **Previsão Probabilística:**
   - Quantilagem preditiva ($P_5, P_{50}, P_{95}$) avaliada por meio de *Pinball Loss* e probabilidade de cobertura de intervalo (*PICP*).

4. **Inteligência Artificial Explicável (XAI):**
   - Gráficos de dependência parcial (*PDP*) e análise de importância de atributos para interpretabilidade operacional.

5. **Monitoramento de Concept & Data Drift:**
   - Cálculo automatizado do **Population Stability Index (PSI)** e monitoramento adaptativo de janelas (*ADWIN*).

6. **Interface Web Interativa & MLOps:**
   - Dashboard completo construído em **Streamlit**.
   - Persistência relacional utilizando **SQLAlchemy** (SQLite/PostgreSQL) e rastreamento de experimentos com **MLflow**.

---

## 🛠️ Tecnologias Utilizadas

* **Linguagem:** Python 3.10+
* **Machine Learning & Otimização:** Scikit-Learn, XGBoost, LightGBM, CatBoost, Optuna
* **Deep Learning:** PyTorch
* **Estatística & Métricas:** SciPy, Statsmodels, Scikit-Posthocs
* **Interface & Visualização:** Streamlit, Plotly, Matplotlib, Seaborn
* **Banco de Dados & MLOps:** SQLAlchemy, MLflow, Docker, GitHub Actions

---

## ⚙️ Como Executar o Projeto Localmente

1. **Clone o repositório:**
   ```bash
   git clone [https://github.com/seu-usuario/seu-repositorio.git](https://github.com/seu-usuario/seu-repositorio.git)
   cd seu-repositorio
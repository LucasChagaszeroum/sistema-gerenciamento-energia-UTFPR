# ⚡ Plataforma Integrada de Inteligência Energética (UTFPR)

Sistema modular avançado de análise de consumo elétrico, previsão de demanda, monitoramento de estabilidade de dados (Data Drift) e interpretabilidade (XAI). Desenvolvido como projeto de Iniciação Científica na **Universidade Tecnológica Federal do Paraná (UTFPR)**.

---

## 🏛️ Arquitetura e Módulos da Aplicação

A plataforma é dividida em três grandes perfis operacionais:

1. **🏠 Módulo Residencial:**
   - **Upload e OCR de Faturas:** Extração semi-automatizada de dados de faturas (PDF/Imagem) com etapa obrigatoria de validação humana para evitar contaminação do banco de dados.
   - **Diagnóstico Estatístico:** Avaliação do histórico de consumo mensal, cálculo de média, desvio padrão e detecção de anomalias estatísticas (+2σ).
   - **Motor de Recomendações:** Sistema de IA baseado em evidências que gera orientações técnicas de economia com indicação de confiança.

2. **🏭 Módulo Industrial:**
   - **Análise Causal de Carga:** Acompanhamento da demanda horária em kW, curvas de carga e monitoramento do fator de potência.
   - **Séries Temporais Avançadas:** Janelas deslizantes (*lags* de 24h a 336h) e tendências sazonais integradas.

3. **🔬 Módulo de Pesquisa & Experimentos (IC):**
   - **Benchmarking & Ensemble:** Combinação de modelos XGBoost, LightGBM, CatBoost e Random Forest via *Softmax Negativo*.
   - **Otimização de Hiperparâmetros:** Optuna com algoritmo de poda (*Pruning*) e busca paralela.
   - **Deep Learning Temporal:** Redes **Transformer Encoder** em PyTorch com máscara causal e aceleração por *Automatic Mixed Precision (AMP)*.
   - **Validação Estatística:** Teste de **Diebold-Mariano** e tamanho de efeito (*Cohen's d*).
   - **Monitoramento & XAI:** Detecção de drift via **Population Stability Index (PSI)**, algoritmo **ADWIN**, gráficos de dependência parcial (**PDP**) e **SHAP**.

---

## 📂 Estrutura Modular do Código

```text
plataforma_energia/
├── app.py                      # Orquestrador e roteador principal
├── requirements.txt            # Dependências do projeto
├── README.md                   # Documentação
│
├── data/                       # Camada de Persistência e Parsers
│   ├── database.py             # Gerenciador SQLAlchemy (SQLite/PostgreSQL)
│   └── invoice_parser.py       # Extração e OCR de faturas residenciais
│
├── analysis/                   # Processamento e Diagnósticos
│   └── residential.py          # Análise estatística de faturas
│
├── ai/                         # Inteligência e Regras de Negócio
│   └── recommendations.py      # Motor de recomendações de eficiência
│
└── ui/                         # Interface do Usuário (Streamlit)
    └── residential.py          # Renderização do módulo residencial
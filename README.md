# ⚡ Sistema Integrado de Gerenciamento de Energia — IC UTFPR

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.28%2B-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io/)
[![SQLite](https://img.shields.io/badge/SQLite-3-003B57?logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

Aplicação web interativa desenvolvida em **Python** para monitoramento de demanda elétrica, cálculo de vetores de potência, auditoria de conformidade regulatória (normativa da ANEEL) e automação de laudos técnicos em PDF.

Este projeto faz parte da pesquisa de **Iniciação Científica na UTFPR (Universidade Tecnológica Federal do Paraná)**, focada no desenvolvimento de ferramentas computacionais aplicadas à gestão e eficiência energética.

---

## 📌 Funcionalidades Principais

- **📊 Dashboard & Analytics em Tempo Real:**
  - Métricas dinâmicas de Demanda Média, Demanda Máxima, Fator de Carga ($FC$) e Fator de Potência ($FP$).
  - Alerta regulatório automatizado para instalações com $FP < 0{,}92$ (passíveis de ajuste/penalização por reativos).
  - Gráfico interativo em **Plotly** para comparação entre Potência Ativa ($kW$) e Reativa ($kvar$).

- **🧮 Modelagem Matemática e Álgebra Simbólica:**
  - Integração com a biblioteca **SymPy** para cálculo analítico do triângulo de potências e taxa de variação/sensibilidade reativa ($\frac{dQ}{dFP}$).

- **💾 Gestão de Dados (CRUD e Ingestão em Lote):**
  - Registro manual único de medições via formulário.
  - Ingestão massiva em lote a partir de ficheiros `.csv` ou `.xlsx` (Pandas).
  - Persistência e gerenciamento de leituras num banco de dados relacional **SQLite3**.

- **📑 Automação de Laudos Técnicos:**
  - Geração automática de relatórios em PDF padronizados via **ReportLab** para documentação de auditoria energética.

- **🌐 Módulo de Tarifação (Web Scraping):**
  - Consulta tarifária com mecanismo de *fallback* para estimativa de custos operacionais mensais.

---

## 🛠️ Tecnologias e Bibliotecas Utilizadas

| Camada / Módulo | Tecnologia / Biblioteca | Função no Sistema |
| :--- | :--- | :--- |
| **Interface Web** | `Streamlit` | Frontend reativo e interativo |
| **Banco de Dados** | `SQLite3` | Armazenamento relacional local |
| **Processamento de Dados** | `Pandas` & `NumPy` | Manipulação vetorial e cálculos de $S$ (kVA) e $Q$ (kvar) |
| **Estatística & Álgebra** | `SciPy` & `SymPy` | Intervalos de confiança e diferenciação simbólica |
| **Visualização de Dados** | `Plotly Express` / `Graph Objects` | Gráficos técnicos interativos |
| **Relatórios** | `ReportLab` | Geração de PDFs formais em código |
| **Coleta de Dados** | `BeautifulSoup4` & `Requests` | Web scraping de dados tarifários |

---

## 📐 Equações e Modelagem Elétrica

O backend efetua a decomposição das grandezas elétricas através do triângulo de potências:

1. **Potência Aparente ($S$):**
   $$S = \frac{P}{FP} \quad \text{[kVA]}$$

2. **Potência Reativa ($Q$):**
   $$Q = \sqrt{S^2 - P^2} = \sqrt{\left(\frac{P}{FP}\right)^2 - P^2} \quad \text{[kvar]}$$

3. **Fator de Carga ($FC$):**
   $$FC = \frac{P_{\text{média}}}{P_{\text{máxima}}}$$

---

## 🚀 Como Executar o Projeto Localmente

### Pré-requisitos
- **Python 3.10** ou superior instalado na máquina.

### Passo a Passo

1. **Clonar o Repositório:**
   ```bash
   git clone [https://github.com/teu-usuario/seu-repositorio.git](https://github.com/teu-usuario/seu-repositorio.git)
   cd seu-repositorio# ⚡ Sistema Integrado de Gerenciamento de Energia — IC UTFPR

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.28%2B-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io/)
[![SQLite](https://img.shields.io/badge/SQLite-3-003B57?logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

Aplicação web interativa desenvolvida em **Python** para monitoramento de demanda elétrica, cálculo de vetores de potência, auditoria de conformidade regulatória (normativa da ANEEL) e automação de laudos técnicos em PDF.

Este projeto faz parte da pesquisa de **Iniciação Científica na UTFPR (Universidade Tecnológica Federal do Paraná)**, focada no desenvolvimento de ferramentas computacionais aplicadas à gestão e eficiência energética.

---

## 📌 Funcionalidades Principais

- **📊 Dashboard & Analytics em Tempo Real:**
  - Métricas dinâmicas de Demanda Média, Demanda Máxima, Fator de Carga ($FC$) e Fator de Potência ($FP$).
  - Alerta regulatório automatizado para instalações com $FP < 0{,}92$ (passíveis de ajuste/penalização por reativos).
  - Gráfico interativo em **Plotly** para comparação entre Potência Ativa ($kW$) e Reativa ($kvar$).

- **🧮 Modelagem Matemática e Álgebra Simbólica:**
  - Integração com a biblioteca **SymPy** para cálculo analítico do triângulo de potências e taxa de variação/sensibilidade reativa ($\frac{dQ}{dFP}$).

- **💾 Gestão de Dados (CRUD e Ingestão em Lote):**
  - Registro manual único de medições via formulário.
  - Ingestão massiva em lote a partir de ficheiros `.csv` ou `.xlsx` (Pandas).
  - Persistência e gerenciamento de leituras num banco de dados relacional **SQLite3**.

- **📑 Automação de Laudos Técnicos:**
  - Geração automática de relatórios em PDF padronizados via **ReportLab** para documentação de auditoria energética.

- **🌐 Módulo de Tarifação (Web Scraping):**
  - Consulta tarifária com mecanismo de *fallback* para estimativa de custos operacionais mensais.

---

## 🛠️ Tecnologias e Bibliotecas Utilizadas

| Camada / Módulo | Tecnologia / Biblioteca | Função no Sistema |
| :--- | :--- | :--- |
| **Interface Web** | `Streamlit` | Frontend reativo e interativo |
| **Banco de Dados** | `SQLite3` | Armazenamento relacional local |
| **Processamento de Dados** | `Pandas` & `NumPy` | Manipulação vetorial e cálculos de $S$ (kVA) e $Q$ (kvar) |
| **Estatística & Álgebra** | `SciPy` & `SymPy` | Intervalos de confiança e diferenciação simbólica |
| **Visualização de Dados** | `Plotly Express` / `Graph Objects` | Gráficos técnicos interativos |
| **Relatórios** | `ReportLab` | Geração de PDFs formais em código |
| **Coleta de Dados** | `BeautifulSoup4` & `Requests` | Web scraping de dados tarifários |

---

## 📐 Equações e Modelagem Elétrica

O backend efetua a decomposição das grandezas elétricas através do triângulo de potências:

1. **Potência Aparente ($S$):**
   $$S = \frac{P}{FP} \quad \text{[kVA]}$$

2. **Potência Reativa ($Q$):**
   $$Q = \sqrt{S^2 - P^2} = \sqrt{\left(\frac{P}{FP}\right)^2 - P^2} \quad \text{[kvar]}$$

3. **Fator de Carga ($FC$):**
   $$FC = \frac{P_{\text{média}}}{P_{\text{máxima}}}$$

---

## 🚀 Como Executar o Projeto Localmente

### Pré-requisitos
- **Python 3.10** ou superior instalado na máquina.

### Passo a Passo

1. **Clonar o Repositório:**
   ```bash
   git clone [https://github.com/teu-usuario/seu-repositorio.git](https://github.com/teu-usuario/seu-repositorio.git)
   cd seu-repositorio
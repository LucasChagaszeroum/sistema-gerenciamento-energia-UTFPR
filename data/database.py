import os
from datetime import datetime
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.pool import QueuePool

class DatabaseManager:
    """
    Gerenciador de Banco de Dados Relacional (SQLite / PostgreSQL)
    Suporta multi-unidades: Residencial, Industrial e Experimentos da UTFPR.
    """
    def __init__(self, db_url=None):
        self.db_url = db_url or os.getenv("DATABASE_URL", "sqlite:///sistema_energia_utfpr.db")
        self.is_postgres = not self.db_url.startswith("sqlite")
        
        # Configuração da engine de conexão
        if not self.is_postgres:
            self.engine = create_engine(self.db_url, connect_args={"check_same_thread": False})
        else:
            self.engine = create_engine(self.db_url, poolclass=QueuePool, pool_size=10, max_overflow=20)
            
        self._init_db()

    def _init_db(self):
        """Inicializa as tabelas relacionais caso não existam."""
        pk_syntax = "INTEGER PRIMARY KEY AUTOINCREMENT" if not self.is_postgres else "SERIAL PRIMARY KEY"
        
        with self.engine.begin() as conn:
            # 1. Unidades Consumidoras / Residências / Indústrias
            conn.execute(text(f'''
                CREATE TABLE IF NOT EXISTS unidades (
                    id {pk_syntax},
                    nome TEXT NOT NULL,
                    tipo TEXT NOT NULL, -- 'RESIDENCIAL', 'INDUSTRIAL', 'PESQUISA'
                    cidade TEXT DEFAULT 'Ponta Grossa',
                    concessionaria TEXT DEFAULT 'COPEL',
                    tarifa_kwh REAL DEFAULT 0.85,
                    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            '''))
            
            # 2. Faturas Mensais (Foco Residencial)
            conn.execute(text(f'''
                CREATE TABLE IF NOT EXISTS faturas (
                    id {pk_syntax},
                    unidade_id INTEGER NOT NULL,
                    periodo_inicio DATE,
                    periodo_fim DATE,
                    consumo_kwh REAL NOT NULL,
                    valor_total REAL NOT NULL,
                    tarifa_kwh REAL,
                    dias_faturados INTEGER DEFAULT 30,
                    bandeira TEXT DEFAULT 'VERDE',
                    data_upload TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (unidade_id) REFERENCES unidades (id)
                )
            '''))

            # 3. Leituras Temporais de Alta Frequência (Foco Industrial / Pesquisa)
            conn.execute(text(f'''
                CREATE TABLE IF NOT EXISTS leituras (
                    id {pk_syntax},
                    unidade_id INTEGER,
                    ponto TEXT NOT NULL,
                    demanda_kw REAL NOT NULL,
                    fator_potencia REAL DEFAULT 0.92,
                    temperatura REAL, umidade REAL, irradiancia REAL,
                    velocidade_vento REAL, pressao_atm REAL,
                    feriado INTEGER DEFAULT 0, periodo_letivo INTEGER DEFAULT 1,
                    data_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (unidade_id) REFERENCES unidades (id)
                )
            '''))

            # 4. Recomendações Geradas por IA
            conn.execute(text(f'''
                CREATE TABLE IF NOT EXISTS recomendacoes (
                    id {pk_syntax},
                    unidade_id INTEGER NOT NULL,
                    categoria TEXT NOT NULL,
                    descricao TEXT NOT NULL,
                    impacto_estimado REAL, -- Economia estimada em R$ ou kWh
                    confianca REAL, -- Percentual 0-100%
                    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (unidade_id) REFERENCES unidades (id)
                )
            '''))

            # 5. Métricas de Modelos de Machine Learning (Foco Pesquisa)
            conn.execute(text(f'''
                CREATE TABLE IF NOT EXISTS metricas_modelo (
                    id {pk_syntax},
                    data_execucao TIMESTAMP,
                    modelo TEXT,
                    mae REAL, rmse REAL, r2 REAL
                )
            '''))

    # --- MÉTODOS DE MANIPULAÇÃO DE RESIDÊNCIAS E FATURAS ---
    def cadastrar_unidade(self, nome: str, tipo: str, cidade: str, concessionaria: str, tarifa_kwh: float) -> int:
        """Cadastra uma nova unidade consumidora e retorna seu ID."""
        with self.engine.begin() as conn:
            result = conn.execute(
                text("INSERT INTO unidades (nome, tipo, cidade, concessionaria, tarifa_kwh) VALUES (:n, :t, :c, :con, :tar)"),
                {"n": nome, "t": tipo, "c": cidade, "con": concessionaria, "tar": tarifa_kwh}
            )
            # Para SQLite, resgata o último ID inserido
            last_id = conn.execute(text("SELECT last_insert_rowid()")).scalar()
            return last_id

    def listar_unidades(self, tipo: str = None) -> pd.DataFrame:
        """Retorna as unidades cadastradas, podendo filtrar por tipo."""
        query = "SELECT * FROM unidades"
        params = {}
        if tipo:
            query += " WHERE tipo = :tipo"
            params["tipo"] = tipo
        with self.engine.connect() as conn:
            return pd.read_sql_query(text(query), conn, params=params)

    def salvar_fatura(self, unidade_id: int, consumo_kwh: float, valor_total: float, periodo_inicio, periodo_fim, tarifa_kwh: float = 0.85):
        """Salva uma nova fatura confirmada pelo usuário."""
        with self.engine.begin() as conn:
            conn.execute(
                text('''
                    INSERT INTO faturas (unidade_id, consumo_kwh, valor_total, periodo_inicio, periodo_fim, tarifa_kwh)
                    VALUES (:uid, :c, :v, :pi, :pf, :t)
                '''),
                {"uid": unidade_id, "c": consumo_kwh, "v": valor_total, "pi": periodo_inicio, "pf": periodo_fim, "t": tarifa_kwh}
            )

    def carregar_faturas(self, unidade_id: int) -> pd.DataFrame:
        """Carrega a série temporal mensal de faturas de uma unidade específica."""
        with self.engine.connect() as conn:
            df = pd.read_sql_query(
                text("SELECT * FROM faturas WHERE unidade_id = :uid ORDER BY periodo_fim ASC"),
                conn, params={"uid": unidade_id}
            )
        if not df.empty:
            df['periodo_fim'] = pd.to_datetime(df['periodo_fim'])
        return df
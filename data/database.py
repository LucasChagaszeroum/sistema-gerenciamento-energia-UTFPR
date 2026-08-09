import sqlite3
import pandas as pd
import numpy as np

class DatabaseManager:
    def __init__(self, db_path="sistema_energia_utfpr.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Cria as tabelas de unidades, faturas e medicoes se nao existirem."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Tabela de unidades consumidoras (Residencial / Industrial)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS unidades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT UNIQUE NOT NULL,
                    tipo TEXT NOT NULL
                )
            """)
            
            # Tabela para armazenamento de faturas de energia
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS faturas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    unidade_id INTEGER,
                    mes_referencia TEXT,
                    consumo_kwh REAL,
                    valor_total REAL,
                    FOREIGN KEY (unidade_id) REFERENCES unidades (id)
                )
            """)
            
            # Tabela para mediçoes de demanda, fator de potencia e temperatura
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS medicoes_industriais (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    data_hora TEXT,
                    demanda_kw REAL,
                    fator_potencia REAL,
                    temperatura REAL
                )
            """)
            
            # Insere uma unidade residencial padrao se a tabela estiver vazia
            cursor.execute("SELECT COUNT(*) FROM unidades WHERE tipo = 'RESIDENCIAL'")
            if cursor.fetchone()[0] == 0:
                cursor.execute("INSERT INTO unidades (nome, tipo) VALUES ('Casa 1', 'RESIDENCIAL')")
                
            conn.commit()

    def listar_unidades(self, tipo: str = "RESIDENCIAL") -> pd.DataFrame:
        """Retorna todas as unidades consumidoras cadastradas de um determinado tipo."""
        with sqlite3.connect(self.db_path) as conn:
            query = "SELECT * FROM unidades WHERE tipo = ?"
            df = pd.read_sql_query(query, conn, params=(tipo,))
            return df

    def carregar_dados(self) -> pd.DataFrame:
        """Lê a tabela de mediçoes do banco e retorna um DataFrame do Pandas."""
        with sqlite3.connect(self.db_path) as conn:
            df = pd.read_sql_query("SELECT * FROM medicoes_industriais", conn)
            if not df.empty:
                df['data_hora'] = pd.to_datetime(df['data_hora'])
            return df

    def carregar_dados_reais_ou_simulados(self):
        """Gera uma serie temporal de 30 dias (720 horas) para testes do sistema."""
        datas = pd.date_range(start="2026-07-01", periods=720, freq="h")
        horas = datas.hour

        demanda = 150 + 80 * np.sin(2 * np.pi * horas / 24) + np.random.normal(0, 12, len(datas))
        fator_pot = np.random.uniform(0.87, 0.97, len(datas))
        temp = 20 + 8 * np.sin(2 * np.pi * horas / 24) + np.random.normal(0, 2, len(datas))

        df_simulado = pd.DataFrame({
            'data_hora': datas.strftime('%Y-%m-%d %H:%M:%S'),
            'demanda_kw': np.maximum(demanda, 10),
            'fator_potencia': fator_pot,
            'temperatura': temp
        })

        with sqlite3.connect(self.db_path) as conn:
            df_simulado.to_sql('medicoes_industriais', conn, if_exists='replace', index=False)
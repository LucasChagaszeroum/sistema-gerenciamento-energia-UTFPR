import sqlite3
import pandas as pd
import numpy as np

class DatabaseManager:
    def __init__(self, db_path="sistema_energia_utfpr.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Cria a estrutura de tabelas relacionais e popula dados de teste iniciais."""
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
            
            # Tabela de faturas mensais de energia elétrica
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
            
            # Tabela de medições industriais temporais
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS medicoes_industriais (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    data_hora TEXT,
                    demanda_kw REAL,
                    fator_potencia REAL,
                    temperatura REAL
                )
            """)
            
            # Insere unidade residencial padrão se não existir nenhuma
            cursor.execute("SELECT COUNT(*) FROM unidades WHERE tipo = 'RESIDENCIAL'")
            if cursor.fetchone()[0] == 0:
                cursor.execute("INSERT INTO unidades (nome, tipo) VALUES ('casa 1', 'RESIDENCIAL')")
                
            # Popula histórico simulado de faturas se a tabela estiver vazia
            cursor.execute("SELECT COUNT(*) FROM faturas")
            if cursor.fetchone()[0] == 0:
                cursor.execute("SELECT id FROM unidades WHERE tipo = 'RESIDENCIAL' LIMIT 1")
                unidade_row = cursor.fetchone()
                if unidade_row:
                    unid_id = unidade_row[0]
                    faturas_demo = [
                        (unid_id, '2026-01', 210.5, 185.30),
                        (unid_id, '2026-02', 245.0, 215.80),
                        (unid_id, '2026-03', 198.2, 174.50),
                        (unid_id, '2026-04', 230.1, 202.40),
                        (unid_id, '2026-05', 260.8, 235.10),
                        (unid_id, '2026-06', 215.4, 189.90)
                    ]
                    cursor.executemany("""
                        INSERT INTO faturas (unidade_id, mes_referencia, consumo_kwh, valor_total)
                        VALUES (?, ?, ?, ?)
                    """, faturas_demo)
                    
            conn.commit()

    def listar_unidades(self, tipo: str = "RESIDENCIAL") -> pd.DataFrame:
        """Busca todas as unidades consumidoras cadastradas por tipo."""
        with sqlite3.connect(self.db_path) as conn:
            query = "SELECT * FROM unidades WHERE tipo = ?"
            return pd.read_sql_query(query, conn, params=(tipo,))

    def carregar_faturas(self, unidade: str) -> pd.DataFrame:
        """
        Retorna o histórico de faturas registradas para a unidade informada.
        Permite consulta tanto pelo nome da unidade quanto pelo ID.
        """
        with sqlite3.connect(self.db_path) as conn:
            query = """
                SELECT f.id, f.mes_referencia, f.consumo_kwh, f.valor_total
                FROM faturas f
                JOIN unidades u ON f.unidade_id = u.id
                WHERE u.nome = ? OR u.id = ?
                ORDER BY f.mes_referencia ASC
            """
            return pd.read_sql_query(query, conn, params=(str(unidade), str(unidade)))

    def carregar_dados(self) -> pd.DataFrame:
        """Lê os registros da tabela de medições industriais."""
        with sqlite3.connect(self.db_path) as conn:
            df = pd.read_sql_query("SELECT * FROM medicoes_industriais", conn)
            if not df.empty:
                df['data_hora'] = pd.to_datetime(df['data_hora'])
            return df

    def carregar_dados_reais_ou_simulados(self):
        """Gera série temporal sintética de 30 dias para testes da curva de carga."""
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
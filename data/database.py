import os
import sqlite3
import numpy as np
import pandas as pd


class DatabaseManager:
  """Gerenciador de banco de dados SQLite3 com autorrecuperação de esquema para o sistema de energia (UTFPR)."""

  def __init__(self, db_path="sistema_energia_utfpr.db"):
    self.db_path = db_path
    self._init_db()

  def _init_db(self):
    """Inicializa as tabelas do banco com suporte a unidades, faturas e medições."""
    try:
      with sqlite3.connect(self.db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON;")

        # 1. Tabela de Unidades Consumidoras (com atributos de tarifa e localidade)
        cursor.execute("""
                    CREATE TABLE IF NOT EXISTS unidades (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        nome TEXT UNIQUE NOT NULL,
                        tipo TEXT NOT NULL,
                        cidade TEXT DEFAULT 'Ponta Grossa',
                        concessionaria TEXT DEFAULT 'COPEL',
                        tarifa REAL DEFAULT 0.85
                    )
                """)

        # 2. Tabela de Faturas Mensais de Energia
        cursor.execute("""
                    CREATE TABLE IF NOT EXISTS faturas (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        unidade_id INTEGER NOT NULL,
                        mes_referencia TEXT NOT NULL,
                        consumo_kwh REAL NOT NULL,
                        valor_total REAL NOT NULL,
                        FOREIGN KEY (unidade_id) REFERENCES unidades (id) ON DELETE CASCADE
                    )
                """)

        # 3. Tabela de Medições Industriais
        cursor.execute("""
                    CREATE TABLE IF NOT EXISTS medicoes_industriais (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        data_hora TEXT NOT NULL,
                        demanda_kw REAL NOT NULL,
                        fator_potencia REAL NOT NULL,
                        temperatura REAL NOT NULL
                    )
                """)

        # Garante registro da unidade residencial inicial 'casa 1'
        cursor.execute("SELECT id FROM unidades WHERE nome = 'casa 1'")
        unidade = cursor.fetchone()

        if not unidade:
          cursor.execute("""
                        INSERT INTO unidades (nome, tipo, cidade, concessionaria, tarifa) 
                        VALUES ('casa 1', 'RESIDENCIAL', 'Ponta Grossa', 'COPEL', 0.85)
                    """)
          conn.commit()
          cursor.execute("SELECT id FROM unidades WHERE nome = 'casa 1'")
          unidade = cursor.fetchone()

        unid_id = unidade[0]

        # Popula histórico de faturas demonstrativas
        cursor.execute("SELECT COUNT(*) FROM faturas")
        if cursor.fetchone()[0] == 0:
          faturas_demo = [
              (unid_id, "2026-01", 210.5, 185.30),
              (unid_id, "2026-02", 245.0, 215.80),
              (unid_id, "2026-03", 198.2, 174.50),
              (unid_id, "2026-04", 230.1, 202.40),
              (unid_id, "2026-05", 260.8, 235.10),
              (unid_id, "2026-06", 215.4, 189.90),
          ]
          cursor.executemany(
              """
                        INSERT INTO faturas (unidade_id, mes_referencia, consumo_kwh, valor_total)
                        VALUES (?, ?, ?, ?)
                    """,
              faturas_demo,
          )

        conn.commit()

    except sqlite3.OperationalError:
      # Se o esquema do arquivo local estiver desatualizado, recria o banco limpo
      if os.path.exists(self.db_path):
        os.remove(self.db_path)
      self._init_db()

  def listar_unidades(self, tipo: str = "RESIDENCIAL") -> pd.DataFrame:
    """Retorna todas as unidades consumidoras cadastradas por tipo."""
    with sqlite3.connect(self.db_path) as conn:
      query = "SELECT * FROM unidades WHERE tipo = ?"
      return pd.read_sql_query(query, conn, params=(tipo,))

  def cadastrar_unidade(
      self,
      nome: str,
      tipo: str,
      cidade: str = "Ponta Grossa",
      concessionaria: str = "COPEL",
      tarifa: float = 0.85,
  ) -> int:
    """Insere uma nova unidade consumidora no SQLite3 e retorna seu ID."""
    with sqlite3.connect(self.db_path) as conn:
      cursor = conn.cursor()
      cursor.execute(
          """
                INSERT INTO unidades (nome, tipo, cidade, concessionaria, tarifa)
                VALUES (?, ?, ?, ?, ?)
            """,
          (nome, tipo, cidade, concessionaria, tarifa),
      )
      conn.commit()
      return cursor.lastrowid

  def carregar_faturas(self, unidade_id) -> pd.DataFrame:
    """Carrega o histórico mensal mapeando 'mes_referencia' e 'periodo_fim' para exibição nos gráficos."""
    with sqlite3.connect(self.db_path) as conn:
      query = """
                SELECT 
                    f.id, 
                    f.mes_referencia, 
                    f.mes_referencia AS periodo_fim, 
                    f.consumo_kwh, 
                    f.valor_total
                FROM faturas f
                WHERE f.unidade_id = ? OR f.unidade_id = (SELECT id FROM unidades WHERE nome = ? LIMIT 1)
                ORDER BY f.mes_referencia ASC
            """
      return pd.read_sql_query(
          query, conn, params=(str(unidade_id), str(unidade_id))
      )

  def salvar_fatura(
      self, unidade_id, consumo_kwh: float, valor_total: float, p_inicio, p_fim
  ):
    """Insere uma nova fatura confirmada no banco de dados."""
    mes_ref = p_fim.strftime("%Y-%m") if hasattr(p_fim, "strftime") else str(p_fim)
    with sqlite3.connect(self.db_path) as conn:
      cursor = conn.cursor()
      cursor.execute(
          """
                INSERT INTO faturas (unidade_id, mes_referencia, consumo_kwh, valor_total)
                VALUES (?, ?, ?, ?)
            """,
          (unidade_id, mes_ref, consumo_kwh, valor_total),
      )
      conn.commit()

  def carregar_dados(self) -> pd.DataFrame:
    """Carrega dados da tabela de medições industriais."""
    with sqlite3.connect(self.db_path) as conn:
      df = pd.read_sql_query("SELECT * FROM medicoes_industriais", conn)
      if not df.empty:
        df["data_hora"] = pd.to_datetime(df["data_hora"])
      return df

  def carregar_dados_reais_ou_simulados(self):
    """Gera série temporal de telemetria industrial para simulações."""
    datas = pd.date_range(start="2026-07-01", periods=720, freq="h")
    horas = datas.hour

    demanda = 150 + 80 * np.sin(2 * np.pi * horas / 24) + np.random.normal(
        0, 12, len(datas)
    )
    fator_pot = np.random.uniform(0.87, 0.97, len(datas))
    temp = 20 + 8 * np.sin(2 * np.pi * horas / 24) + np.random.normal(
        0, 2, len(datas)
    )

    df_simulado = pd.DataFrame({
        "data_hora": datas.strftime("%Y-%m-%d %H:%M:%S"),
        "demanda_kw": np.maximum(demanda, 10),
        "fator_potencia": fator_pot,
        "temperatura": temp,
    })

    with sqlite3.connect(self.db_path) as conn:
      df_simulado.to_sql(
          "medicoes_industriais", conn, if_exists="replace", index=False
      )
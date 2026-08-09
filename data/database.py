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
    """Inicializa as tabelas do banco com fallback automático em caso de incompatibilidade no servidor."""
    try:
      with sqlite3.connect(self.db_path) as conn:
        cursor = conn.cursor()

        # Ativa suporte a chaves estrangeiras no SQLite
        cursor.execute("PRAGMA foreign_keys = ON;")

        # 1. Tabela de Unidades Consumidoras
        cursor.execute("""
                    CREATE TABLE IF NOT EXISTS unidades (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        nome TEXT UNIQUE NOT NULL,
                        tipo TEXT NOT NULL
                    )
                """)

        # 2. Tabela de Faturas Mensais com chave estrangeira vinculada a unidades
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

        # Insere e busca a unidade 'casa 1' para obter a chave primaria ID
        cursor.execute("SELECT id FROM unidades WHERE nome = 'casa 1'")
        unidade = cursor.fetchone()

        if not unidade:
          cursor.execute(
              "INSERT INTO unidades (nome, tipo) VALUES ('casa 1',"
              " 'RESIDENCIAL')"
          )
          conn.commit()  # Salva a transação para gerar o ID na chave primária
          cursor.execute("SELECT id FROM unidades WHERE nome = 'casa 1'")
          unidade = cursor.fetchone()

        unid_id = unidade[0]

        # Insere dados de faturas sintéticas se a tabela estiver vazia
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

        conn.commit()  # Garante a gravação física no banco SQLite

    except sqlite3.OperationalError:
      # Se o arquivo .db do servidor for antigo e faltar colunas, apaga o arquivo corrompido e recria
      if os.path.exists(self.db_path):
        os.remove(self.db_path)
      self._init_db()

  def listar_unidades(self, tipo: str = "RESIDENCIAL") -> pd.DataFrame:
    """Busca unidades consumidoras cadastradas por tipo."""
    with sqlite3.connect(self.db_path) as conn:
      query = "SELECT * FROM unidades WHERE tipo = ?"
      return pd.read_sql_query(query, conn, params=(tipo,))

  def carregar_faturas(self, unidade: str) -> pd.DataFrame:
    """Carrega o histórico mensal de consumo e custos por unidade."""
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
    """Lê registros da tabela de medições industriais."""
    with sqlite3.connect(self.db_path) as conn:
      df = pd.read_sql_query("SELECT * FROM medicoes_industriais", conn)
      if not df.empty:
        df["data_hora"] = pd.to_datetime(df["data_hora"])
      return df

  def carregar_dados_reais_ou_simulados(self):
    """Gera dados de telemetria industrial de 720 horas para simulações."""
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
import sqlite3
import pandas as pd

class DatabaseManager:
    def __init__(self, db_path="data/sistema_eletrico.db"):
        self.db_path = db_path

    # ... [seus métodos existentes da DatabaseManager] ...

    def adicionar_fatura_residencial(self, mes_ano: str, consumo_kwh: float, bandeira: str, valor_total: float):
        """Insere uma nova fatura residencial no banco de dados SQLite."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Cria a tabela caso ainda não exista
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS faturas_residenciais (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mes_ano TEXT NOT NULL,
                consumo_kwh REAL NOT NULL,
                bandeira TEXT NOT NULL,
                valor_total REAL NOT NULL
            )
        """)
        
        # Insere o novo registro
        cursor.execute("""
            INSERT INTO faturas_residenciais (mes_ano, consumo_kwh, bandeira, valor_total)
            VALUES (?, ?, ?, ?)
        """, (mes_ano, consumo_kwh, bandeira, valor_total))
        
        conn.commit()
        conn.close()

    def carregar_faturas_residenciais() -> pd.DataFrame:
        """Carrega o histórico de faturas residenciais cadastrado."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS faturas_residenciais (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mes_ano TEXT NOT NULL,
                consumo_kwh REAL NOT NULL,
                bandeira TEXT NOT NULL,
                valor_total REAL NOT NULL
            )
        """)
        df = pd.read_sql_query("SELECT * FROM faturas_residenciais ORDER BY id DESC", conn)
        conn.close()
        return df

    def deletar_fatura_residencial(self, fatura_id: int):
        """Remove uma fatura específica pelo ID."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM faturas_residenciais WHERE id = ?", (fatura_id,))
        conn.commit()
        conn.close()

    def resetar_faturas_residenciais(self):
        """Reseta a tabela residencial limpando os registros inseridos e recarregando os padrões."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DROP TABLE IF EXISTS faturas_residenciais")
        conn.commit()
        conn.close()
        
        # Recarrega a tabela e insere faturas padrão para demonstração
        faturas_padrao = [
            ("2026-01", 320.0, "VERDE", 312.40),
            ("2026-02", 380.0, "AMARELA", 385.10),
            ("2026-03", 290.0, "VERDE", 283.15),
            ("2026-04", 310.0, "VERMELHA_P1", 328.90)
        ]
        for mes, cons, band, val in faturas_padrao:
            self.adicionar_fatura_residencial(mes, cons, band, val)
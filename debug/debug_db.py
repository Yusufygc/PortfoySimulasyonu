from config.settings_loader import load_settings
from src.infrastructure.db.mysql_connection import MySQLConnectionProvider

def main():
    cfg = load_settings()
    cp = MySQLConnectionProvider(cfg)

    with cp.get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT DATABASE()")
        db_name = cur.fetchone()[0]
        print("Connected to DB:", db_name)

if __name__ == "__main__":
    main()

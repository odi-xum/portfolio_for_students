"""
Загрузка SQL-файлов в БД приложения через sqlite3 CLI.
"""
import sys, os, subprocess
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def load_sql(filepath):
    from app import create_app
    from models import db
    app = create_app()
    with app.app_context():
        db.create_all()

    db_path = os.path.join(app.instance_path, 'database.db')
    if not os.path.exists(db_path):
        print(f'БД не найдена: {db_path}')
        return

    sql = Path(filepath).read_text(encoding='utf-8')
    r = subprocess.run(['sqlite3', db_path], input=sql,
                       capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        print(f'Ошибка: {r.stderr.strip()}')
    else:
        print(f'Загружен: {filepath}')


if __name__ == '__main__':
    p = sys.argv[1] if len(sys.argv) > 1 else 'sql/seed.sql'
    if not os.path.exists(p):
        print(f'Файл не найден: {p}')
        sys.exit(1)
    load_sql(p)

"""Temporary: test db.create_all() against PostgreSQL."""
import os
os.environ['DATABASE_URL'] = 'postgresql://diplom:diplom_pass@127.0.0.1:5432/diplom'

from app import create_app
from models import db

app = create_app()
with app.app_context():
    from sqlalchemy import inspect
    inspector = inspect(db.engine)
    tables = inspector.get_table_names()
    print(f'Tables before: {tables}')
    db.create_all()
    tables = inspector.get_table_names()
    print(f'Tables after: {tables}')
    print('Tables created successfully.')

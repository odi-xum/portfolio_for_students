import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, request
from flask_login import LoginManager, login_required, current_user
from models import db, User, AuditLog
from sqlalchemy import desc
from constants import UserRole

app = Flask(__name__)
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance', 'database.db')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + DB_PATH
app.config['SECRET_KEY'] = 'test'
app.config['WTF_CSRF_ENABLED'] = False
db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

with app.app_context():
    # Проверяем, что можно залогиниться как админ
    admin = User.query.filter_by(username='admin').first()
    if admin:
        print(f'Admin found: {admin.username} role={admin.role}')
    else:
        print('Admin user not found, creating test...')
    
    # Создаём тестовый контекст запроса
    with app.test_request_context('/admin/audit'):
        # Логиним админа
        from flask_login import login_user
        if admin:
            login_user(admin)
        
        # Эмулируем маршрут /admin/audit
        page = 1
        per_page = 50
        action_filter = ''
        user_filter = ''
        
        q = AuditLog.query
        if action_filter:
            q = q.filter(AuditLog.action == action_filter)
        if user_filter:
            q = q.filter(AuditLog.username.ilike(f'%{user_filter}%'))
        q = q.order_by(desc(AuditLog.created_at))
        
        total = q.count()
        offset = (page - 1) * per_page
        logs = q.offset(offset).limit(per_page).all()
        
        print(f'Total: {total}, Logs count: {len(logs)}')
        
        try:
            actions = [r[0] for r in db.session.query(AuditLog.action).distinct().order_by(AuditLog.action).all()]
            print(f'Actions: {actions}')
        except Exception as e:
            print(f'ERROR in actions query: {type(e).__name__}: {e}')
        
        # Пробуем render_template
        try:
            from flask import render_template_string
            simple_template = '''
            <html><body>
            Total: {{ total }}
            {% for log in logs %}
                <p>{{ log.id }} {{ log.username }} {{ log.action }}</p>
            {% else %}
                <p>No entries</p>
            {% endfor %}
            </body></html>
            '''
            result = render_template_string(simple_template, logs=logs, page=page, per_page=per_page,
                                           total=total, actions=actions,
                                           action_filter=action_filter, user_filter=user_filter)
            print('Template rendered OK')
        except Exception as e:
            print(f'ERROR in template: {type(e).__name__}: {e}')

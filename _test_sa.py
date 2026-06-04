import os, sys; os.chdir('/home/odi/Documents/projects/diplom'); sys.path.insert(0, '.')
from flask import Flask, render_template
from flask_login import LoginManager, login_user
from models import db, User
from routes import register_routes
app = Flask(__name__)
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance', 'database.db')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + DB_PATH
app.config['SECRET_KEY'] = 'test'
db.init_app(app)
lm = LoginManager(); lm.init_app(app)
@lm.user_loader
def lu(uid): return db.session.get(User, int(uid))
register_routes(app)
with app.app_context():
    s = User.query.filter_by(username='student1').first()
    print('Student:', s.username, s.role)
    with app.test_request_context('/student/create', method='GET'):
        login_user(s)
        h = render_template('student_create.html')
        print('OK:', len(h), 'chars')

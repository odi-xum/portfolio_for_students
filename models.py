from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

# Инициализация объекта базы данных (связывается с приложением в app.py)
db = SQLAlchemy()

class User(db.Model, UserMixin):
    """
    Модель пользователя системы. 
    Поддерживает 5 ролей: admin, student, teacher, curator, commission.
    """
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    
    # Название группы (необходимо для связи студентов и их кураторов, например 'ИСП-41')
    group_name = db.Column(db.String(20), nullable=True)
    
    # Обратные связи для удобной выборки через ORM
    events = db.relationship('Event', backref='student', lazy=True, cascade="all, delete-orphan")
    notifications = db.relationship('Notification', backref='user', lazy=True, cascade="all, delete-orphan")
    scholarship_requests = db.relationship('ScholarshipRequest', backref='student', lazy=True, cascade="all, delete-orphan")


class Event(db.Model):
    """
    Модель поста (мероприятия) на стене студента.
    Содержит статусы проверки, оценки куратора и логику арбитража комиссии.
    """
    __tablename__ = 'events'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    
    # Допустимые статусы записи: 
    # 'pending'    - отправлено студентом, ждет куратора
    # 'approved'   - одобрено (куратором или комиссией в ходе пересмотра)
    # 'rejected'   - окончательно отклонено комиссией после арбитража
    # 'disputed'   - отклонено куратором и передано на арбитраж в комиссию
    status = db.Column(db.String(20), default='pending', nullable=False)
    
    # Поле сохранения промежуточного статуса для реализации отката решений комиссии
    previous_status = db.Column(db.String(20), nullable=True)
    
    # Оценочные метрики и фидбек сторон
    score = db.Column(db.Integer, nullable=True)  # Оценка от 1 до 5
    curator_comment = db.Column(db.Text, nullable=True)
    commission_comment = db.Column(db.Text, nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    # Фиксация времени вынесения вердикта комиссией (необходимо для фильтрации архива)
    commission_reviewed_at = db.Column(db.DateTime, nullable=True)
    
    # Связь с таблицей файлов (обращение через event.files в шаблонах)
    files = db.relationship('EventFile', backref='event', lazy=True, cascade="all, delete-orphan")


class EventFile(db.Model):
    """
    Модель хранения метаданных о загруженных файлах-доказательствах.
    Физические файлы распределяются по защищенным папкам на сервере.
    """
    __tablename__ = 'event_files'
    
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=False)
    
    # Абсолютный или относительный путь к файлу на диске сервера
    file_path = db.Column(db.String(300), nullable=False)
    
    # Расширение файла для фронтенд-контроля отрисовки ('png', 'jpg', 'jpeg', 'pdf')
    file_type = db.Column(db.String(10), nullable=False)


class Notification(db.Model):
    """
    Система внутренних уведомлений для координации действий между ролями.
    """
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)  # Адресат
    
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class ScholarshipRequest(db.Model):
    """
    Модель запросов на повышенную государственную академическую стипендию.
    Инициируется студентом при достижении лимитов (>=20 одобренных постов, балл >=4.5).
    """
    __tablename__ = 'scholarship_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Этапы согласования и архивные статусы:
    # 'under_curator_review'    - проверяется куратором (сверка статистики)
    # 'under_commission_review' - передано комиссии на финальное утверждение
    # 'approved'                - стипендия успешно назначена комиссией
    # 'rejected'                - в назначении отказано комиссией
    status = db.Column(db.String(30), default='under_curator_review', nullable=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    # Фиксация времени вынесения решения по стипендии для истории действий
    commission_reviewed_at = db.Column(db.DateTime, nullable=True)

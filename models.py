from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

# Инициализация объекта базы данных (связывается с приложением в app.py)
db = SQLAlchemy()

class User(db.Model, UserMixin):
    """
    Модель пользователя системы. 
    Поддерживает 4 роли: admin, student, curator, commission.
    """
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    
    # ФИО
    last_name = db.Column(db.String(50), nullable=True)     # Фамилия
    first_name = db.Column(db.String(50), nullable=True)    # Имя
    patronymic = db.Column(db.String(50), nullable=True)    # Отчество
    
    # Название группы (необходимо для связи студентов и их кураторов, например 'ИСП-41')
    group_name = db.Column(db.String(20), nullable=True)
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id'), nullable=True)
    
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
    link = db.Column(db.String(300), nullable=True)
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class Department(db.Model):
    """
    Модель отделения колледжа.
    К каждому отделению привязаны только определенные специальности.
    """
    __tablename__ = 'departments'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)   # "ИТ-отделение"
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    specialties = db.relationship('Specialty', backref='department_rel', lazy=True)


class Specialty(db.Model):
    """
    Модель специальности колледжа.
    Каждая специальность имеет уникальное название, код и сокращение из первых букв.
    Пример: Информационные системы и программирование → ИСП (код 09.02.07)
    Привязана к определённому отделению.
    """
    __tablename__ = 'specialties'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), unique=True, nullable=False)   # "Информационные системы и программирование"
    code = db.Column(db.String(20), nullable=False)                  # "09.02.07"
    abbreviation = db.Column(db.String(10), nullable=False)          # "ИСП"
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    groups = db.relationship('Group', backref='specialty_rel', lazy=True)


class Group(db.Model):
    """
    Модель учебной группы колледжа.
    Название генерируется автоматически: {сокращение}-{тип}-{год}
    Пример: ИСП-Б-2022, ПКС-К-2023
    """
    __tablename__ = 'groups'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20), unique=True, nullable=False)  # ИСП-Б-2022 (авто-генерация)
    group_number = db.Column(db.String(10), nullable=True)        # 232, 232а (внутренний номер группы)
    specialty_id = db.Column(db.Integer, db.ForeignKey('specialties.id'), nullable=True)
    specialty_name = db.Column(db.String(200), nullable=False)     # Информационные системы и программирование
    specialty_code = db.Column(db.String(20), nullable=False)      # 09.02.07
    budget_type = db.Column(db.String(10), nullable=True)          # 'бюджет' → Б, 'коммерция' → К
    start_year = db.Column(db.Integer, nullable=True)              # 2022
    course = db.Column(db.Integer, nullable=False)                 # 1-4 курс
    department = db.Column(db.String(100), nullable=True)          # ИТ-отделение
    form_of_study = db.Column(db.String(50), default='очная')     # очная/заочная
    start_date = db.Column(db.Date, nullable=True)
    end_date = db.Column(db.Date, nullable=True)
    curator_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    curator = db.relationship('User', foreign_keys=[curator_id], lazy=True, post_update=True)


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

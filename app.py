import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from sqlalchemy.orm import joinedload
from models import db, User, Event, EventFile, Notification, ScholarshipRequest

app = Flask(__name__)
app.config['SECRET_KEY'] = 'gruvbox-material-secure-shadow-key-1984'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

BASE_UPLOAD_FOLDER = os.path.abspath('./diplom')
app.config['UPLOAD_FOLDER'] = BASE_UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}

db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/diplom/<path:filename>')
@login_required
def serve_diplom_files(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

def init_test_db():
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
        
    db.create_all()
    
    # Создание пользователей, если их нет
    if not User.query.filter_by(username='admin').first():
        roles_config = [
            {'username': 'admin', 'role': 'admin', 'group': None},
            {'username': 'teacher', 'role': 'teacher', 'group': None},
            {'username': 'student', 'role': 'student', 'group': 'ИСП-41'},
            {'username': 'curator', 'role': 'curator', 'group': 'ИСП-41'},
            {'username': 'commission', 'role': 'commission', 'group': None},
            {'username': 'ivanov', 'role': 'student', 'group': 'ИСП-41'} # Дополнительный студент для массовки
        ]
        
        users_map = {}
        for user_data in roles_config:
            u = User(
                username=user_data['username'],
                password_hash=generate_password_hash('111'),
                role=user_data['role'],
                group_name=user_data['group']
            )
            db.session.add(u)
            users_map[user_data['username']] = u
        db.session.commit()
        
        student = users_map['student']
        ivanov = users_map['ivanov']
        
        # ------------------------------------------------------------------
        # ГЕНЕРАЦИЯ 20 ОДОБРЕННЫХ ПОСТОВ ДЛЯ СТУДЕНТА 'student' (Для стипендии)
        # ------------------------------------------------------------------
        for i in range(1, 21):
            verified_event = Event(
                student_id=student.id,
                title=f"Олимпиада/Мероприятие №{i}",
                description=f"Автоматически сгенерированное описание подтвержденного достижения №{i} для тестирования лимитов стипендии.",
                status='approved',
                score=5, # Фиксируем 5 баллов для прохождения порога в 4.5
                curator_comment="Документы проверены, балл начислен.",
                created_at=datetime.utcnow()
            )
            db.session.add(verified_event)
            db.session.commit() # Фиксируем ID
            
            # Добавляем фейковый файл-заглушку в базу для консистентности
            db.session.add(EventFile(
                event_id=verified_event.id,
                file_path=f"{app.config['UPLOAD_FOLDER']}/students/student/mock_cert_{i}.pdf",
                file_type="pdf"
            ))

        # ------------------------------------------------------------------
        # ДОПОЛНИТЕЛЬНЫЕ ТЕСТОВЫЕ ДАННЫЕ ДЛЯ ОСТАЛЬНЫХ СЦЕНАРИЕВ (по ~5 штук)
        # ------------------------------------------------------------------
        
        # 1. Новые посты на проверку куратору (статус 'pending') от второго студента
        for i in range(1, 6):
            pending_event = Event(
                student_id=ivanov.id,
                title=f"Новая заявка на проверку №{i}",
                description=f"Студент Иванов отправил этот пост на верификацию. Куратор должен его обработать.",
                status='pending',
                created_at=datetime.utcnow()
            )
            db.session.add(pending_event)
            db.session.commit()
            db.session.add(EventFile(
                event_id=pending_event.id,
                file_path=f"{app.config['UPLOAD_FOLDER']}/students/ivanov/pending_proof_{i}.jpg",
                file_type="jpg"
            ))

        # 2. Спорные посты в процессе арбитража комиссией (статус 'disputed')
        for i in range(1, 6):
            disputed_event = Event(
                student_id=ivanov.id,
                title=f"Спорная публикация №{i}",
                description=f"Описание достижения, которое вызвало сомнения у куратора.",
                status='disputed',
                curator_comment=f"Нечитаемый скан документа или некорректная дата в заявке №{i}.",
                created_at=datetime.utcnow()
            )
            db.session.add(disputed_event)
            db.session.commit()
            db.session.add(EventFile(
                event_id=disputed_event.id,
                file_path=f"{app.config['UPLOAD_FOLDER']}/students/ivanov/disputed_proof_{i}.png",
                file_type="png"
            ))

        # 3. Архив уже вынесенных решений комиссии по постам (статус 'rejected'/'approved' с commission_reviewed_at)
        for i in range(1, 4):
            resolved_event = Event(
                student_id=student.id,
                title=f"Архивный арбитраж №{i}",
                description="Старая запись, по которой комиссия уже вынесла окончательный вердикт.",
                status='rejected',
                curator_comment="Отклонено куратором за несоответствие профилю.",
                commission_comment=f"Комиссия подтверждает решение куратора. Протокол №{i}.",
                created_at=datetime.utcnow(),
                commission_reviewed_at=datetime.utcnow()
            )
            db.session.add(resolved_event)

        # 4. Активные заявки на стипендию для панели комиссии
        # Одна заявка от нашего готового студента (ее можно сразу одобрить/отклонить)
        db.session.add(ScholarshipRequest(
            student_id=student.id,
            status='under_curator_review',
            created_at=datetime.utcnow()
        ))
        
        # Пачка архивных (уже закрытых) заявок на стипендию
        for i in range(1, 4):
            db.session.add(ScholarshipRequest(
                student_id=ivanov.id,
                status='approved' if i % 2 == 0 else 'rejected',
                created_at=datetime.utcnow(),
                commission_reviewed_at=datetime.utcnow()
            ))

        db.session.commit()

@app.route('/', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for(f'{current_user.role}_dashboard'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for(f'{user.role}_dashboard'))
        
        flash('Неверный логин или пароль. Попробуйте еще раз.', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/student/dashboard', methods=['GET', 'POST'])
@login_required
def student_dashboard():
    if current_user.role != 'student':
        return "Доступ ограничен", 403
        
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        files = request.files.getlist('files')
        
        valid_files = [f for f in files if f and allowed_file(f.filename)]
        
        if not title:
            flash('Пожалуйста, заполните название мероприятия.', 'warning')
            return redirect(url_for('student_dashboard'))
            
        if not valid_files:
            flash('Ошибка: Не хватает доказательств для присутствия на мероприятии! Прикрепите JPG/PNG или PDF.', 'danger')
            return redirect(url_for('student_dashboard'))
            
        new_event = Event(
            student_id=current_user.id, 
            title=title, 
            description=description, 
            status='pending'
        )
        db.session.add(new_event)
        db.session.commit()
        
        safe_username = secure_filename(current_user.username)
        safe_title = secure_filename(title)
        event_dir_name = f"{new_event.id}_{safe_title}"
        
        student_folder = os.path.join(app.config['UPLOAD_FOLDER'], 'students', safe_username, event_dir_name)
        os.makedirs(student_folder, exist_ok=True)
        
        for file in valid_files:
            filename = secure_filename(file.filename)
            file_path = os.path.join(student_folder, filename)
            file.save(file_path)
            
            ext = filename.rsplit('.', 1)[1].lower()
            ev_file = EventFile(event_id=new_event.id, file_path=file_path, file_type=ext)
            db.session.add(ev_file)
            
        curator = User.query.filter_by(role='curator', group_name=current_user.group_name).first()
        if curator:
            notification = Notification(
                user_id=curator.id,
                message=f"Студент {current_user.username} опубликовал новое мероприятие: '{title}'. Требуется проверка."
            )
            db.session.add(notification)
            
        db.session.commit()
        flash('Мероприятие успешно опубликовано на вашей стене и отправлено куратору.', 'success')
        return redirect(url_for('student_dashboard'))
        
    events = Event.query.filter_by(student_id=current_user.id).order_by(Event.created_at.desc()).all()
    return render_template('student.html', events=events)

# ==========================================================================
# ПАНЕЛЬ КУРАТОРА (МОДЕРНИЗИРОВАННАЯ, С ПОДДЕРЖКОЙ АРХИВА РЕШЕНИЙ)
# ==========================================================================
@app.route('/curator/dashboard', methods=['GET'])
@login_required
def curator_dashboard():
    if current_user.role != 'curator':
        return "Доступ ограничен", 403
    
    # Находим всех студентов, закрепленных за группой куратора
    group_students = User.query.filter_by(group_name=current_user.group_name, role='student').all()
    student_ids = [student.id for student in group_students]
    
    # Актуальные задачи (только новые посты)
    pending_events = Event.query.options(joinedload(Event.student)).filter(
        Event.student_id.in_(student_ids), 
        Event.status == 'pending'
    ).order_by(Event.created_at.asc()).all()
    
    # Архив решений куратора (все посты группы, которые уже были обработаны)
    resolved_events = Event.query.options(joinedload(Event.student)).filter(
        Event.student_id.in_(student_ids),
        Event.status.in_(['approved', 'disputed', 'rejected'])
    ).order_by(Event.created_at.desc()).all()
    
    return render_template('curator.html', events=pending_events, resolved_events=resolved_events)

@app.route('/curator/evaluate/<int:event_id>', methods=['POST'])
@login_required
def curator_evaluate(event_id):
    if current_user.role != 'curator':
        return "Доступ ограничен", 403
    
    event = Event.query.get_or_404(event_id)
    action = request.form.get('action')
    comment = request.form.get('comment')
    
    if action == 'approve':
        score = int(request.form.get('score', 5))
        event.score = score
        event.curator_comment = comment
        event.status = 'approved'
        flash(f"Мероприятие ID {event.id} успешно одобрено с оценкой {score}.", 'success')
        
    elif action == 'reject':
        if not comment or comment.strip() == "":
            flash("Ошибка: При отклонении поста комментарий с указанием причины обязателен!", "danger")
            return redirect(url_for('curator_dashboard'))
            
        event.curator_comment = comment
        event.status = 'disputed'
        
        commission_members = User.query.filter_by(role='commission').all()
        for member in commission_members:
            db.session.add(Notification(
                user_id=member.id,
                message=f"Куратор отклонил пост студента (ID мероприятия: {event.id}). Требуется арбитражная оценка комиссии."
            ))
        flash(f"Мероприятие ID {event.id} отклонено и перенаправлено в комиссию.", 'warning')
            
    db.session.commit()
    return redirect(url_for('curator_dashboard'))

@app.route('/student/request_scholarship', methods=['POST'])
@login_required
def request_scholarship():
    if current_user.role != 'student':
        return "Доступ ограничен", 403
    
    approved_events = Event.query.filter_by(student_id=current_user.id, status='approved').all()
    
    if len(approved_events) < 20:
        flash(f'Отказано: Недостаточно верифицированных достижений. У вас {len(approved_events)} из 20 необходимых.', 'danger')
        return redirect(url_for('student_dashboard'))
        
    avg_score = sum([e.score for e in approved_events]) / len(approved_events)
    if avg_score < 4.5:
        flash(f'Отказано: Недостаточный средний балл портфолио. Ваш показатель: {avg_score:.2f} (требуется не менее 4.50).', 'danger')
        return redirect(url_for('student_dashboard'))
        
    new_request = ScholarshipRequest(student_id=current_user.id, status='under_curator_review')
    db.session.add(new_request)
    
    curator = User.query.filter_by(role='curator', group_name=current_user.group_name).first()
    if curator:
        db.session.add(Notification(
            user_id=curator.id, 
            message=f"Студент {current_user.username} выполнил нормативы портфолио и подал заявку на повышенную стипендию."
        ))
        
    db.session.commit()
    flash('Заявка на повышенную стипендию сформирована и отправлена куратору группы для сверки статистики.', 'success')
    return redirect(url_for('student_dashboard'))

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if current_user.role != 'admin': 
        return "Доступ ограничен", 403
    users = User.query.all()
    return render_template('admin.html', users=users)

@app.route('/admin/add_user', methods=['POST'])
@login_required
def admin_add_user():
    if current_user.role != 'admin': 
        return "Доступ ограничен", 403
    username = request.form.get('username')
    password = request.form.get('password')
    role = request.form.get('role')
    group_name = request.form.get('group_name')
    
    if User.query.filter_by(username=username).first():
        flash('Пользователь с таким логином уже существует!', 'danger')
        return redirect(url_for('admin_dashboard'))
        
    new_user = User(
        username=username,
        password_hash=generate_password_hash(password),
        role=role,
        group_name=group_name if group_name else None
    )
    db.session.add(new_user)
    db.session.commit()
    flash(f'Пользователь {username} ({role}) успешно добавлен.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_user/<int:user_id>', methods=['POST'])
@login_required
def admin_delete_user(user_id):
    if current_user.role != 'admin': 
        return "Доступ ограничен", 403
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('Вы не можете удалить самого себя!', 'danger')
        return redirect(url_for('admin_dashboard'))
    db.session.delete(user)
    db.session.commit()
    flash('Пользователь успешно удален из системы.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/commission/dashboard')
@login_required
def commission_dashboard():
    if current_user.role != 'commission': 
        return "Доступ ограничен", 403
    
    disputed_events = Event.query.options(joinedload(Event.student)).filter_by(status='disputed').order_by(Event.created_at.asc()).all()
    
    scholarship_requests = ScholarshipRequest.query.options(joinedload(ScholarshipRequest.student)).filter(
        ScholarshipRequest.status.in_(['under_commission_review', 'under_curator_review'])
    ).order_by(ScholarshipRequest.created_at.asc()).all()
    
    resolved_events = Event.query.options(joinedload(Event.student)).filter(
        Event.status.in_(['approved', 'rejected']),
        Event.commission_reviewed_at.isnot(None)
    ).order_by(Event.commission_reviewed_at.desc()).all()
    
    resolved_scholarships = ScholarshipRequest.query.options(joinedload(ScholarshipRequest.student)).filter(
        ScholarshipRequest.status.in_(['approved', 'rejected']),
        ScholarshipRequest.commission_reviewed_at.isnot(None)
    ).order_by(ScholarshipRequest.commission_reviewed_at.desc()).all()
    
    return render_template(
        'commission.html', 
        disputed_events=disputed_events, 
        scholarship_requests=scholarship_requests,
        resolved_events=resolved_events,
        resolved_scholarships=resolved_scholarships
    )

@app.route('/commission/resolve_dispute/<int:event_id>', methods=['POST'])
@login_required
def resolve_dispute(event_id):
    if current_user.role != 'commission': 
        return "Доступ ограничен", 403
    event = Event.query.get_or_404(event_id)
    decision = request.form.get('decision')
    comment = request.form.get('commission_comment')
    
    event.previous_status = event.status
    event.commission_comment = comment
    event.commission_reviewed_at = datetime.utcnow()
    
    if decision == 'confirm_reject':
        event.status = 'rejected'
        flash(f'Пост ID {event.id} окончательно отклонен комиссией.', 'danger')
    elif decision == 'overrule_approve':
        event.status = 'approved'
        event.score = 5 if not event.score else event.score
        flash(f'Решение куратора отменено. Пост ID {event.id} успешно одобрен комиссией.', 'success')
        
    db.session.commit()
    return redirect(url_for('commission_dashboard'))

@app.route('/commission/scholarship_decision/<int:req_id>', methods=['POST'])
@login_required
def scholarship_decision(req_id):
    if current_user.role != 'commission': 
        return "Доступ ограничен", 403
    req = ScholarshipRequest.query.get_or_404(req_id)
    decision = request.form.get('decision')
    
    req.commission_reviewed_at = datetime.utcnow()
    if decision == 'approve':
        req.status = 'approved'
        flash('Повышенная стипендия успешно назначена.', 'success')
    elif decision == 'reject':
        req.status = 'rejected'
        flash('В назначении стипендии отказано.', 'danger')
        
    db.session.commit()
    return redirect(url_for('commission_dashboard'))

@app.route('/commission/reconsider_event/<int:event_id>', methods=['POST'])
@login_required
def reconsider_event(event_id):
    if current_user.role != 'commission': 
        return "Доступ ограничен", 403
    event = Event.query.get_or_404(event_id)
    
    event.status = 'disputed'
    event.commission_reviewed_at = None
    event.commission_comment = f"[Отправлено на пересмотр] {event.commission_comment or ''}"
    
    db.session.commit()
    flash(f'Решение по посту ID {event.id} отменено. Запись возвращена в активный арбитраж.', 'warning')
    return redirect(url_for('commission_dashboard'))

@app.route('/commission/reconsider_scholarship/<int:req_id>', methods=['POST'])
@login_required
def reconsider_scholarship(req_id):
    if current_user.role != 'commission': 
        return "Доступ ограничен", 403
    req = ScholarshipRequest.query.get_or_404(req_id)
    
    req.status = 'under_commission_review'
    req.commission_reviewed_at = None
    
    db.session.commit()
    flash(f'Решение по стипендии ID {req.id} отменено. Заявка возвращена на этап рассмотрения.', 'warning')
    return redirect(url_for('commission_dashboard'))

@app.route('/teacher/dashboard')
@login_required
def teacher_dashboard():
    return "Панель преподавателя находится в стадии наполнения логикой."

if __name__ == '__main__':
    with app.app_context():
        init_test_db()
    app.run(debug=True)

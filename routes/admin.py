"""
Административные маршруты: пользователи, группы, специальности, импорт.
"""
import json
import os

from flask import render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from sqlalchemy.orm import joinedload

from constants import UserRole
from models import db, User, Group, Specialty, Department, Event, ScholarshipRequest
from helpers import generate_abbreviation, build_group_name, parse_date, now_utc, log_audit, BASE_UPLOAD_FOLDER


def _admin_only():
    abort(403)


def register_admin_routes(app):

    @app.route('/admin/dashboard')
    @login_required
    def admin_dashboard():
        if current_user.role != UserRole.ADMIN:
            _admin_only()

        from datetime import timedelta
        now = now_utc()
        month_ago = now - timedelta(days=30)

        stats = {
            'users_count': User.query.count(),
            'students_count': User.query.filter_by(role='student').count(),
            'curators_count': User.query.filter_by(role='curator').count(),
            'groups_count': Group.query.count(),
            'events_total': Event.query.count(),
            'events_pending': Event.query.filter_by(status='pending').count(),
            'events_approved': Event.query.filter_by(status='approved').count(),
            'events_disputed': Event.query.filter_by(status='disputed').count(),
            'events_rejected': Event.query.filter_by(status='rejected').count(),
            'events_month': Event.query.filter(Event.created_at >= month_ago).count(),
            'scholarship_requests': ScholarshipRequest.query.count(),
            'active_scholarships': ScholarshipRequest.query.filter(
                ScholarshipRequest.status.in_(['under_curator_review', 'under_commission_review'])
            ).count(),
            'dept_count': Department.query.count(),
            'specialty_count': Specialty.query.count(),
        }

        # По отделениям
        dept_stats = []
        for d in Department.query.all():
            spec_ids = [s.id for s in d.specialties]
            grps = Group.query.filter(Group.specialty_id.in_(spec_ids)).all()
            grp_ids = [g.id for g in grps]
            stu_count = User.query.filter(
                User.role == UserRole.STUDENT, User.group_id.in_(grp_ids)
            ).count() if grp_ids else 0
            dept_stats.append({'name': d.name, 'groups': len(grps), 'students': stu_count})

        return render_template('admin.html', stats=stats, dept_stats=dept_stats)

    # ------------------------------------------------------------------
    #  ПОЛЬЗОВАТЕЛИ
    # ------------------------------------------------------------------
    @app.route('/admin/users')
    @login_required
    def admin_users():
        if current_user.role != UserRole.ADMIN:
            _admin_only()
        users = User.query.all()
        groups = Group.query.order_by(Group.name).all()
        return render_template('admin_users.html', users=users, groups=groups)

    @app.route('/admin/add_user', methods=['POST'])
    @login_required
    def admin_add_user():
        if current_user.role != UserRole.ADMIN:
            _admin_only()
        username = request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role')
        group_id = request.form.get('group_id')

        if User.query.filter_by(username=username).first():
            flash('Пользователь с таким логином уже существует!', 'danger')
            return redirect(url_for('admin_users'))

        group_name = None
        if group_id:
            grp = db.session.get(Group, int(group_id))
            group_name = grp.name if grp else None

        new_user = User(
            username=username,
            password_hash=generate_password_hash(password),
            role=role,
            last_name=request.form.get('last_name'),
            first_name=request.form.get('first_name'),
            patronymic=request.form.get('patronymic'),
            group_name=group_name,
            group_id=int(group_id) if group_id else None
        )
        db.session.add(new_user)
        db.session.commit()
        log_audit(current_user, 'user_create', f'Создан пользователь {username} ({role})')
        flash(f'Пользователь {username} ({role}) успешно добавлен.', 'success')
        return redirect(url_for('admin_users'))

    @app.route('/admin/delete_user/<int:user_id>', methods=['POST'])
    @login_required
    def admin_delete_user(user_id):
        if current_user.role != UserRole.ADMIN:
            _admin_only()
        user = db.get_or_404(User, user_id)
        if user.id == current_user.id:
            flash('Вы не можете удалить самого себя!', 'danger')
            return redirect(url_for('admin_dashboard'))
        log_audit(current_user, 'user_delete', f'Удалён пользователь #{user.id} {user.username} ({user.role})')
        db.session.delete(user)
        db.session.commit()
        flash('Пользователь успешно удален из системы.', 'success')
        return redirect(url_for('admin_users'))

    # ------------------------------------------------------------------
    #  ГРУППЫ
    # ------------------------------------------------------------------
    @app.route('/admin/groups')
    @login_required
    def admin_groups():
        if current_user.role != UserRole.ADMIN:
            _admin_only()
        groups = Group.query.options(
            joinedload(Group.curator), joinedload(Group.specialty_rel)
        ).order_by(Group.name).all()
        curators = User.query.filter_by(role='curator').all()
        departments = Department.query.options(
            joinedload(Department.specialties)
        ).order_by(Department.name).all()
        specialties = Specialty.query.options(
            joinedload(Specialty.department_rel)
        ).order_by(Specialty.name).all()
        return render_template('admin_groups.html',
                               groups=groups, curators=curators,
                               departments=departments, specialties=specialties)

    @app.route('/admin/add_group', methods=['POST'])
    @login_required
    def admin_add_group():
        if current_user.role != UserRole.ADMIN:
            _admin_only()

        specialty_id = request.form.get('specialty_id')
        group_number = request.form.get('group_number')
        budget_type = request.form.get('budget_type')
        start_year_str = request.form.get('start_year')
        course = request.form.get('course')
        department = request.form.get('department')
        form_of_study = request.form.get('form_of_study', 'очная')
        curator_id = request.form.get('curator_id')
        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')

        if not specialty_id or not course:
            flash('Выберите специальность и укажите курс.', 'danger')
            return redirect(url_for('admin_groups'))

        specialty = db.get_or_404(Specialty, int(specialty_id))
        name = build_group_name(specialty.abbreviation, budget_type, start_year_str)

        if Group.query.filter_by(name=name).first():
            flash(f'Группа {name} уже существует!', 'danger')
            return redirect(url_for('admin_groups'))

        new_group = Group(
            name=name,
            group_number=group_number or None,
            specialty_id=specialty.id,
            specialty_name=specialty.name,
            specialty_code=specialty.code,
            budget_type=budget_type,
            start_year=int(start_year_str) if start_year_str else None,
            course=int(course),
            department=department,
            form_of_study=form_of_study,
            start_date=parse_date(start_date_str),
            end_date=parse_date(end_date_str),
            curator_id=int(curator_id) if curator_id else None
        )
        db.session.add(new_group)
        db.session.commit()
        log_audit(current_user, 'group_create', f'Создана группа {name}')
        flash(f'Группа {name} успешно создана.', 'success')
        return redirect(url_for('admin_groups'))

    @app.route('/admin/edit_group/<int:group_id>', methods=['GET', 'POST'])
    @login_required
    def admin_edit_group(group_id):
        if current_user.role != UserRole.ADMIN:
            _admin_only()

        group = db.session.query(Group).options(
            joinedload(Group.curator), joinedload(Group.specialty_rel)
        ).filter(Group.id == group_id).one_or_404()
        curators = User.query.filter_by(role='curator').all()
        specialties = Specialty.query.options(
            joinedload(Specialty.department_rel)
        ).order_by(Specialty.name).all()

        if request.method == 'POST':
            group.group_number = request.form.get('group_number') or None
            group.course = int(request.form.get('course', group.course))
            group.department = request.form.get('department') or group.department
            group.form_of_study = request.form.get('form_of_study', 'очная')
            curator_id = request.form.get('curator_id')
            group.curator_id = int(curator_id) if curator_id else None
            group.start_date = parse_date(request.form.get('start_date'))
            group.end_date = parse_date(request.form.get('end_date'))
            db.session.commit()
            log_audit(current_user, 'group_edit', f'Обновлена группа {group.name}')
            flash(f'Группа {group.name} обновлена.', 'success')
            return redirect(url_for('admin_groups'))

        return render_template('admin_edit_group.html',
                               group=group, curators=curators, specialties=specialties)

    @app.route('/admin/delete_group/<int:group_id>', methods=['POST'])
    @login_required
    def admin_delete_group(group_id):
        if current_user.role != UserRole.ADMIN:
            _admin_only()
        group = db.get_or_404(Group, group_id)
        students_in_group = User.query.filter_by(group_id=group_id).count()
        if students_in_group > 0:
            flash(f'Нельзя удалить группу: к ней привязано {students_in_group} студентов.', 'danger')
            return redirect(url_for('admin_groups'))
        log_audit(current_user, 'group_delete', f'Удалена группа {group.name}')
        db.session.delete(group)
        db.session.commit()
        flash(f'Группа {group.name} удалена.', 'success')
        return redirect(url_for('admin_groups'))

    # ------------------------------------------------------------------
    #  СПЕЦИАЛЬНОСТИ
    # ------------------------------------------------------------------
    @app.route('/admin/add_specialty', methods=['POST'])
    @login_required
    def admin_add_specialty():
        if current_user.role != UserRole.ADMIN:
            _admin_only()
        name = request.form.get('specialty_name')
        code = request.form.get('specialty_code')
        department_id = request.form.get('department_id')

        if not name or not code:
            flash('Заполните название и код специальности.', 'danger')
            return redirect(url_for('admin_groups'))
        if Specialty.query.filter_by(name=name).first():
            flash('Специальность с таким названием уже существует!', 'danger')
            return redirect(url_for('admin_groups'))

        abbreviation = generate_abbreviation(name)
        new_specialty = Specialty(
            name=name, code=code, abbreviation=abbreviation,
            department_id=int(department_id) if department_id else None
        )
        db.session.add(new_specialty)
        db.session.commit()

        dept = db.session.get(Department, int(department_id)) if department_id else None
        dept_name = dept.name if dept else '—'
        flash(f'Специальность «{name}» ({abbreviation}) добавлена в {dept_name}.', 'success')
        return redirect(url_for('admin_groups'))

    @app.route('/admin/delete_specialty/<int:specialty_id>', methods=['POST'])
    @login_required
    def admin_delete_specialty(specialty_id):
        if current_user.role != UserRole.ADMIN:
            _admin_only()
        specialty = db.get_or_404(Specialty, specialty_id)
        groups_count = Group.query.filter_by(specialty_id=specialty_id).count()
        if groups_count > 0:
            flash(f'Нельзя удалить специальность: к ней привязано {groups_count} групп.', 'danger')
            return redirect(url_for('admin_groups'))
        db.session.delete(specialty)
        db.session.commit()
        flash(f'Специальность «{specialty.name}» удалена.', 'success')
        return redirect(url_for('admin_groups'))

    # ------------------------------------------------------------------
    #  ИМПОРТ СТУДЕНТОВ ИЗ JSON
    # ------------------------------------------------------------------
    @app.route('/admin/import_students', methods=['POST'])
    @login_required
    def admin_import_students():
        if current_user.role != UserRole.ADMIN:
            _admin_only()

        file = request.files.get('json_file')
        if not file:
            flash('Файл не выбран.', 'danger')
            return redirect(url_for('admin_users'))

        try:
            data = json.load(file)
        except Exception:
            flash('Ошибка чтения JSON-файла.', 'danger')
            return redirect(url_for('admin_users'))

        if not isinstance(data, list):
            data = [data]

        imported = 0
        skipped = 0
        for item in data:
            username = item.get('username')
            password = item.get('password', '111')
            role = item.get('role', 'student')
            group_name = item.get('group')

            if not username:
                skipped += 1
                continue
            if User.query.filter_by(username=username).first():
                skipped += 1
                continue

            group_id = None
            if group_name:
                grp = Group.query.filter_by(name=group_name).first()
                if grp:
                    group_id = grp.id

            new_user = User(
                username=username,
                password_hash=generate_password_hash(password),
                role=role,
                last_name=item.get('last_name'),
                first_name=item.get('first_name'),
                patronymic=item.get('patronymic'),
                group_name=group_name,
                group_id=group_id
            )
            db.session.add(new_user)
            imported += 1

        db.session.commit()
        flash(f'Импортировано: {imported}, пропущено (дубликаты/ошибки): {skipped}.',
              'success' if imported > 0 else 'warning')
        return redirect(url_for('admin_users'))

    # ------------------------------------------------------------------
    #  АУДИТ-ЛОГ
    # ------------------------------------------------------------------
    @app.route('/admin/audit', methods=['GET'])
    @login_required
    def admin_audit():
        if current_user.role != UserRole.ADMIN:
            _admin_only()

        from models import AuditLog
        from sqlalchemy import desc

        page = request.args.get('page', 1, type=int)
        per_page = 50
        action_filter = request.args.get('action', '')
        user_filter = request.args.get('username', '')

        q = AuditLog.query

        if action_filter:
            q = q.filter(AuditLog.action == action_filter)
        if user_filter:
            q = q.filter(AuditLog.username.ilike(f'%{user_filter}%'))

        q = q.order_by(desc(AuditLog.created_at))

        total = q.count()
        offset = (page - 1) * per_page
        logs = q.offset(offset).limit(per_page).all()

        # Все уникальные действия для фильтра
        actions = [r[0] for r in db.session.query(AuditLog.action).distinct().order_by(AuditLog.action).all()]

        return render_template('admin_audit.html',
                               logs=logs, page=page, per_page=per_page,
                               total=total, actions=actions,
                               action_filter=action_filter,
                               user_filter=user_filter)

    # ------------------------------------------------------------------
    #  ИМПОРТ СТУДЕНТОВ ИЗ EXCEL
    # ------------------------------------------------------------------
    @app.route('/admin/import_excel', methods=['POST'])
    @login_required
    def admin_import_excel():
        if current_user.role != UserRole.ADMIN:
            _admin_only()

        file = request.files.get('excel_file')
        if not file:
            flash('Файл не выбран.', 'danger')
            return redirect(url_for('admin_users'))

        from excel_import import import_students_from_excel
        imported, skipped, errors = import_students_from_excel(file)

        msg = f'Импортировано: {imported}, пропущено: {skipped}.'
        if errors:
            msg += f' Ошибки: {"; ".join(errors[:3])}'
        flash(msg, 'success' if imported > 0 else 'warning')
        return redirect(url_for('admin_users'))

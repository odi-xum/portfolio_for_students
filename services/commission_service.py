"""
Сервис комиссии: агрегация статистики по группам, студентам, событиям.
Принимает db: Session от вызывающей стороны (роута).
"""
from __future__ import annotations
from typing import List, Dict, Any
from collections import defaultdict
from sqlalchemy.orm import Session
from sqlalchemy import func
from constants import EventStatus
from models import User, Event, Group


def get_all_students(db: Session) -> List[User]:
    """Все студенты."""
    return db.query(User).filter(User.role == 'student').order_by(User.last_name).all()


def get_all_groups(db: Session) -> List[Group]:
    """Все группы."""
    return db.query(Group).order_by(Group.name).all()


def get_group_stats(db: Session) -> List[dict]:
    """Статистика по всем группам: количество студентов, средняя оценка, сумма оценок."""
    groups = get_all_groups(db)
    result = []
    for g in groups:
        students = db.query(User).filter(
            User.role == 'student', User.group_id == g.id
        ).all()
        student_ids = [s.id for s in students]
        if not student_ids:
            result.append({
                'group': g,
                'student_count': 0,
                'total_score': 0,
                'avg_score': 0,
                'approved_count': 0,
            })
            continue
        stats = db.query(
            func.count(Event.id).label('count'),
            func.coalesce(func.sum(Event.score), 0).label('total'),
            func.coalesce(func.avg(Event.score), 0).label('avg'),
        ).filter(
            Event.student_id.in_(student_ids),
            Event.status == EventStatus.APPROVED,
        ).first()
        result.append({
            'group': g,
            'student_count': len(students),
            'total_score': int(stats.total),
            'avg_score': round(float(stats.avg), 2),
            'approved_count': stats.count,
        })
    # сортировка: сначала по среднему баллу, потом по сумме
    result.sort(key=lambda x: (x['avg_score'], x['total_score']), reverse=True)
    return result


def get_category_distribution(db: Session) -> Dict[str, int]:
    """Распределение мероприятий по категориям ОК (для круговой диаграммы)."""
    rows = db.query(
        Event.category, func.count(Event.id)
    ).filter(
        Event.status == EventStatus.APPROVED
    ).group_by(Event.category).all()
    result = {}
    for cat, cnt in rows:
        label = cat if cat else 'Без категории'
        result[label] = cnt
    return result


def get_score_distribution(db: Session) -> Dict[int, int]:
    """Распределение количества одобренных мероприятий по баллам (для гистограммы)."""
    rows = db.query(
        Event.score, func.count(Event.id)
    ).filter(
        Event.status == EventStatus.APPROVED, Event.score.isnot(None)
    ).group_by(Event.score).order_by(Event.score).all()
    return {int(score): cnt for score, cnt in rows}


def get_status_distribution(db: Session) -> Dict[str, int]:
    """Распределение мероприятий по статусам (для круговой диаграммы)."""
    rows = db.query(
        Event.status, func.count(Event.id)
    ).group_by(Event.status).all()
    labels = {'pending': 'На проверке', 'approved': 'Одобрено', 'rejected': 'Отклонено'}
    return {labels.get(s, s): cnt for s, cnt in rows}


def get_top_students(db: Session, limit: int = 20) -> List[dict]:
    """Лучшие студенты по сумме баллов за одобренные мероприятия."""
    rows = db.query(
        User, func.coalesce(func.sum(Event.score), 0).label('total'),
        func.count(Event.id).label('cnt'),
    ).join(Event, Event.student_id == User.id).filter(
        User.role == 'student', Event.status == EventStatus.APPROVED,
    ).group_by(User.id).order_by(func.sum(Event.score).desc()).limit(limit).all()
    return [
        {'student': u, 'total_score': int(total), 'event_count': cnt}
        for u, total, cnt in rows
    ]


def get_group_score_chart(db: Session) -> List[dict]:
    """Данные для столбчатой диаграммы: средний балл по группам."""
    return get_group_stats(db)


def get_student_stats_for_group(db: Session, group_id: int) -> List[dict]:
    """Статистика по студентам внутри одной группы для столбчатой диаграммы."""
    students = db.query(User).filter(
        User.role == 'student', User.group_id == group_id
    ).order_by(User.last_name).all()
    result = []
    for s in students:
        total = db.query(func.coalesce(func.sum(Event.score), 0)).filter(
            Event.student_id == s.id, Event.status == EventStatus.APPROVED,
        ).scalar()
        cnt = db.query(func.count(Event.id)).filter(
            Event.student_id == s.id, Event.status == EventStatus.APPROVED,
        ).scalar()
        result.append({
            'student': s,
            'total_score': int(total),
            'event_count': cnt,
        })
    result.sort(key=lambda x: x['total_score'], reverse=True)
    return result

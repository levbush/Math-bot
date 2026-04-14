import sqlalchemy as sa
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from data.db_session import SqlAlchemyBase, create_session
from config import lang, _default_stats
from logic.achievements import _default_achievements, ACHIEVEMENTS, AchievementType, SUBJECT, SUBJECTS, Achievement
from typing import Optional
import hashlib


class User(SqlAlchemyBase, UserMixin):
    __tablename__ = 'users'

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    username = sa.Column(sa.String, unique=True, nullable=False, index=True)
    lang = sa.Column(sa.String, nullable=False, default=lang)
    password_hash = sa.Column(sa.String, nullable=False)
    solved = sa.Column(sa.JSON, nullable=False, default=list)
    stats = sa.Column(sa.JSON, nullable=False, default=dict)
    achievements = sa.Column(sa.JSON, nullable=False, default=dict)
    avatar_color = sa.Column(sa.String, nullable=False, default='#FF6B6B')

    @classmethod
    def register(cls, username: str, password: str) -> Optional['User']:
        with create_session() as s:
            if s.query(cls).filter_by(username=username).first():
                return None
            user = cls(
                username=username,
                password_hash=generate_password_hash(password),
                solved=[],
                stats=_default_stats(),
                achievements=_default_achievements(),
                avatar_color=cls._generate_avatar_color(username)
            )
            s.add(user)
            s.commit()
            s.refresh(user)
            return user

    @classmethod
    def _generate_avatar_color(cls, username: str) -> str:
        colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7',
                  '#DDA0DD', '#98D8C8', '#F7DC6F', '#BB8FCE', '#85C1E2',
                  '#F8C471', '#A3E4D7', '#F9E79F', '#D7BDE2', '#F1948A']
        hash_val = hashlib.md5(username.encode()).hexdigest()
        index = int(hash_val[:8], 16) % len(colors)
        return colors[index]

    @classmethod
    def get_by_id(cls, user_id: int) -> Optional['User']:
        with create_session() as s:
            return s.get(cls, user_id)

    @classmethod
    def get_by_username(cls, username: str) -> Optional['User']:
        with create_session() as s:
            return s.query(cls).filter_by(username=username).first()

    @classmethod
    def authenticate(cls, username: str, password: str) -> Optional['User']:
        user = cls.get_by_username(username)
        if not user or not check_password_hash(user.password_hash, password):
            return None
        return user

    def get_solved(self) -> set:
        with create_session() as s:
            user = s.get(User, self.id)
            return set(user.solved)

    def mark_solved(self, problem_id: str, subject: str, difficulty: int):
        with create_session() as s:
            user = s.get(User, self.id)
            solved = list(user.solved)
            if problem_id not in solved:
                solved.append(problem_id)
            stats = dict(user.stats)
            stats[subject] = stats.get(subject, 0) + 1
            stats[str(difficulty)] = stats.get(str(difficulty), 0) + 1
            user.solved = solved
            user.stats = stats
            s.commit()

    def get_stats(self) -> dict:
        with create_session() as s:
            user = s.get(User, self.id)
            return user.stats
    
    def get_lang(self) -> str:
        with create_session() as s:
            user = s.get(User, self.id)
            return user.lang
    
    def set_lang(self):
        with create_session() as s:
            user = s.get(User, self.id)
            if user.lang == "ru":
                user.lang = "en"
            else:
                user.lang = "ru"
            s.commit()
            return user.lang
        
    def get_achievements(self) -> dict:
        with create_session() as s:
            user = s.get(User, self.id)
            return user.achievements
    
    def get_avatar_color(self) -> str:
        with create_session() as s:
            user = s.get(User, self.id)
            return user.avatar_color
        
    def update_achievements(self, user, web_session):
        with create_session() as s:
            user = s.merge(user)
            solved_count = sum(user.stats[subject] for subject in SUBJECTS)
            generic_subject = SUBJECT(None)
            def mark(achievement: Achievement, true=True):
                user.achievements[achievement.name] = true
            for achievement in ACHIEVEMENTS:
                if achievement.type == AchievementType.ultimate:
                    if achievement.condition(tuple(user.achievements.values()).count(True), achievement.condition_reference_point):
                        mark(achievement)
                    else:
                        mark(achievement, False)
                    continue
                if user.achievements[achievement.name]:
                    continue
                match achievement.type:
                    case AchievementType.solved:
                        if achievement.condition(solved_count, achievement.condition_reference_point):
                            mark(achievement)
                    case AchievementType.correct_streak:
                        if achievement.condition(web_session.get('correct_in_a_row', 0), achievement.condition_reference_point):
                            mark(achievement)
                    case generic_subject:
                        if achievement.condition(user.stats[achievement.type.name], achievement.condition_reference_point):
                            mark(achievement)
            s.commit()
            s.refresh(user)

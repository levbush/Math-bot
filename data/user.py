import sqlalchemy as sa
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from data.db_session import SqlAlchemyBase, create_session
from config import SUBJECTS
from typing import Optional


def _default_stats():
    return {key: 0 for key in SUBJECTS + [str(d) for d in range(1, 11)]}


class User(SqlAlchemyBase, UserMixin):
    __tablename__ = 'users'

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    username = sa.Column(sa.String, unique=True, nullable=False, index=True)
    password_hash = sa.Column(sa.String, nullable=False)
    solved = sa.Column(sa.JSON, nullable=False, default=list)
    stats = sa.Column(sa.JSON, nullable=False, default=dict)

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
            )
            s.add(user)
            s.commit()
            s.refresh(user)
            return user

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

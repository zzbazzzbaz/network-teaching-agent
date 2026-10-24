import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.user import Users


class UserRepository:
    def get(self, session: Session, user_id: uuid.UUID) -> Users | None:
        return session.get(Users, user_id)

    def get_by_username(self, session: Session, username: str) -> Users | None:
        return session.scalar(select(Users).where(Users.username == username))

    def create(self, session: Session, *, username: str, password_hash: str) -> Users:
        user = Users(username=username, password_hash=password_hash)
        session.add(user)
        session.commit()
        session.refresh(user)
        return user


user_repository = UserRepository()

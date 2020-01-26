import sqlalchemy as sql
from . import core

USERNAME_LIMIT = 64
EMAIL_LIMIT = USERNAME_LIMIT + 128
PASSWORD_LIMIT = 128


class User(core.Base, core.OrmObject):
    __tablename__ = "users"

    id = sql.Column(sql.Integer, sql.Sequence("users_id_seq"), primary_key=True)
    username = sql.Column(sql.String(USERNAME_LIMIT), nullable=False, index=True)
    email = sql.Column(sql.String(EMAIL_LIMIT), nullable=False)
    password = sql.Column(sql.String(PASSWORD_LIMIT), nullable=False)

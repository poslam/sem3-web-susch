import enum

from database.database import base
from sqlalchemy import TEXT, TIMESTAMP, Column, Enum, Integer


class UserTypes(enum.Enum):
    client = "client"
    moderator = "moderator"


class User(base):
    __tablename__ = 'client'

    id = Column(Integer, primary_key=True)

    nickname = Column(TEXT, unique=True)
    password = Column(TEXT)
    
    type = Column(Enum(UserTypes), default='client')


class RefreshTokenStorage(base):
    __tablename__ = "refresh_token_storage"

    id = Column(Integer, primary_key=True)

    refresh_token = Column(TEXT)
    expired = Column(TIMESTAMP)

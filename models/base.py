"""Base classes for models"""
from abc import ABC
import uuid
import peewee

db = peewee.SqliteDatabase("game.db")


class Model(peewee.Model, ABC):
    """Base model with automatic UUIDs"""

    id_ = peewee.UUIDField(primary_key=True, default=uuid.uuid4)

    class Meta:
        database = db


class Game(Model):
    """A game instance"""

    name = peewee.CharField(unique=True)


class InGameModel(Model):
    """A Model linked to a game"""

    game = peewee.ForeignKeyField(Game)

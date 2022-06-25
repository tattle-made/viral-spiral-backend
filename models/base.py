"""Base classes for models"""
from abc import ABC
import uuid
import peewee

db = peewee.SqliteDatabase("game.db")


class Model(peewee.Model):
    """Base model with automatic UUIDs"""

    id_ = peewee.UUIDField(primary_key=True, default=uuid.uuid4)

    class Meta:
        database = db


class Game(Model):
    """A game instance"""

    name = peewee.CharField(unique=True)
    rounds = peewee.IntegerField(default=0)

    def active(self):
        # TODO implement this
        return self.rounds <= 5

    @classmethod
    def new(cls, name, players: list[str], colors: list[str], topics: list[str]):
        """Creates a new game and performs initial setup"""
        from .player import Player
        from .counters import Color, AffinityTopic

        # TODO create initial biases
        game = cls.create(name=name)

        color_objs = []
        for color_name in colors:
            color_objs.append(Color.create(name=name, game=game))

        topic_objs = []
        for topic_name in topics:
            topic_objs.append(AffinityTopic.create(name=name, game=game))

        for player_name in players:
            color = color_objs[0]
            colors = color_objs[1:] + [color_objs[0]]
            player = Player.create(name=player_name, color=color)
        return game


class InGameModel(Model):
    """A Model linked to a game"""

    game = peewee.ForeignKeyField(Game)

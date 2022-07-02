"""Base classes for models"""
from abc import ABC
from io import StringIO
import json
import uuid
import peewee
from playhouse.dataset import DataSet

from deck_generators import GENERATORS

db = peewee.SqliteDatabase("game.db")
dataset = DataSet(db)

model_id_generator = uuid.uuid4


class Model(peewee.Model):
    """Base model with automatic UUIDs"""

    id_ = peewee.UUIDField(primary_key=True, default=model_id_generator)

    class Meta:
        database = db

    @classmethod
    def import_from_json(cls, json_path, defaults=None):
        """Can provid a JSON defaults dict"""
        # TODO optimise this
        objects = []
        with open(json_path) as infile:
            for dict_ in json.load(infile):
                if defaults:
                    dict_.update(defaults)
                obj = cls.create(**dict_)
                objects.append(obj)

    @classmethod
    def export_to_file(cls, format, output_path):
        ds_table = dataset[cls._meta.name]
        dataset.freeze(ds_table.all(), format=format, filename=output_path)


class Game(Model):
    """A game instance"""

    name = peewee.CharField(unique=True)
    rounds = peewee.IntegerField(default=0)
    draw_fn_name = peewee.CharField(unique=False)
    password = peewee.CharField(unique=False)

    def active(self):
        # TODO implement this
        return self.rounds <= 5

    @classmethod
    def new(
        cls,
        name,
        players: list[str],
        colors: list[str],
        topics: list[str],
        cards_filepath: str = None,
        **model_kwargs
    ):
        """Creates a new game and performs initial setup"""
        from .player import Player
        from .counters import Color, AffinityTopic
        from .card import Card

        # TODO create initial biases
        game = cls.create(name=name, **model_kwargs)

        color_objs = []
        for color_name in colors:
            color_objs.append(Color.create(name=color_name, game=game))

        topic_objs = []
        for topic_name in topics:
            topic_objs.append(AffinityTopic.create(name=topic_name, game=game))

        for player_name in players:
            color = color_objs[0]
            colors = color_objs[1:] + [color_objs[0]]
            player = Player.create(name=player_name, color=color, game=game)

        if cards_filepath:
            Card.import_from_json(cards_filepath, defaults={"game_id": str(game.id_)})

        return game

    def draw(self, player):
        draw_fn = GENERATORS.get(self.draw_fn_name)
        return draw_fn(player)

    @classmethod
    def get_by_name(cls, name):
        """Loads a game object by name and returns it. Raises an exception if
        not found"""

        return cls.select().where(cls.name == name)


class InGameModel(Model):
    """A Model linked to a game"""

    game = peewee.ForeignKeyField(Game)

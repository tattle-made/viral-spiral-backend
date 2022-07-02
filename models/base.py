"""Base classes for models"""
from abc import ABC
import random
from io import StringIO
import json
import uuid
import peewee
from playhouse.dataset import DataSet
import peeweedbevolve

# TODO shift these to environment variables
db = peewee.PostgresqlDatabase(
    "tattleviralspiral",
    host="localhost",
    port=5432,
    user="postgres",
)
dataset = DataSet(db)


def model_id_generator():
    return uuid.uuid4().hex


class Model(peewee.Model):
    """Base model with automatic IDs"""

    id_ = peewee.CharField(primary_key=True, default=model_id_generator)

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
        colors_filepath: str,
        topics_filepath: str,
        cards_filepath: str,
        **model_kwargs
    ):
        """Creates a new game and performs initial setup"""
        from .player import Player
        from .counters import Color, AffinityTopic
        from .card import Card

        # TODO create initial biases
        game = cls.create(name=name, **model_kwargs)

        color_objs = []
        for color_name in json.load(open(colors_filepath)):
            color_objs.append(Color.create(name=color_name, game=game))

        topic_objs = []
        for topic_name in json.load(open(topics_filepath)):
            topic_objs.append(AffinityTopic.create(name=topic_name, game=game))

        sequences = [x for x in range(1, len(players) + 1)]
        random.shuffle(sequences)
        for idx, player_name in enumerate(players):
            color = color_objs[0]
            colors = color_objs[1:] + [color_objs[0]]
            player = Player.create(
                name=player_name, color=color, game=game, sequence=sequences[idx]
            )

        Card.import_from_json(cards_filepath, defaults={"game_id": str(game.id_)})

        return game

    def draw(self, player):
        from deck_generators import GENERATORS

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

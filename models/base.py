"""Base classes for models"""
from abc import ABC
import random
from io import StringIO
import json
import uuid
import peewee
from playhouse.dataset import DataSet
from .utils import model_to_dict
import peeweedbevolve

from constants import PLAYER_WIN_SCORE

# TODO shift these to environment variables
db = peewee.MySQLDatabase(
    "tattleviralspiral",
    host="db",
    port=3306,
    user="root",
    password="helloworld",
)
dataset = DataSet(db)


def model_id_generator():
    return uuid.uuid4().hex


class Model(peewee.Model):
    """Base model with automatic IDs"""

    id_ = peewee.CharField(primary_key=True, default=model_id_generator, max_length=32)
    created_at = peewee.DateTimeField(
        constraints=[peewee.SQL("DEFAULT CURRENT_TIMESTAMP")]
    )
    created_at = peewee.DateTimeField(
        constraints=[peewee.SQL("ON UPDATE CURRENT_TIMESTAMP")]
    )

    class Meta:
        database = db

    @classmethod
    def import_from_json(cls, json_dict=None, json_path=None, defaults=None):
        """
        Required: Either a json dict containing the objects or a path to a json
        file.
        Optional: Can provide a JSON defaults dict"""
        # TODO optimise this
        objects = []
        if not json_dict:
            with open(json_path) as infile:
                json_dict = json.load(infile)
        for dict_ in json_dict:
            if defaults:
                dict_.update(defaults)
            obj = cls.create(**dict_)
            objects.append(obj)
        return objects

    @classmethod
    def export_to_file(cls, format, output_path):
        ds_table = dataset[cls._meta.name]
        dataset.freeze(ds_table.all(), format=format, filename=output_path)


class Game(Model):
    """A game instance"""

    name = peewee.CharField(unique=True)
    draw_fn_name = peewee.CharField(unique=False)
    password = peewee.CharField(unique=False)

    def active(self):
        # TODO implement this
        for player in self.player_set:
            if player.score >= PLAYER_WIN_SCORE:
                return False
        return True

    @property
    def current_round(self):
        round_ = self.round_set.order_by(Round.idx.desc()).first()
        if not round_:
            round_ = Round(game=self, idx=0)  # 0 means not started
        return round_

    def add_round(self):
        """Adds a round to this came"""
        with db.atomic():
            round_ = Round.create(game=self, idx=self.current_round.idx + 1)

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
            color_objs = color_objs[1:] + [color_objs[0]]
            player = Player.create(
                name=player_name, color=color, game=game, sequence=sequences[idx]
            )

        Card.import_from_json(
            json_path=cards_filepath, defaults={"game_id": str(game.id_)}
        )

        return game

    def draw(self, player):
        from .player import Player
        from deck_generators import GENERATORS

        self.add_round()
        draw_fn = GENERATORS.get(self.draw_fn_name)
        Player.update(current=False).where(Player.game == self).execute()
        Player.update(sequence=Player.sequence + 100, current=True).where(
            Player.id_ == player.id_
        ).execute()
        return draw_fn(player)

    @classmethod
    def get_by_name(cls, name):
        """Loads a game object by name and returns it. Raises an exception if
        not found"""

        return cls.select().where(cls.name == name)

    def about(self):
        """Returns a dictionary about this game"""
        from .player import Player

        current_player = self.player_set.where(Player.current == True).first()
        return {
            "name": self.name,
            "players": [model_to_dict(player) for player in self.player_set],
            "colors": [model_to_dict(color) for color in self.color_set],
            "topics": [model_to_dict(topics) for topics in self.affinitytopic_set],
            "draw_fn_name": self.draw_fn_name,
            "current_drawing_player": model_to_dict(current_player)
            if current_player
            else None,
        }

    def update_powers(self):
        """Updates powers of each of the players in this game"""
        for player in self.player_set:
            player.update_powers()


class InGameModel(Model):
    """A Model linked to a game"""

    game = peewee.ForeignKeyField(Game)


class Round(InGameModel):
    """A Round of a game"""

    idx = peewee.IntegerField()

    class Meta:
        # Unique together
        indexes = ((("idx", "game"), True),)

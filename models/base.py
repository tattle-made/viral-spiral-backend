"""Base classes for models"""
from abc import ABC
import os
import random
from io import StringIO
import json
import uuid
import peewee
from playhouse.dataset import DataSet
from .utils import model_to_dict
import peeweedbevolve

# import profiling_utils

from constants import PLAYER_WIN_SCORE

# TODO shift these to environment variables

DB_NAME = os.getenv("DB_NAME")
DB_HOST = os.getenv("DB_HOST")
DB_USERNAME = os.getenv("DB_USERNAME")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_PORT = os.getenv("DB_PORT")

print(DB_NAME, DB_HOST, DB_USERNAME, DB_PASSWORD, DB_PORT)

db = peewee.MySQLDatabase(
    DB_NAME,
    host=DB_HOST,
    port=int(DB_PORT),
    user=DB_USERNAME,
    password=DB_PASSWORD,
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
    updated_at = peewee.DateTimeField(
        constraints=[peewee.SQL("ON UPDATE CURRENT_TIMESTAMP")]
    )

    class Meta:
        database = db

    @classmethod
    def import_from_json(cls, json_dict=None, json_path=None, defaults=None):
        """
        Required: Either a json dict containing the objects or a path to a json
        file.
        Optional: Can provide a JSON defaults dict

        Returns - a tuple list of the following format:
            [
                (original_json, created_object),
                .
                .
            ]
        """
        # TODO optimise this
        objects = []
        if not json_dict:
            with open(json_path) as infile:
                json_dict = json.load(infile)
        for dict_ in json_dict:
            if defaults:
                dict_.update(defaults)
            obj = cls.create(**dict_)
            objects.append((dict_, obj))
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
    ended = peewee.BooleanField(unique=False, default=False)

    def active(self):
        # TODO implement this
        for player in self.player_set:
            if player.score >= PLAYER_WIN_SCORE:
                return False
        return True

    def heartbeat(self):
        """Sends an about event to the game room"""
        self.runner.send_to_game(game=self, data=self.about(), event="heartbeat")

    @property
    def current_round(self):
        round_ = self.round_set.order_by(Round.created_at.desc()).first()
        if not round_:
            round_ = Round(game=self, started=False)
        return round_

    def add_round(self):
        """Adds a round to this came"""
        round_ = Round.create(game=self, started=True)

    def total_global_bias(self):
        """Total global bias of the game"""
        # Total number of biased cards which have bene passed at least once
        from models import Card

        return (
            self.card_set.where(Card.original_player.is_null(False))
            .where(Card.bias_against.is_null(False))
            .count()
        )

    @classmethod
    # @profiling_utils.profile
    def new(
        cls,
        name,
        players: list[str],
        colors_filepath: str,
        topics_filepath: str,
        cards_filepath: str,
        encyclopedia_filepath: str,
        **model_kwargs
    ):
        """Creates a new game and performs initial setup"""
        from .player import Player
        from .counters import Color, AffinityTopic
        from .card import Card
        from .encyclopedia import Article

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
        Article.import_from_json(
            json_path=encyclopedia_filepath, defaults={"game_id": str(game.id_)}
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

        players = []
        for player in self.player_set:
            dict_ = model_to_dict(player)
            dict_["affinities"] = player.all_affinities()
            dict_["biases"] = player.all_biases()
            players.append(dict_)

        return {
            "name": self.name,
            "players": players,
            "colors": [model_to_dict(color) for color in self.color_set],
            "topics": [model_to_dict(topics) for topics in self.affinitytopic_set],
            "draw_fn_name": self.draw_fn_name,
            "current_drawing_player": model_to_dict(current_player)
            if current_player
            else None,
            "total_global_bias": self.total_global_bias(),
        }

    def update_powers(self):
        """Updates powers of each of the players in this game"""
        for player in self.player_set:
            player.update_powers()

    def end(self):
        self.ended = True
        self.save()


class InGameModel(Model):
    """A Model linked to a game"""

    game = peewee.ForeignKeyField(Game)


class Round(InGameModel):
    """A Round of a game"""

    started = peewee.BooleanField(null=True)

    class Meta:
        # Unique together
        indexes = ((("created_at", "game"), True),)

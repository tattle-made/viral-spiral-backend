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

    def next(self, order_by=None):
        """Returns the next obj. You can specify the order_by as a field.
        if order_by == None, it will order by created_at"""

        if not order_by:
            order_by = FullRound.created_at

        objs = self.select().order_by(order_by).iterator()
        while obj := next(objs, None):
            if obj.id_ == self.id_:
                return next(objs, None)

    def previous(self, order_by=None):
        """Returns the prev obj. You can specify the order_by as a field.
        if order_by == None, it will order by created_at"""

        if not order_by:
            order_by = FullRound.created_at
        order_by = order_by.desc()

        return self.next(order_by=order_by)


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
            round_ = Round.create(
                game=self,
                started=False,
                full_round=FullRound.select()
                .order_by(FullRound.created_at.desc())
                .first(),
            )
        return round_

    @property
    def previous_round(self):
        return self.round_set.order_by(Round.created_at.desc())[1]

    def add_round(self, full_round):
        """Adds a round to this came"""
        round_ = Round.create(game=self, full_round=full_round, started=True)

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
    def new_name(cls):
        """Returns a new name for a new game"""
        verbs = [
            "obnoxious",
            "odd",
            "fun",
            "smart",
            "lazy"
        ]
        nouns = [
            "cow",
            "dog",
            "cat",
            "banana",
            "router",
        ]
        number = "%04d" % random.randint(0, 9999)
        name = f"{random.choice(verbs)}-{random.choice(nouns)}-{number}"
        if cls.select().where(cls.name == name).exists():
            return cls.new_name()
        return name

    @classmethod
    # @profiling_utils.profile
    def new(
        cls,
        player_count: int,
        colors_filepath: str,
        topics_filepath: str,
        cards_filepath: str,
        encyclopedia_filepath: str,
        **model_kwargs,
    ):
        """Creates a new game and performs initial setup"""
        from .player import Player
        from .counters import Color, AffinityTopic
        from .card import Card
        from .encyclopedia import Article

        encyclopedia_filepath = "config_jsons/example1/articles.json"

        name = cls.new_name()

        # TODO create initial biases
        game = cls.create(name=name, **model_kwargs)

        color_objs = []
        for color_name in json.load(open(colors_filepath)):
            color_objs.append(Color.create(name=color_name, game=game))

        topic_objs = []
        for topic_name in json.load(open(topics_filepath)):
            topic_objs.append(AffinityTopic.create(name=topic_name, game=game))

        sequences = [x for x in range(1, player_count + 1)]
        random.shuffle(sequences)
        for idx in range(player_count):
            color = color_objs[0]
            color_objs = color_objs[1:] + [color_objs[0]]
            player = Player.create(
                color=color, game=game, sequence=sequences[idx]
            )

        Card.import_from_json(
            json_path=cards_filepath, defaults={"game_id": str(game.id_)}
        )
        Article.import_from_json(
            json_path=encyclopedia_filepath, defaults={"game_id": str(game.id_)}
        )

        return game

    def get_unclaimed_player(self):
        """Returns a player that hasn't been claimed yet.

        When a new user joins the game, they claim a player - and the 
        name attribute of that player is set.
        """
        from .player import Player
        # Player.name.is_null was not selecting for empty varchar field
        # peewee.fn.Random() isn't generating a valid sql syntax
        # I implemented an acceptable solution. Once the syntax issues are
        # resolved, we should revert to the original logic of ordering in random order 
        return self.player_set.select().where(Player.name == "").order_by(Player.created_at.desc()).first()

    def draw(self, player, full_round):
        from .player import Player
        from deck_generators import GENERATORS

        self.add_round(full_round=full_round)
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


class FullRound(InGameModel):
    """A set of rounds"""

    pass


class Round(InGameModel):
    """A Round of a game"""

    started = peewee.BooleanField(null=True)
    full_round = peewee.ForeignKeyField(FullRound)

    class Meta:
        # Unique together
        indexes = ((("created_at", "game"), True),)

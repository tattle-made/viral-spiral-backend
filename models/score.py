"""
Keeps all game related scores in one table.
includes player's affinities, biases and clout.

Each row represents a type of score for a player in a game -
the player's clout, or their affinity towards a topic or their bias against a color

The table's schema was chosen keeping in mind that the affinity and bias count 
might change, so we've adopted this instead of a table with large but fixed columns.

"""
from enum import Enum
from .base import InGameModel, Game
from .player import Player
from .counters import Color, AffinityTopic
import peewee


class ScoreType(Enum):
    CLOUT = "clout"
    AFFINITY = "affinity"
    BIAS = "bias"


class Score(InGameModel):
    player = peewee.ForeignKeyField(Player, null=True)

    # Tells you which type of score this is. The subsequent fields `target` and `value`
    # need to be treated accordingly. Possible values are clout, affinity or bias.
    # I would have preferred to use an enum but peewee implementation for Enum seemed non trivial
    type = peewee.FixedCharField(max_length=10)
    target = peewee.UUIDField(null=True)
    value = peewee.IntegerField()

    @classmethod
    def initialize(cls, game: Game, player: Player):
        Score.create(game=game, player=player, type=ScoreType.CLOUT.value)
        for affinity in game.affinitytopic_set:
            Score.create(
                game=game,
                player=player,
                type=ScoreType.AFFINITY.value,
                target=affinity.id_,
            )
        for bias in game.color_set:
            if bias != player.color:
                Score.create(
                    game=game, player=player, type=ScoreType.BIAS.value, target=bias.id_
                )

    @classmethod
    def inc_bias(cls, player: Player, color: Color, inc: int):
        (
            Score.update({Score.value: Score.value + inc})
            .where(Score.game == player.game)
            .where(Score.player == player)
            .where(Score.target == color.id_)
            .where(Score.type == ScoreType.BIAS.value)
            .execute()
        )

    @classmethod
    def inc_affinity(cls, player: Player, affinity: AffinityTopic, inc: int):
        (
            Score.update({Score.value: Score.value + inc})
            .where(Score.game == player.game)
            .where(Score.player == player)
            .where(Score.target == affinity.id_)
            .where(Score.type == ScoreType.AFFINITY.value)
            .execute()
        )

    @classmethod
    def inc_clout(cls, player: Player, inc: int):
        (
            Score.update({Score.value: Score.value + inc})
            .where(Score.game == player.game)
            .where(Score.player == player)
            .where(Score.type == ScoreType.CLOUT.value)
            .execute()
        )

    """
        A helper method to format scores in a way thats backwards compatible
        with what the client expects 
    """

    @classmethod
    def all_scores_for_client(cls, scores: peewee.ModelSelect):
        all_scores = {"score": 0, "biases": {}, "affinities": {}}
        for score in scores:
            if score.type == ScoreType.CLOUT.value:
                all_scores["score"] = score.value
            elif score.type == ScoreType.BIAS.value:
                all_scores["biases"][score.target] = score.value
            elif score.type == ScoreType.AFFINITY.value:
                all_scores["affinities"][score.target] = score.value
        return all_scores

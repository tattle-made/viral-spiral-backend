"""List of powers"""

import peewee
from .base import InGameModel, Game, Round, db, model_id_generator, FullRound
from .player import Player
from .counters import AffinityTopic

from constants import ACTIVE_STR
from exceptions import NotFound, DuplicateAction

VIRAL_SPIRAL = "viral_spiral"
CANCEL = "cancel"
FAKE_NEWS = "fake_news"

ALL_POWERS = [VIRAL_SPIRAL, CANCEL, FAKE_NEWS]


class PlayerPower(InGameModel):
    """The name is the name of the power
    Player is the player
    created_at is used to maintain historic count. The latest created_on is the current
        power status
    active = True means the player has this power
    active = False means the player does not have this power
    """

    name = peewee.CharField()
    player = peewee.ForeignKeyField(Player, backref="powers", unique=False)
    active = peewee.BooleanField()

    class Meta:
        # Unique together
        indexes = ((("name", "player", "game", "created_at"), True),)

    @classmethod
    def get_latest(cls, name: str, player: Player):
        assert name in ALL_POWERS
        power = (
            player.powers.where(cls.name == name)
            .order_by(cls.created_at.desc())
            .first()
        )
        if not power:
            power = cls(name=name, player=player, active=False)
        return power

    @classmethod
    def update(cls, name: str, player: Player, active: bool):
        # TODO No need to update if power hasn't changed
        assert name in ALL_POWERS
        try:
            cls.create(name=name, player=player, active=active, game=player.game)
        except peewee.IntegrityError:
            pass


class CancelStatus(InGameModel):
    """State variables for cancelling a player for a round"""

    round = peewee.ForeignKeyField(Round)
    against = peewee.ForeignKeyField(Player)
    initiator = peewee.ForeignKeyField(Player)
    topic = peewee.ForeignKeyField(AffinityTopic)

    class Meta:
        # Unique together
        indexes = ((("round", "against", "initiator", "game"), True),)

    @classmethod
    def cancelled(cls, player: Player):
        """Returns True if this player has been cancelled in the previous FullRound"""
        try:
            current_full_round = player.game.current_round.full_round
            previous_full_round = current_full_round.previous()
        except FullRound.DoesNotExist:
            return False

        rounds = previous_full_round.round_set

        for round_ in rounds:
            votes = (
                CancelVote.select()
                .join(cls)
                .where(
                    cls.against == player,
                    cls.game == player.game,
                    cls.round == round_,
                    CancelVote.vote == True,
                )
            )
            grouped = votes.select(
                cls.initiator, peewee.fn.COUNT(CancelVote.id_).alias("votes")
            ).group_by(cls.initiator)

            for row in grouped:
                if (
                    row.votes
                    / player.game.player_set.where(Player.color == player.color).count()
                    >= 0.5
                ):
                    return True
        return False

    @classmethod
    def initiate(cls, initiator: Player, against: Player, topic: AffinityTopic):
        cancel_status = cls.create(
            round=initiator.game.current_round,
            against=against,
            initiator=initiator,
            topic=topic,
            game=initiator.game,
        )

        CancelVote.initiate(cancel_status=cancel_status, initiator=initiator)
        return cancel_status


class CancelVote(InGameModel):
    cancel_status = peewee.ForeignKeyField(CancelStatus)
    voter = peewee.ForeignKeyField(Player)
    vote = peewee.BooleanField()

    class Meta:
        # Unique together
        indexes = ((("cancel_status", "voter", "game"), True),)

    @classmethod
    def initiate(cls, cancel_status: CancelStatus, initiator: Player):
        # TODO use multi put
        for player in player.game.player_set:
            if not player.affinity_matches(
                with_=initiator, towards=cancel_status.topic
            ):
                continue

            voted = True if player.id_ == initiator.id_ else None
            cls.create(cancel_status=cancel_status, voter=player, voted=voted)

    @classmethod
    def pending_votes(cls, round_: Round):
        return (
            cls.select()
            .join(CancelStatus)
            .where(CancelStatus.round == round_, cls.game == round_.game)
        )

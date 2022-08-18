"""List of powers"""

import peewee
from .base import InGameModel, Game, Round, db, model_id_generator
from .player import Player

from constants import ACTIVE_STR
from exceptions import NotFound, DuplicateAction

VIRAL_SPIRAL = "viral_spiral"
CANCEL = "cancel"
FAKE_NEWS = "fake_news"

ALL_POWERS = [VIRAL_SPIRAL, CANCEL, FAKE_NEWS]


class PlayerPower(InGameModel):
    """The name is the name of the power
    Player is the player
    idx is used to maintain historic count. The gratest idx is the current
        power status
    active = True means the player has this power
    active = False means the player does not have this power
    """

    name = peewee.CharField()
    player = peewee.ForeignKeyField(Player, backref="powers", unique=False)
    idx = peewee.IntegerField()
    active = peewee.BooleanField()

    class Meta:
        # Unique together
        indexes = ((("name", "player", "game", "idx"), True),)

    @classmethod
    def get_latest(cls, name: str, player: Player):
        assert name in ALL_POWERS
        power = player.powers.where(cls.name == name).order_by(cls.idx.desc()).first()
        if not power:
            power = cls(name=name, player=player, idx=0, active=False)
        return power

    @classmethod
    def update(cls, name: str, player: Player, active: bool):
        # TODO No need to update if power hasn't changed
        assert name in ALL_POWERS
        with db.atomic():
            old_idx = cls.get_latest(name=name, player=player).idx
            new_idx = old_idx + 1
            cls.create(
                name=name, player=player, active=active, game=player.game, idx=new_idx
            )


class CancelStatus(InGameModel):
    """State variables for cancelling a player for a round"""

    round = peewee.ForeignKeyField(Round)
    against = peewee.ForeignKeyField(Player)
    initiator = peewee.ForeignKeyField(Player)

    class Meta:
        # Unique together
        indexes = ((("round", "against", "initiator", "game"), True),)

    @classmethod
    def cancelled(cls, player: Player):
        """Returns True if this player has been cancelled in the active round
        else False"""
        votes = (
            CancelVote.select()
            .join(cls)
            .where(
                cls.against == player,
                cls.game == player.game,
                cls.round == player.game.current_round,
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
    def initiate(cls, initiator: Player, against: Player):
        cancel_status = cls.create(
            round=initiator.game.current_round,
            against=against,
            initiator=initiator,
            game=initiator.game,
        )

        CancelVote.initiate(cancel_status=cancel_status, initiator=initiator)


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
        for player in player.game.player_set.where(Player.color == player.color):
            voted = True if player.id_ == initiator.id_ else None
            cls.create(cancel_status=cancel_status, voter=player, voted=voted)

    @classmethod
    def pending_votes(cls, round_: Round):
        return (
            cls.select()
            .join(CancelStatus)
            .where(CancelStatus.round == round_, cls.game == round_.game)
        )

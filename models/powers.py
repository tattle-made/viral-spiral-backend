"""List of powers"""

import peewee
from .base import InGameModel, Game, Round, db, model_id_generator, FullRound
from .player import Player
from .counters import AffinityTopic

from constants import ACTIVE_STR, CANCEL_VOTE_ALL_PLAYERS
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

    # Keeps track of the final result of the voting. Possible values - -1 : unfinished poll, 0 : player wasnt cancelled, 1 : player was cancelled
    final_status = peewee.SmallIntegerField(default=-1)

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

        if not previous_full_round:
            return False

        rounds = previous_full_round.round_set

        for round_ in rounds:
            status = (
                CancelStatus.select()
                .where(CancelStatus.round_id == round_.id_)
                .where(CancelStatus.against_id == player.id_)
                .first()
            )
            status_bool = True if status and status.final_status else False
            return status_bool

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

    # This method is to be called everytime a new vote is casted. If all the votes aren't casted yet, final_status remains unchanged
    @classmethod
    def set_final_status(cls, cancel_status_id: str):
        from itertools import filterfalse

        MAJORITY_THRESHOLD = 0.5

        votes = CancelVote.select().where(
            CancelVote.cancel_status_id == cancel_status_id
        )

        total_votes = len(votes)
        total_uncasted_votes = len(
            list(filterfalse(lambda x: x.vote == 1 or x.vote == 0, votes))
        )

        if total_uncasted_votes > 0:
            return
        else:
            total_yes_votes = len(list(filterfalse(lambda x: x.vote == 0, votes)))
            vote_ratio = total_yes_votes / total_votes
            voting_result = 1 if vote_ratio >= MAJORITY_THRESHOLD else 0
            CancelStatus.update(final_status=voting_result).where(
                CancelStatus.id_ == cancel_status_id
            ).execute()


class CancelVote(InGameModel):
    cancel_status = peewee.ForeignKeyField(CancelStatus)
    voter = peewee.ForeignKeyField(Player)
    vote = peewee.SmallIntegerField(default=-1)

    class Meta:
        # Unique together
        indexes = ((("cancel_status", "voter", "game"), True),)

    @classmethod
    def initiate(cls, cancel_status: CancelStatus, initiator: Player):
        # TODO use multi put
        for player in initiator.game.player_set:
            if not (
                CANCEL_VOTE_ALL_PLAYERS
                or player.affinity_matches(with_=initiator, towards=cancel_status.topic)
            ):
                continue

            voted = True if player.id_ == initiator.id_ else None
            cls.create(
                cancel_status=cancel_status,
                voter=player,
                voted=voted,
                game=initiator.game,
            )

    @classmethod
    def pending_votes(cls, round_: Round):
        return (
            cls.select()
            .join(CancelStatus)
            .where(CancelStatus.round == round_, cls.game == round_.game)
            .where(CancelVote.vote == -1)
        )

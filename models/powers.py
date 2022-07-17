"""List of powers"""

import peewee
from .base import InGameModel, Game, db
from .player import Player

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

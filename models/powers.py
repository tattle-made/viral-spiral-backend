"""List of powers"""

import peewee
from .base import InGameModel
from .player import Player

VIRAL_SPIRAL = "viral_spiral"
CANCEL = "cancel"
FAKE_NEWS = "fake_news"

ALL_POWERS = [VIRAL_SPIRAL, CANCEL, FAKE_NEWS]


class PlayerPower(InGameModel):
    name = peewee.CharField()
    player = peewee.ForeignKeyField(Player, backref="powers", unique=False)

    class Meta:
        # Unique together
        indexes = ((("name", "player_id"), True),)

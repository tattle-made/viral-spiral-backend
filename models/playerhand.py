import peewee
from .base import InGameModel
from .card import CardInstance
from .player import Player


class PlayerHand(InGameModel):
    player = peewee.ForeignKeyField(Player, null=False)
    card_instance = peewee.ForeignKeyField(CardInstance, null=False)

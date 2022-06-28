import peewee
from .base import InGameModel
from .card import CardInstance
from .player import Player


class PlayerCardQueue(InGameModel):
    """Many to many relation to store the player card queue.

    Each card instance in this model requires some action from the player in
    the given order.

    This is a FIFO queue"""

    idx = peewee.IntegerField()
    player = peewee.ForeignKeyField(Player, backref="card_queue_items")
    card_instance = peewee.ForeignKeyField(CardInstance, backref="card_queue_items")
    active = peewee.BooleanField(default=True)

    class Meta:
        # Unique together
        indexes = (
            (("idx", "player_id", "game_id"), True),
            (("card_instance_id", "player_id", "game_id"), True),
        )

    @classmethod
    def queue(cls, player, card_instance):
        """Adds a card instance to given player's card queue"""
        # TODO atomic
        query = (
            cls.select().where(cls.player == player).order_by(cls.idx.desc()).limit(1)
        )
        if query.count() == 1:
            idx = query.first().idx + 1
        else:
            idx = 0
        saved = cls.create(
            idx=idx, player=player, game=player.game, card_instance=card_instance
        )
        return saved

    @classmethod
    def dequeue(cls, player, card_instance):
        """Sets a card queue instance to active == false"""
        query = (
            cls.select()
            .where(player == player)
            .where(card_instance == card_instance)
            .where(active=True)
        )
        query.update(active=False)

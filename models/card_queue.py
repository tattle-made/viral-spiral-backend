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
    card_instance = peewee.ForeignKeyField(
        CardInstance, backref="card_queue_items", unique=True
    )
    active = peewee.BooleanField(default=True)

    @classmethod
    def queue(cls, card_instance):
        """Adds a card instance to given player's card queue"""
        # TODO atomic
        query = (
            cls.select()
            .where(cls.player == card_instance.player)
            .order_by(cls.idx.desc())
            .limit(1)
        )
        if query.count() == 1:
            idx = query.first().idx + 1
        else:
            idx = 0
        saved = cls.create(
            idx=idx,
            player=card_instance.player,
            game=card_instance.game,
            card_instance=card_instance,
        )
        return saved

    @classmethod
    def dequeue(cls, card_instance):
        """Sets a card queue instance to active == false"""
        cls.update(active=False).where(cls.card_instance == card_instance).where(
            cls.active == True
        ).execute()

    @classmethod
    def mark_as_fake(cls, card):
        """Dequeues all instances for a given card"""
        ids = [
            x.id_
            for x in cls.select(cls.id_)
            .join(CardInstance)
            .where(CardInstance.card == card)
        ]
        cls.update(acive=False).where(cls.id_.in_(ids))

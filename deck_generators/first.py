"""A deck generator function"""

import peewee
from models import Card, Player


def draw(player: Player):
    """Takes a player as an argument and returns a card instance from the
    remaining cards"""

    card = (
        Card.select()
        .where(Card.original_player == None)
        .order_by(peewee.fn.Random())
        .limit(1)
        .first()
    )
    return card.draw()

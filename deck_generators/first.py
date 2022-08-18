"""A deck generator function"""

import peewee
from exceptions import OutOfCards
from models import Card, Player


def draw(player: Player):
    """Takes a player as an argument and returns a card instance from the
    remaining cards"""

    card = (
        Card.select()
        .where(Card.game == player.game)
        .where(Card.original_player == None)
        .limit(1)
        .first()
    )
    if not card:
        raise OutOfCards(f"Game: {player.game.name}, Player: {player.name}")
    return card.draw(player)

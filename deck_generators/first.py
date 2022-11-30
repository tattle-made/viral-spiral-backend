"""A deck generator function"""

import random

import peewee
from exceptions import OutOfCards
from models import Card, Player


def draw(player: Player):
    """Takes a player as an argument and returns a card instance from the
    remaining cards"""

    # First randomly select an unplayed card
    card = (
        Card.select(Card.storyline)
        .where(Card.game == player.game)
        .where(Card.original_player == None)
        .first()
    )

    # Now get lowest pending index of this card's storyline
    card = (
        Card.select()
        .where(Card.game == player.game)
        .where(Card.original_player == None)
        .where(Card.storyline == card.storyline)
        .order_by(Card.storyline_index)
        .first()
    )
    if not card:
        raise OutOfCards(f"Game: {player.game.name}, Player: {player.name}")
    return card.draw(player)

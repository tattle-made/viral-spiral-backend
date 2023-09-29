"""
CARD drawn in a game is a function of the total global bias and some probabilities

BIAS cards appear with a constant probability of 0.25 throughout the game
For the remaining 0.75, we have two choices :
    a. with a probability of tgb/MAX_TGB, draw a card containing FAKE AFFINITY NEWS  or FAKE TOPICAL news
    b. with a probability of (1 - tgb/MAX_TGB), draw a card containing TRUE AFFINITY NEWS or TRUE TOPICAL news
"""


from exceptions import OutOfCards
from models import Card, Player
import random
from constants import TGB_END_SCORE
from peewee import fn



def _draw_true_cards(player: Player):
    """
    Test function only to be used during debugging and testing.
    This version of the draw function only returns true cards.
    Ideal for testing the turn into fake news power."""
    tgb = player.game.total_global_bias()

    card = (
        Card.select()
        .where(Card.game == player.game)
        .where(Card.original_player == None)
        .where(Card.affinity_towards != None)
        .where(Card.fake == False)
        .where(Card.tgb <= tgb)
        .where(Card.bias_against.name != 'yellow')
        .order_by(fn.Rand())
        .first()
    )

    return card.draw(player)


def draw(player: Player):
    tgb = player.game.total_global_bias()

    bias_p = random.uniform(0, 1)

    # temporary code to exclude drawing anti yellow card
    yellow = [color for color in player.game.color_set if color.name=='yellow'][0]

    print('drawing card')
    if bias_p <= 0.1:
        print('drawing a bias card')
        # draw a bias card
        card = (
            Card.select()
            .where(Card.game == player.game)
            .where(Card.original_player == None)
            .where(Card.bias_against != None)
            .where(Card.bias_against != player.color)
            .where(Card.bias_against != yellow)
            .where(Card.tgb <= tgb + 2)
            .order_by(fn.Rand())
            .first()
        )

    else:
        # draw AFFINITY or TOPICAL card
        fake_p = random.uniform(0, 1)
        should_draw_affinity = random.uniform(0, 1) < 0.5
        should_draw_topical = not should_draw_affinity

        if fake_p < (tgb / TGB_END_SCORE):
            # draw FAKE card
            print('drawing a fake card')
            if should_draw_affinity:
                print('drawing a fake affinity')
                card = (
                    Card.select()
                    .where(Card.game == player.game)
                    .where(Card.original_player == None)
                    .where(Card.affinity_towards != None)
                    .where(Card.fake == True)
                    .where(Card.faked_by == None)
                    .where(Card.tgb <= tgb)
                    .order_by(fn.Rand())
                    .first()
                )
            if should_draw_topical:
                print('drawing a fake topical card')
                card = (
                    Card.select()
                    .where(Card.game == player.game)
                    .where(Card.original_player == None)
                    .where(Card.affinity_towards == None)
                    .where(Card.bias_against == None)
                    .where(Card.fake == True)
                    .where(Card.faked_by == None)
                    .where(Card.tgb <= tgb)
                    .order_by(fn.Rand())
                    .first()
                )
        else:
            # draw TRUE card
            if should_draw_affinity:
                card = (
                    Card.select()
                    .where(Card.game == player.game)
                    .where(Card.original_player == None)
                    .where(Card.affinity_towards != None)
                    .where(Card.fake == False)
                    .where(Card.tgb <= tgb)
                    .order_by(fn.Rand())
                    .first()
                )
            if should_draw_topical:
                card = (
                    Card.select()
                    .where(Card.game == player.game)
                    .where(Card.original_player == None)
                    .where(Card.affinity_towards == None)
                    .where(Card.bias_against == None)
                    .where(Card.fake == False)
                    .where(Card.tgb <= tgb)
                    .order_by(fn.Rand())
                    .first()
                )

    if not card:
        card = (
            Card.select()
            .where(Card.game == player.game)
            .where(Card.original_player == None)
            .where(Card.tgb <= tgb)
            .where(Card.bias_against != yellow)
            .order_by(fn.Rand())
            .first()
        )
    return card.draw(player)

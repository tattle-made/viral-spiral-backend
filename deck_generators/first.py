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

def clamp(x, minn, maxx):
   return x if x > minn and x < maxx else (minn if x < minn else maxx)

def select_true_topical_card(player, tgb, yellow):
    return (
        Card.select()
        .where(Card.game == player.game)
        .where(Card.original_player == None)
        .where(Card.affinity_towards == None)
        .where(Card.bias_against == None)
        .where(Card.fake == False)
        .count(),
        Card.select()
        .where(Card.game == player.game)
        .where(Card.original_player == None)
        .where(Card.affinity_towards == None)
        .where(Card.bias_against == None)
        .where(Card.fake == False)
        .order_by(fn.Rand())
        .first()
    )

def select_true_affinity_card(player, tgb, yellow):
    return (
        Card.select()
        .where(Card.game == player.game)
        .where(Card.original_player == None)
        .where(Card.affinity_towards != None)
        .where(Card.fake == False)
        .where(Card.tgb <= tgb + 2)
        .count(),
        Card.select()
        .where(Card.game == player.game)
        .where(Card.original_player == None)
        .where(Card.affinity_towards != None)
        .where(Card.fake == False)
        .where(Card.tgb <= tgb + 2)
        .order_by(fn.Rand())
        .first()
    )

def select_fake_topical_card(player, tgb, yellow):
    return (
        Card.select()
        .where(Card.game == player.game)
        .where(Card.original_player == None)
        .where(Card.affinity_towards == None)
        .where(Card.bias_against == None)
        .where(Card.fake == True)
        .where(Card.faked_by == None)
        .count(),
        Card.select()
        .where(Card.game == player.game)
        .where(Card.original_player == None)
        .where(Card.affinity_towards == None)
        .where(Card.bias_against == None)
        .where(Card.fake == True)
        .where(Card.faked_by == None)
        .order_by(fn.Rand())
        .first()
    )

def select_fake_affinity_card(player, tgb, yellow):
    return (
        Card.select()
        .where(Card.game == player.game)
        .where(Card.original_player == None)
        .where(Card.affinity_towards != None)
        .where(Card.fake == True)
        .where(Card.faked_by == None)
        .where(Card.tgb <= tgb + 2)
        .count(),
        Card.select()
        .where(Card.game == player.game)
        .where(Card.original_player == None)
        .where(Card.affinity_towards != None)
        .where(Card.fake == True)
        .where(Card.faked_by == None)
        .where(Card.tgb <= tgb + 2)
        .order_by(fn.Rand())
        .first()
    )

def select_bias_card(player, tgb, yellow):
    return(
        Card.select()
        .where(Card.game == player.game)
        .where(Card.original_player == None)
        .where(Card.bias_against != None)
        .where(Card.bias_against != player.color)
        .where(Card.bias_against != yellow)
        .where(Card.tgb <= tgb + 2)
        .count(),
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

def _select(player: Player):
    card = None
    while card == None:
        # random.seed("denny-1")
        tgb = player.game.total_global_bias()

        bias_p = random.uniform(0, 1)

        # temporary code to exclude drawing anti yellow card
        yellow = [color for color in player.game.color_set if color.name=='yellow'][0]

        print('\t\tdrawing card')
        if bias_p <= 0.5:
            print('\t\t\tdrawing a bias card')
            # draw a bias card
            (_, card) = select_bias_card(player, tgb, yellow)

        else:
            print('\t\t\tdrawing a unbiased card')
            # draw AFFINITY or TOPICAL card
            fake_p = random.uniform(0, 1)
            should_draw_affinity = random.uniform(0, 1) < 0.5
            should_draw_topical = not should_draw_affinity
            should_draw_true = random.uniform(0,1) < (1-(tgb/TGB_END_SCORE))
            should_draw_fake = not should_draw_true
            print(should_draw_affinity, should_draw_topical, should_draw_true, should_draw_fake)

            if should_draw_fake : 
                # draw FAKE card
                print('\t\t\t\tdrawing a fake card')
                if should_draw_affinity:
                    print('\t\t\t\t\tdrawing a fake affinity')
                    (_, card) = select_fake_affinity_card(player, tgb, yellow)
                if should_draw_topical:
                    print('\t\t\t\t\tdrawing a fake topical card')
                    (_, card) = select_fake_topical_card(player, tgb, yellow)
            else:
                # draw TRUE card
                print('\t\t\t\tdrawing a true card')
                if should_draw_affinity:
                    print('\t\t\t\t\tdrawing a true affinity card')
                    (_, card) = select_true_affinity_card(player, tgb, yellow)
                if should_draw_topical:
                    print('\t\t\t\t\tdrawing a true topical card')
                    (count, card) = select_true_topical_card(player, tgb, yellow)
                    print(count)
                    if not card:
                        (_, card) = select_bias_card(player, tgb, yellow)
    
    return card


def select(player: Player):
    card = None
    while card == None:
        # random.seed("denny-1")
        tgb = player.game.total_global_bias()

        bias_p = random.uniform(0, 1)

        # temporary code to exclude drawing anti yellow card
        yellow = [color for color in player.game.color_set if color.name=='yellow'][0]

        print('\t\tdrawing card')
        if bias_p <= 0.2:
            print('\t\t\tdrawing a bias card')
            # draw a bias card
            (_, card) = select_bias_card(player, tgb, yellow)

        else:
            print('\t\t\tdrawing a unbiased card')
            # draw AFFINITY or TOPICAL card
            fake_p = random.uniform(0, 1)
            should_draw_affinity = random.uniform(0, 1) < 0.5
            should_draw_topical = not should_draw_affinity
            should_draw_true = random.uniform(0,1) < (1-(tgb/TGB_END_SCORE))
            should_draw_fake = not should_draw_true
            print(should_draw_affinity, should_draw_topical, should_draw_true, should_draw_fake)

            if should_draw_fake : 
                # draw FAKE card
                print('\t\t\t\tdrawing a fake card')
                if should_draw_affinity:
                    print('\t\t\t\t\tdrawing a fake affinity')
                    (_, card) = select_fake_affinity_card(player, tgb, yellow)
                if should_draw_topical:
                    print('\t\t\t\t\tdrawing a fake topical card')
                    (_, card) = select_fake_topical_card(player, tgb, yellow)
            else:
                # draw TRUE card
                print('\t\t\t\tdrawing a true card')
                if should_draw_affinity:
                    print('\t\t\t\t\tdrawing a true affinity card')
                    (_, card) = select_true_affinity_card(player, tgb, yellow)
                if should_draw_topical:
                    print('\t\t\t\t\tdrawing a true topical card')
                    (count, card) = select_true_topical_card(player, tgb, yellow)
                    print(count)
                    if not card:
                        (_, card) = select_bias_card(player, tgb, yellow)
    
    return card

def draw(player: Player):
    card = select(player)
    return card.draw(player)


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

def draw(player: Player):
    tgb = player.game.total_global_bias()

    bias_p = random.uniform(0,1)


    if bias_p <= 0.2:   
        # draw a bias card
        card = (
            Card.select()
                .where(Card.game == player.game)
                .where(Card.original_player == None)
                .where(Card.bias_against != None) 
                .where(Card.bias_against != player.color)
                .where(Card.tgb <= tgb + 2)               
                .first()
        )

    else : 
        # draw AFFINITY or TOPICAL card
        fake_p = random.uniform(0,1)
        should_draw_affinity = random.uniform(0,1) < 0.5
        should_draw_topical = not should_draw_affinity
        
        if fake_p < (tgb/TGB_END_SCORE):    
            # draw FAKE card
            if should_draw_affinity:
                card = (Card.select()
                    .where(Card.game == player.game)
                    .where(Card.original_player == None)
                    .where(Card.affinity_towards != None)
                    .where(Card.fake == True) 
                    .where(Card.faked_by == None)
                    .where(Card.tgb <= tgb) 
                    .first()
                )
            if should_draw_topical:
                card = (Card.select()
                    .where(Card.game == player.game)
                    .where(Card.original_player == None)
                    .where(Card.affinity_towards == None)
                    .where(Card.bias_against == None)
                    .where(Card.fake == True) 
                    .where(Card.faked_by == None)
                    .where(Card.tgb <= tgb) 
                    .first()
                )
        else:
            # draw TRUE card
            if should_draw_affinity:
                card = (Card.select()
                    .where(Card.game == player.game)
                    .where(Card.original_player == None)
                    .where(Card.affinity_towards != None)
                    .where(Card.fake == False) 
                    .where(Card.tgb <= tgb)
                    .first()
                )
            if should_draw_topical:
                card = (Card.select()
                    .where(Card.game == player.game)
                    .where(Card.original_player == None)
                    .where(Card.affinity_towards == None)
                    .where(Card.bias_against == None) 
                    .where(Card.fake == False)
                    .where(Card.tgb <= tgb)
                    .first() 
                )
    
    if not card:
        card = (Card.select()
            .where(Card.game == player.game)
            .where(Card.original_player == None)
            .where(Card.tgb < tgb)            
            .first()
        )
    return card.draw(player)
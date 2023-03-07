import json
import random
from time import sleep

with open('cards_data.json') as json_file:
    data = json.load(json_file)
    # print(data)


def without_keys(d, keys):
    return {x: d[x] for x in d if x not in keys}

def deck_generator_alpha(data, tgb):

    print("Total Global Bias: " + str(tgb))

    bias_cards = []
    non_bias_cards = []
    for card in data:
        if 'bias_against' in card:
            bias_cards.append(card)
        else:
            non_bias_cards.append(card)
        

    # print(len(bias_cards))
    # print(len(non_bias_cards))
    
    if (tgb<15):
        bias_p = random.uniform(0,1) # variable to decide the probability of bias card being drawn
        if bias_p <= 0.2: 
            drawn_card = random.choice(bias_cards)
            print(json.dumps(drawn_card, indent = 4))
            tgb = tgb + 1
            # sleep(7)
            deck_generator_alpha(data, tgb)
            
            
        else:
            fake_p = random.uniform(0,1) # variable to decide the probability of fake description appearing
            drawn_card = random.choice(non_bias_cards)
            if fake_p < (tgb/15):
                drawn_card = drawn_card['fakes'][0]
                print(json.dumps(drawn_card, indent = 4))
                tgb = tgb + 1
                # sleep(7)
                deck_generator_alpha(data, tgb)
                
            else: 
                drawn_card = without_keys(drawn_card, {"fakes"})
                print(json.dumps(drawn_card, indent = 4))
                # sleep(7)
                deck_generator_alpha(data, tgb)
                

deck_generator_alpha(data, 0)
            



        

    
    



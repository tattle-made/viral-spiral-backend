# Deck Generators

Rundowns of the scripts present in this folder

## First

The script `first.py` is where the primary card selection logic exists right now. The script has a function called `draw`. This function takes in a player as its input and draws a new card for that player. We take the current total global bias and store it in the `tgb` variable. Next, we put a random value between 0 and 1 into the "bias_p"  variable. If the value of this variable is less than 0.2 we draw a bias card. Thus a bias card is drawn with 20% probability. (Subject to change)

With 80% probability we either draw a TOPICAL (factual card) or AFFINITY (related to some topic) card. The decision of whether or not to draw a topical or affinity card is done in the following code block:

```
should_draw_affinity = random.uniform(0,1) < 0.5
should_draw_topical = not should_draw_affinity
```

This ensures that both are drawn with a 50% probability. 

Next, we have a variable called `fake_p` whose value is randomly set between 0 and 1. The new logic for drawing the fake versions of the topical and affinity cards dictates that the probability of drawing a fake version is directly proportional to the current tgb. Thus, if the value of fake_p is less than tgb/(Maximum value of TGB) then we pass the fake version. This implies that the probability of drawing a fake topical or affinity card is `tgb/(Maximum value of TGB)`. Thus it increases as a function of the tgb. 

Update: The script now uses the tgb variable in order to increase the draw pool as the game goes on. So the cards that are being drawn currently need to have their tgb parameter less than the current tgb, except for bias card that have a larger range for `tgb`. This can be seein in the following line of code: 

```
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
```
If no card that matches the current conditions then the script draws any card who tgb value is less than the current tgb. 


## Deck Generator Alpha

Outputs a sequence of cards based on the new logic, which works as a function of the total global bias (`tgb`). Use the following command to run the code: 

```
pipenv shell
python deck-generator-alpha.py | tee output.txt
```

The `output.txt` file should then have an a sequence of the cards, ending at total global bias 15. 

By default this script divides the cards into bias cards and non bias cards. Bias cards are the ones which have a bias against a community of particular colored shirts. Non bias cards are the remaining. With a given probability it (currently 20%) it presents bias cards. Moreover whenever a non-bias card is displayed, the probability of the information on it being fake is: `tgb`/15. The script assumes that all the cards are passed atleast once and thus whenever a bias card or a fake information card appears the value of `tgb` goes up by 1. 

 

 v0.0.1
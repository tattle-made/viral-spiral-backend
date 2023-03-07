# Deck Generators

Rundowns of the scripts present in this folder

## First

The `first.py` script uses the logic of the `storyline` variable in order to generate a deck using the properties and class methods of the `Card` model from the `models` folder. It generates a deck based on the game name, player name and ensures dynamically that the total global bias (`tgb`) value that is hardcoded in a particular card is less than the current value of `tgb`. Then it orders the deck by its index in the storyline and passes the card to the `draw` method of `Card`. 

## Deck Generator Alpha

Outputs a sequence of cards based on the new logic, which works as a function of the total global bias (`tgb`). Use the following command to run the code: 

```
pipenv shell
python deck-generator-alpha.py | tee output.txt
```

The `output.txt` file should then have an a sequence of the cards, ending at total global bias 15. 

By default this script divides the cards into bias cards and non bias cards. Bias cards are the ones which have a bias against a community of particular colored shirts. Non bias cards are the remaining. With a given probability it (currently 20%) it presents bias cards. Moreover whenever a non-bias card is displayed, the probability of the information on it being fake is: `tgb`/15. The script assumes that all the cards are passed atleast once and thus whenever a bias card or a fake information card appears the value of `tgb` goes up by 1. 
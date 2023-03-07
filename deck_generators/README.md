# Deck Generators

Rundowns of the scripts present in this folder

## First

The `first.py` script uses the logic of the `storyline` variable in order to generate a deck using the properties and class methods of the `Card` model from the `models` folder. It generates a deck based on the game name, player name and ensures dynamically that the total global bias (`tgb`) value that is hardcoded in a particular card is less than the current value of `tgb`. Then it orders the deck by its index in the storyline and passes the card to the `draw` method of `Card`. 
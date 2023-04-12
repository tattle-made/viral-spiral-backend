# Prerequisite
# Modify constants.py and set FAKE_NEWS_BIAS_COUNT to -1

from models import (
    Game,
    Player,
    Card,
    CardInstance,
    Score,
    FullRound,
    PlayerPower,
    utils,
)
from main_loop import websocket
from random import random
from itertools import filterfalse

# Create Game
for progress in Game.new(
    player_count=4,
    colors_filepath="config_jsons/example1/colors.json",
    topics_filepath="config_jsons/example1/topics.json",
    password="asdf",
    draw_fn_name="first",
    cards_filepath="config_jsons/example1/cards.json",
    encyclopedia_filepath="config_jsons/example1/articles.json",
):
    if progress["type"] == "message":
        print(progress["payload"])
    if progress["type"] == "result":
        game = progress["payload"]

print("Game Created : ", game.name)

playernames = ["adhiraj", "aman", "krys", "farah"]
players = game.player_set

# join game
for name in playernames:
    player = game.get_unclaimed_player(name)
    player.name = name
    Score.initialize(game, player)
    player.save()


full_round = FullRound.create(game=game)
players = [player for player in players]
ordered_players = sorted(players, key=lambda player: player.sequence)


current_player = ordered_players[0]
current_player.current = True
current_player.save()
game.update_powers()


for player in ordered_players:
    print(player.name, player.sequence, player.current)

# draw a card
card_instance = game.draw(current_player, full_round=full_round)
if not card_instance:
    raise Exception("Out of cards!")
print(card_instance.card.fake, card_instance.card.description)
cardId = card_instance.card.id_
cardInstanceId = card_instance.id_
fakeCardCount = len(card_instance.card.fakes)
if fakeCardCount != 0:
    fakeCardId = card_instance.card.fakes[0].id_
else:
    raise Exception("No fake card present")

game.update_powers()

recipients = [rec.name for rec in card_instance.allowed_recipients()]
allowed_actions = current_player.allowed_actions(card_instance)


print("card Id : ", cardId)
print("card instance id : ", cardInstanceId)
print("fake card count : ", fakeCardCount)
print("fake card id : ", fakeCardId)
print("recipients : ", recipients)
print("allowed actions : ", allowed_actions)

print(card_instance.card.fake, card_instance.card.description)

# invoke turn to fake power
new_card_instance = current_player.action_fake_news(card_instance, fakeCardId)
print(new_card_instance.get("card").get("description"))
print(new_card_instance.get("card").get("affinity_towards").get("name"))
print(new_card_instance.get("card").get("affinity_count"))
print(new_card_instance.get("card").get("bias_against"))

# pass to next player

# assert everyone's score

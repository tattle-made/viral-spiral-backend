"""Prints all player details as a CSV"""

from io import StringIO
import os
import csv
from models import Player, Game

GAME_NAME = os.getenv("GAME")
OUTPUT = os.getenv("OUTPUT")

output = open(OUTPUT, "w")
writer = csv.writer(output)


game = Game.select().where(Game.name == GAME_NAME).first()

rows = []

for player in game.player_set:
    player_dict = {
        "name": player.name,
        "id": player.id_,
    }
    player_dict.update(player.all_affinities())
    player_dict.update(player.all_biases())
    rows.append(player_dict)

first = rows[0]

writer.writerow(first.keys())
writer.writerows([r.values() for r in rows])

output.close()

import unittest
from models import Game, Card, PlayerCardQueue, AffinityTopic, Color, Score


def create_new_game():
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
    return game


def join_game(game, player_name):
    player = game.get_unclaimed_player(player_name)
    player.name = player_name
    Score.initialize(game, player)
    player.save()


"""
todo : 
after a few cards have been passed around, get every player's queue and confirm the cards look right
invoke viral spiral and check the receiver's card queue looks right
"""

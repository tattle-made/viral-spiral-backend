import unittest
from models import (
    Game,
    Card,
    PlayerCardQueue,
    AffinityTopic,
    Color,
    Score,
    FullRound,
    Player,
)
import random
from time import sleep
from deck_generators import GENERATORS

draw_func = GENERATORS["first"]


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


def whose_turn_is_it(game):
    players = game.player_set
    ordered_players = sorted(players, key=lambda player: player.sequence)
    return ordered_players[0]


def draw_true_topical_card(game, player, tgb_threshold):
    card = (
        Card.select()
        .where(Card.game == game)
        .where(Card.original_player == None)
        .where(Card.affinity_towards == None)
        .where(Card.bias_against == None)
        .where(Card.fake == False)
        .where(Card.tgb <= tgb_threshold)
        .first()
    )
    card_instance = card.draw(player)
    return card_instance


def draw_random_card(game, player, tgb_threshold):
    card = (
        Card.select()
        .where(Card.game == game)
        .where(Card.original_player == None)
        .where(Card.tgb <= tgb_threshold)
        .first()
    )
    card_instance = card.draw(player)
    return card_instance


def init_fullround(game):
    full_round = FullRound.create(game=game)
    return full_round


def make_player_current(game, player):
    player.current = True
    player.save()
    game.update_powers()


def player_map_by_name(game):
    players_by_name = {}
    players = game.player_set
    for player in players:
        players_by_name[player.name] = player

    return players_by_name


def init():
    print("creating game")
    game = create_new_game()

    print("players join game")
    join_game(game, "adhiraj")
    join_game(game, "aman")
    join_game(game, "farah")
    join_game(game, "krys")
    players = player_map_by_name(game)
    return (game, players)


def begin_fullround(game):
    full_round = init_fullround(game)
    current_player = whose_turn_is_it(game)
    card_inst = draw_true_topical_card(game, current_player, 4)
    # make_player_current(game, current_player)
    return (full_round, current_player, card_inst)



def main():
    (game, players) = init()
    adhiraj = players["adhiraj"]
    aman = players["aman"]
    farah = players["farah"]
    krys = players["krys"]

    print(game)
    tgb = 2

    for i in range(25):
        print("START OF ROUND")

        full_round = init_fullround(game)
        ordered_players = sorted(game.player_set, key=lambda player: player.sequence)

        for player in ordered_players:
            print("\tSTART OF ", player.name, "'s TURN. tgb: ", game.total_global_bias())
            sleep(3)
            game.add_round(full_round=full_round)
            Player.update(current=False).where(Player.game == game).execute()
            Player.update(sequence=Player.sequence + 100, current=True).where(
                Player.id_ == player.id_
            ).execute()
            card_inst = draw_func(player)
            print('\t\t\t\t\tdrawn card', card_inst.card.description)
            print("\tEND OF ", player.name, "'s TURN")

            card_holder = player
            current_card_instance = card_inst

            others = filter(lambda p: p != player, ordered_players)
            print("starting %s's round" % (player.name))
            print("card is in %s's hand" % (card_holder.name))
            for other in others:
                sleep(1)
                should_keep = True if random.uniform(0,1) < 0.2 else False
                if should_keep:
                    print(
                        "keeping card instance",
                        current_card_instance,
                        "with",
                        card_holder.name,
                    )
                    card_holder.action_keep_card(
                        card_instance_id=current_card_instance.id_
                    )
                    break
                else:
                    print(
                        card_holder.name,
                        "passing",
                        current_card_instance,
                        " to ",
                        other.name,
                    )
                    card_holder.action_pass_card(
                        card_instance=current_card_instance, to_player=other
                    )
                    card_holder = other
                    current_card_instance = other.card_instances_in_hand()[0]
                    # print("new card instance ", current_card_instance)

            game.update_powers()
            game.save()
        print("END OF ROUND")
    return (game, adhiraj, aman, farah, krys)
    # return (game, players, adhiraj, aman, farah, krys, ordered_players, current_player)


main()

"""
todo : 
after a few cards have been passed around, get every player's queue and confirm the cards look right
invoke viral spiral and check the receiver's card queue looks right

bug : 
why does the full round always start with farah

"""

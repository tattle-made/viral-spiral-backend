"""Main loop using the terminal"""

from typing import Callable
from models import Game, Player, CardInstance
from main_loop.base import GameRunner

from deck_generators.first import draw


class ConsoleGameRunner(GameRunner):

    def invoke_player_action(self, player: Player, card_instance: CardInstance):
        """Prompts the player to do something"""
        print(f"Player {player.name} - your turn to act. What do you want to do?")
        print("Allowed actions", player.allowed_actions(card_instance))
        action = input()
        player.perform_action(action)


if __name__ == "__main__":
    game = Game.new(
        name="helloworld",
        players=["rishav", "denny"],
        colors=["red", "blue"],
        topics=["cats", "stocks"],
    )
    gr = ConsoleGameRunner(game=game, draw_fn=draw)
    gr.loop()

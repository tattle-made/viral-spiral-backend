"""Main loop using the terminal"""

from typing import Callable
from models import Game, Player, CardInstance


class GameRunner:
    def __init__(self, game: Game, draw_fn: Callable):
        self.game = game
        self.players = Player.select().where(Player.game == game).all()
        self.draw_fn = draw_fn

    def ask_do_sync(self, player: Player, card_instance: CardInstance):
        """Prompts the player to do something"""
        print(f"Player {player.name} - your turn to act. What do you want to do?")
        print("Allowed actions", player.allowed_actions(card_instance))
        action = input()
        action_fn = getattr(player, action, None)
        if not action_fn:
            print("Invalid input")
            return self.ask_do_sync(player, card_instance)
        action_fn()

    def do_round(self, player: Player):
        """Performs a round in `game` with `player` drawing a card"""
        card_instance = self.draw_fn(player)
        for player in self.players:
            if (card_instance := player.get_queued_card_instance()) is not None:
                self.ask_do_sync(player, card_instance)

    def loop(self):
        while self.game.active():
            for player in self.players:
                self.do_round(player)
                self.game.rounds += 1
                self.game.save()

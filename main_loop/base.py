"""Abstract class for main loop"""

from abc import ABC, abstractmethod
from typing import Callable
from models import Game, Player, CardInstance


class GameRunner(ABC):
    def __init__(self, game: Game, draw_fn: Callable):
        self.game = game
        self.name = game.name
        self.players = Player.select().where(Player.game == game).all()
        self.draw_fn = draw_fn

    def invoke_player_action(self, player: Player, card_instance: CardInstance):
        """If this is a synchronous game runner - like a console based, ask the
        player to do something here. If it is an event based game runner - like
        a web server, no need to do anything here"""
        pass

    def do_round(self, drawing_player: Player):
        """Performs a round in `game` with `drawing_player` drawing a card"""
        card_instance = self.draw_fn(drawing_player)
        # Finish this
        while True:
            queued = [player.get_queued_card_instance() for player in self.players]
            pending = any([bool(ci) for ci in queued])
            done = True
            for player in self.players:
                if (card_instance := player.get_queued_card_instance()) is not None:
                    self.invoke_player_action(player, card_instance)
                    done = False
            if done:
                break

    def exit(self):
        """Run any exit operations if you want"""
        pass

    def loop(self):
        while self.game.active():
            for player in self.players:
                self.do_round(player)
                self.game.rounds += 1
                self.game.save()
        self.exit()

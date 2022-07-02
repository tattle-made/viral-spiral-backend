"""Abstract class for main loop"""

import logging
import sys
import time
from abc import ABC, abstractmethod
from typing import Callable
from models import Game, Player, CardInstance


class GameRunner(ABC):
    def __init__(self, game: Game, logger: logging.Logger = None):
        self.game = game
        self.default_log_formatter = logging.Formatter(
            f"{self.name} : %(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        if logger:
            self.logger = logger
            for handler in self.logger.handlers:
                handler.setFormatter(self.default_log_formatter)
        else:
            self.logger = logging.Logger(name=self.name, level=logging.INFO)
            handler = logging.StreamHandler(stream=sys.stdout)
            handler.setFormatter(self.default_log_formatter)
            self.logger.addHandler(handler)

    @property
    def name(self):
        return self.game.name

    @property
    def players(self):
        return Player.select().where(Player.game == self.game)

    def invoke_player_action(self, player: Player, card_instance: CardInstance):
        """If this is a synchronous game runner - like a console based, ask the
        player to do something here. If it is an event based game runner - like
        a web server, no need to do anything here"""
        pass

    def finish_round(self, drawing_player: Player):
        """Invokes actions and waits until no cards are queued"""
        while True:
            if not self.game.active():
                self.logger.info("Game has ended")
                return
            self.logger.info("Looping")
            time.sleep(0.1)
            done = True
            for player in self.players:
                if (card_instance := player.get_queued_card_instance()) is not None:
                    self.invoke_player_action(player, card_instance)
                    done = False
            if done:
                Player.update(sequence=Player.sequence + 100).where(
                    Player.id_ == drawing_player.id_
                )
                break

    def do_round(self, drawing_player: Player):
        """Performs a round in `game` with `drawing_player` drawing a card"""
        self.finish_round(drawing_player)  # Finish any older rounds
        card_instance = self.game.draw(drawing_player)
        self.finish_round(drawing_player)

    def exit(self):
        """Run any exit operations if you want"""
        pass

    def loop(self):
        while self.game.active():
            for player in self.players.order_by(Player.sequence):
                self.do_round(player)
                self.game.rounds += 1
                self.game.save()
        self.exit()

"""Abstract class for main loop"""

import logging
import sys
from abc import ABC, abstractmethod
from typing import Callable
from models import db, Game, Player, CardInstance, CancelStatus, CancelVote, FullRound
from constants import CANCELLING_ALLOW_POLL


class GameRunner(ABC):
    def __init__(self, game: Game, socketio=None, logger: logging.Logger = None):
        self.game = game
        self.socketio = socketio
        game.runner = self
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

    def invoke_vote(self, player: Player, pending_vote: CancelVote):
        """Ask the player to vote for/against cancellation"""
        pass

    def finish_round(self, drawing_player: Player):
        """Invokes actions and waits until no cards are queued"""
        # If this player is pending cancellation punishment then skip them
        if CancelStatus.cancelled(drawing_player):
            print(str(drawing_player) + " was cancelled")
            # update the sequence of players regardless of the player being cancelled for the turn order to be maintained
            Player.update(sequence=Player.sequence + 100, current=True).where( 
                Player.id_ == drawing_player.id_ 
            ).execute()
            return False

        while True:
            # First send out the heartbeat
            self.game.heartbeat()

            logging.info("doing round")
            self.game.update_powers()
            if not self.game.active():
                self.logger.info("Game has ended")
                return False # See if False is indeed needed for game end (needs to be checked)
            # self.logger.info("Looping")
            done = True
            with db:
                for player in self.players.iterator():
                    # TODO see if you can optimise this in a single query
                    if (card_instance := player.get_queued_card_instance()) is not None:
                        self.invoke_player_action(player, card_instance)
                        done = False
                    if ((pending_vote := player.get_pending_cancel_vote()) is not None) and CANCELLING_ALLOW_POLL:
                        self.invoke_vote(player, pending_vote)
                        done = False
                    # TODO see if you really need to update powers after each turn
                    # self.game.update_powers()
            if done:
                break
            self.socketio.sleep(1)
        
        return True

    def do_round(self, drawing_player: Player, full_round: FullRound):
        """Performs a round in `game` with `drawing_player` drawing a card"""
        flag = self.finish_round(drawing_player)  # Finish any older rounds
        # -- this checks to see if this player has any already queued card instance
        # if yes, then they will get a turn and the game will wait till that player takes an action with it
        # this card instance is assigned at the previous round when the below code runs
        if flag:
            with db:
                card_instance = self.game.draw(drawing_player, full_round=full_round)
                if not card_instance:
                    raise Exception("Out of cards!")
            self.finish_round(drawing_player)

    def exit(self):
        """Run any exit operations if you want"""
        pass

    def loop(self):
        while self.game.active() and not self.game.started():
            # All players have not joined
            self.socketio.sleep(1)
            # Send the heartbeat
            self.game.heartbeat()
            # TODO add a timeout of 5 minutes
            continue

        while self.game.active():
            with db:
                idx = 0
                full_round = FullRound.create(game=self.game)
                players = [player for player in self.players]
                ordered_players = sorted(players, key=lambda player: player.sequence)
                
            for player in ordered_players:
                # Re fetch the player once
                player = self.players.select().where(Player.id_ == player.id_).first()
                self.do_round(player, full_round)
                # if idx == 10:
                #     self.game.save()
                #     idx = 0
                # idx += 1
                self.game.save()

        self.exit()

    @classmethod
    def send_to_player(cls, player: Player, data: dict = None, event: str = None):
        """Send a message to a player"""
        pass

    @classmethod
    def send_to_game(cls, game: Game, data: dict = None, event: str = None):
        """Send a message to all players in the game"""
        pass

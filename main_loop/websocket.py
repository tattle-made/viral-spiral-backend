import eventlet

eventlet.monkey_patch()
import logging
import inspect
import json
import sys
import os
import pickle
from functools import wraps
from datetime import datetime, timezone
from queue import Queue
from threading import Lock, Thread
from flask import Flask, render_template, session, request, copy_current_request_context
from flask_socketio import (
    SocketIO,
    emit,
    send,
    join_room,
    leave_room,
    close_room,
    rooms,
    disconnect,
)
from models.utils import model_to_dict
import cProfile
import sys
from models import Score

from constants import GAME_CREATION_TOTAL_TRIES
from models import Game, Player, Card, CardInstance, CancelVote, FullRound, db
from models.messages import (
    ERROR_GENERIC,
    HEARTBEAT,
)

from main_loop.base import GameRunner

root_logger = logging.getLogger("root")

# Set this variable to "threading", "eventlet" or "gevent" to test the
# different async modes, or leave it set to None for the application to choose
# the best option based on installed packages.
async_mode = None

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET")
socketio = SocketIO(
    app,
    async_mode=async_mode,
    cors_allowed_origins="*",
    logger=root_logger,
    log_output=True,
)
thread = None
thread_lock = Lock()
DEBUG = os.getenv("DEBUG", "no") == "yes"


# Set the logger
class SocketHandler(logging.StreamHandler):
    def emit(self, record):
        # TODO check level, request.message
        msg = self.format(record)
        if record.levelno >= logging.ERROR:
            try:
                socketio.emit(
                    ERROR_GENERIC.name,
                    {
                        "original_request": request.event,
                        "error": msg,
                    },
                    to=request.sid,
                )
            except (RuntimeError, TypeError) as exc:
                print(exc)
                pass


root_logger.setLevel(os.getenv("LOG_LEVEL", "INFO"))
root_logger.addHandler(SocketHandler())
root_logger.addHandler(logging.StreamHandler(sys.stdout))


class UniqueQueue(Queue):
    def __init__(self, *args, **kwargs):
        self._set = set()
        super().__init__(*args, **kwargs)

    def put(self, d):
        if d not in self._set:
            super().put(d)
            self._set.add(d)

    def get(self):
        retval = super().get()
        self._set.remove(retval)
        return retval


class WebsocketGameRunner(GameRunner):
    background_tasks = {}
    max_games = 3

    def __init__(self, *args, name: str = None, **kwargs):
        self.thread = None
        super().__init__(*args, **kwargs)

    @classmethod
    def send_to_game(cls, game: Game, data=None, event="text_response"):
        json.dumps(data)  # If data isn't json dumpable, raise the error here
        logging.info(f"Emmitting to game {game.name} - event {event}")
        socketio.emit(event, {"data": data}, to=game.name)

    @classmethod
    def send_to_player(cls, player: Player, data=None, event="text_response"):
        json.dumps(data)  # If data isn't json dumpable, raise the error here

        if player.client_id:
            logging.info(
                f"Emmitting to player {player.name} - event {event} | game"
                f" {player.game.name}"
            )
            socketio.emit(event, {"data": data}, to=player.client_id)

    def invoke_player_action(self, player: Player, card_instance: CardInstance):
        self.send_to_player(
            player,
            {
                "card_instance": model_to_dict(card_instance),
                "recipients": [rec.name for rec in card_instance.allowed_recipients()],
                "allowed_actions": player.allowed_actions(card_instance),
                "valid_topics_for_cancel": [
                    model_to_dict(topic) for topic in player.valid_topics_for_cancel()
                ],
            },
            event="play_card",
        )
        # self.send_to_game(self.game, {"player_name": player.name}, event="whos_turn")

    def invoke_vote(self, player: Player, pending_vote: CancelVote):
        self.send_to_player(
            player,
            {"pending_vote": model_to_dict(pending_vote)},
            event="vote_cancel",
        )

    def do_round(self, drawing_player: Player, full_round: FullRound):
        """Sleeps socket things"""
        socketio.sleep(1)
        self.send_to_game(
            self.game,
            {
                "drawing_player": model_to_dict(drawing_player),
            },
            event="round_start",
        )
        super().do_round(drawing_player, full_round)
        self.send_to_game(
            self.game,
            {
                "drawing_player": model_to_dict(drawing_player),
            },
            event="round_end",
        )

    def loop_async(self):
        """Runs the loop function in a thread"""
        self.thread = socketio.start_background_task(target=self.loop)
        self.background_tasks[self.name] = self

    def exit(self):
        self.game.end()
        self.send_to_game(self.game, None, "endgame")
        if self.name in self.background_tasks:
            self.background_tasks.pop(self.name)
        try:
            close_room(self.name)
        except RuntimeError as exc:
            logging.error("Failed to close room: %s", str(exc))
            pass

    def perform_action(self, player_name, action, **kwargs):
        player = self.game.player_set.where(Player.name == player_name).get()
        result = player.perform_action(action, **kwargs)
        self.send_to_game(
            self.game,
            {
                "action": action,
                "player": model_to_dict(player),
                "result": result,
            },
            "action_performed",
        )
        return result

    def get_queued_card(self, player_name):
        player = self.game.player_set.where(Player.name == player_name).get()
        if card_instance := player.get_queued_card_instance():
            return card_instance.card

    @classmethod
    def get_by_game(cls, game: Game):
        """Returns a game runner obj given a Game obj"""
        # Failsafe - in case this is called for an in-memory game
        if cls.background_tasks.get(game.name):
            return cls.get_by_name(game.name)

        runner = cls(game=game, socketio=socketio)
        runner.loop_async()
        return runner

    @classmethod
    def get_by_name(cls, name: str):
        """Returns a game runner obj given a Game name"""
        if runner := cls.background_tasks.get(name):
            if runner.thread.is_alive():
                return runner
            else:
                cls.background_tasks.pop(name)
                del runner

        # Now load the game from the database, or create a new game
        game = Game.select().where(Game.name == name)
        if game.count() == 1:
            return cls.get_by_game(game.first())

    @classmethod
    def get(cls, name: str):
        """Loads an existing game"""
        runner = cls.get_by_name(name)
        if not runner:
            raise ValueError(f"No game found: {name}")
        return runner

    @classmethod
    def create(cls, **game_kwargs):
        """creates a game runner object"""
        for progress in Game.new(**game_kwargs):
            if progress["type"] == "message":
                yield progress
            if progress["type"] == "result":
                yield {
                    "type": "result",
                    "payload": cls.get_by_game(progress["payload"]),
                }


def password_auth(func):
    """Authenticates this request with the game password"""

    @wraps
    def authenticated(message):
        password = message["password"]
        game_name = message["game_name"]
        game = Game.select().filter(name=game_name).first()
        if game and game.password == password:
            return func(message)
        return {
            "status": 403,
            "error": "Invalid password",
        }


@app.route("/")
def index():
    """Renders the main page of the game"""
    return render_template("index.html", async_mode=socketio.async_mode)


@app.route("/health")
def health_check():
    """Returns an OK"""
    return "OK\n"


@socketio.event
def about_game(message):
    """Returns info about a game"""
    logging.info(
        f"Incoming event - {inspect.getframeinfo(inspect.currentframe()).function} |"
        f" {message}"
    )
    # TODO authenticate
    game_name = message["game"]
    runner = WebsocketGameRunner.get_by_name(game_name)
    if runner:
        return {
            "status": 200,
            "about": runner.game.about(),
        }
    else:
        return {"status": 404, "error": f"Game not found {game_name}"}


@socketio.event
def join_game(message):
    """Takes a player name and game name. Joins the game. The game needs
    to be created with another API"""
    logging.info(
        f"Incoming event - {inspect.getframeinfo(inspect.currentframe()).function} |"
        f" {message}"
    )
    game_name = message["game"]
    player_name = message["player"]
    runner = WebsocketGameRunner.get_by_name(game_name)
    if runner:
        player = runner.game.get_player_by_name(player_name=player_name)
        if not player:
            player = runner.game.get_unclaimed_player(player_name=player_name)
            if not player:
                return {"status": 403, "error": "No more players allowed"}
            player.name = player_name.strip().lower()
            Score.initialize(runner.game, player)
            player.save()

        if player.client_id == request.sid:
            return {"status": 200, "message": f"Already joined game {game_name}"}
        player.client_id = request.sid
        player.save()
        join_room(game_name)
        return {
            "status": 200,
            "about": runner.game.about(),
        }
    else:
        return {"status": 404, "error": f"Game not found {game_name}"}


@socketio.event
def player_hand(message):
    logging.info(
        f"Incoming event - {inspect.getframeinfo(inspect.currentframe()).function} |"
        f" {message}"
    )
    game_name = message["game"]
    player_id = message["player"]
    game = Game.select().where(Game.name == game_name)

    print("----")
    print(game.first().id_, player_id)
    print("----")

    cursor = db.execute_sql(
        """
        SELECT card.id_ as cid, cardinstance.id_ as ciid, card.description, card.image
        FROM card
        INNER JOIN cardinstance 
        ON cardinstance.card_id=card.id_
        WHERE cardinstance.id_ in (
            SELECT card_instance_id
            FROM playerhand
            WHERE game_id='"""
        + game.first().id_
        + "'AND player_id='"
        + player_id
        + "')"
    )

    cards = []

    for row in cursor.fetchall():
        cards.append(
            {
                "card_id": row[0],
                "card_instance_id": row[1],
                "title": row[2],
                "image": row[3],
            }
        )

    return {
        "status": 200,
        "hand": cards,
    }


@socketio.event
def create_game(message):
    """Creates a game"""
    logging.info(
        f"Incoming event - {inspect.getframeinfo(inspect.currentframe()).function} |"
        f" {message}"
    )

    emit("create_room:progress", "Creating Room")

    player_count = int(message["player_count"])
    colors_filepath = message["colors_filepath"]
    topics_filepath = message["topics_filepath"]
    password = message["password"]
    draw_fn_name = message["draw_fn_name"]
    cards_filepath = message["cards_filepath"]
    encyclopedia_filepath = message["encyclopedia_filepath"]

    try:
        for progress in WebsocketGameRunner.create(
            player_count=player_count,
            colors_filepath=colors_filepath,
            topics_filepath=topics_filepath,
            cards_filepath=cards_filepath,
            encyclopedia_filepath=encyclopedia_filepath,
            password=password,
            draw_fn_name=draw_fn_name,
        ):
            if progress["type"] == "message":
                emit("create_room:progress", progress)
                eventlet.sleep(0)
            if progress["type"] == "result":
                runner = progress["payload"]
                join_room(runner.name)
    except ValueError as exc:
        return {
            "status": 500,
            "error": str(exc),
        }

    return {
        "status": 200,
        "game": {"name": runner.name},
    }


@socketio.event
def load_game(message):
    """Loads a game"""
    logging.info(
        f"Incoming event - {inspect.getframeinfo(inspect.currentframe()).function} |"
        f" {message}"
    )
    game_name = message["game"]
    password = message["password"]
    runner = WebsocketGameRunner.get(game_name)
    if runner.game.password != password:
        return {
            "status": 401,
            "error": "incorrect password",
        }

    return {
        "status": 200,
        "game_name": runner.name,
    }


@socketio.event
def get_queued_card(message):
    """Get the state given a player"""
    logging.info(
        f"Incoming event - {inspect.getframeinfo(inspect.currentframe()).function} |"
        f" {message}"
    )
    game_name = message["game"]
    player_name = message["player"]
    runner = WebsocketGameRunner.get_by_name(game_name)
    if runner:
        card = runner.get_queued_card(player_name)
        if card:
            return {"status": 200, "card": model_to_dict(card)}
        return {
            "status": 200,
            "card": None,
            "message": "No card queued",
        }
    return {
        "status": 404,
        "error": "No game found {game_name}",
    }


@socketio.event
def player_action(message):
    logging.info(
        f"Incoming event - {inspect.getframeinfo(inspect.currentframe()).function} |"
        f" {message}"
    )
    game_name = message["game"]
    player_name = message["player"]
    action = message["action"]
    kwargs = message["kwargs"]
    runner = WebsocketGameRunner.get_by_name(game_name)
    if runner:
        response = runner.perform_action(player_name, action, **kwargs)
        return {
            "status": 200,
            "message": response,
        }
    else:
        return {"status": 404, "error": f"No game found {game_name}"}


@socketio.event
def disconnect_request():
    @copy_current_request_context
    def can_disconnect():
        disconnect()

    logging.info(
        f"Incoming event - {inspect.getframeinfo(inspect.currentframe()).function} |"
        f" {disconnect}"
    )
    session["receive_count"] = session.get("receive_count", 0) + 1
    # for this emit we use a callback function
    # when the callback function is invoked we know that the message has been
    # received and it is safe to disconnect
    emit(
        "text_response",
        {"data": "Disconnected!", "count": session["receive_count"]},
        callback=can_disconnect,
    )


@socketio.event
def my_ping(message=None):
    logging.info(
        f"Incoming event - {inspect.getframeinfo(inspect.currentframe()).function} |"
        f" {message}"
    )
    emit("my_pong", message)
    return message


@socketio.event
def my_echo(message):
    logging.info(
        f"Incoming event - {inspect.getframeinfo(inspect.currentframe()).function} |"
        f" {message}"
    )
    message["echo"] = True
    emit("text_response", message)


@socketio.event
def connect(message=None):
    logging.info(
        f"Incoming event - {inspect.getframeinfo(inspect.currentframe()).function} |"
        f" {message}"
    )
    return {
        "status": 200,
        "message": "Connected",
    }


@socketio.on("disconnect")
def test_disconnect():
    print("Client disconnected", request.sid)
    # set player.client_id to NULL for this sid
    player = Player.select().where(Player.client_id == request.sid).first()
    if player is not None:
        player.client_id = None
        player.save()


@socketio.on_error()
def error_handler(exc):
    # Let our custom logger handle things
    logging.exception(exc)


def run():
    socketio.run(app, host="0.0.0.0", port=5000)


if __name__ == "__main__":
    run()

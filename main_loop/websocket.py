import json
import os
import pickle
from queue import Queue
from threading import Lock, Thread
from flask import Flask, render_template, session, request, copy_current_request_context
from flask_socketio import (
    SocketIO,
    emit,
    join_room,
    leave_room,
    close_room,
    rooms,
    disconnect,
)
from models.utils import model_to_dict

from models import Game, Player, Card, CardInstance, CancelVote

from main_loop.base import GameRunner

# Set this variable to "threading", "eventlet" or "gevent" to test the
# different async modes, or leave it set to None for the application to choose
# the best option based on installed packages.
async_mode = None

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET")
socketio = SocketIO(app, async_mode=async_mode)
thread = None
thread_lock = Lock()


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
    max_games = 3  # Allow maximum of 3 games to run in parallel
    emit_queue = UniqueQueue()

    def __init__(self, *args, name: str = None, **kwargs):
        self.thread = None
        super().__init__(*args, **kwargs)

    @classmethod
    def flush_emit_queue(cls):
        while cls.emit_queue.qsize() > 0:
            pickled = cls.emit_queue.get()
            obj = dict(pickle.loads(pickled))
            socketio.emit(*obj["args"], **obj["kwargs"])

    @classmethod
    def emit_async(cls, *args, **kwargs):
        """Enqueues the message for emitting"""
        the_dict = {"args": args, "kwargs": kwargs}
        pickled = pickle.dumps(sorted(the_dict.items()))
        cls.emit_queue.put(pickled)

    @classmethod
    def send_to_game(cls, game: Game, data=None, event="text_response"):
        json.dumps(data)  # If data isn't json dumpable, raise the error here
        cls.emit_async(
            event,
            {"data": data},
            to=game.name,
        )

    @classmethod
    def send_to_player(cls, player: Player, data=None, event="text_response"):
        json.dumps(data)  # If data isn't json dumpable, raise the error here
        if player.client_id:
            cls.emit_async(event, {"data": data}, to=player.client_id)

    @classmethod
    def send_reply(cls, data=None, event="text_response"):
        json.dumps(data)  # If data isn't json dumpable, raise the error here
        cls.emit_async(event, {"data": data}, to=request.sid)

    def invoke_player_action(self, player: Player, card_instance: CardInstance):

        self.send_to_player(
            player,
            {
                "card_instance": model_to_dict(card_instance),
                "recipients": [rec.name for rec in card_instance.allowed_recipients()],
            },
            event="play_card",
        )
        self.send_to_game(self.game, {"player_name": player.name}, event="whos_turn")

    def invoke_vote(self, player: Player, pending_vote: CancelVote):

        self.send_to_player(
            player,
            {"pending_vote": model_to_dict(pending_vote)},
            event="vote_cancel",
        )

    def do_round(self, *args, **kwargs):
        """Sleeps socket things"""
        socketio.sleep(1)
        super().do_round(*args, **kwargs)
        self.send_to_game(self.game, "Finished a round")

    def loop_async(self):
        """Runs the loop function in a thread"""
        self.thread = Thread(target=self.loop)
        self.thread.start()
        self.background_tasks[self.name] = self

    def exit(self):
        self.send_to_game(self.game, None, "endgame")
        if self.name in self.background_tasks:
            self.background_tasks.pop(self.name)
        close_room(self.name)

    def perform_action(self, player_name, action, **kwargs):
        player = self.game.player_set.where(Player.name == player_name).get()
        player.perform_action(action, **kwargs)

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

        runner = cls(game=game)
        runner.loop_async()
        return runner

    @classmethod
    def get_by_name(cls, name: str):
        """Returns a game runner obj given a Game name"""
        if runner := cls.background_tasks.get(name):
            return runner

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
    def create(cls, name: str, **game_kwargs):
        """creates a game runner object"""
        if runner := cls.get_by_name(name):
            raise ValueError(f"Game already exists: {name}")

        # create a new game
        game = Game.new(name, **game_kwargs)
        return cls.get_by_game(game)


def background_thread():
    """Main Loop. Just sends an alive signal."""
    count = 0
    action_interval_secs = 2
    ticker_interval_secs = 10
    while True:
        socketio.sleep(0.1)
        count += 1
        if count % (ticker_interval_secs * 10) == 0:
            socketio.emit("text_response", {"data": "heartbeat", "count": count})
        if count % (action_interval_secs * 10) == 0:
            WebsocketGameRunner.flush_emit_queue()


@app.route("/")
def index():
    """Renders the main page of the game"""
    return render_template("index.html", async_mode=socketio.async_mode)


@socketio.event
def about_game(message):
    """Returns info about a game"""
    # TODO authenticate
    game_name = message["game"]
    runner = WebsocketGameRunner.get_by_name(game_name)
    if runner:
        runner.send_reply(runner.game.about(), event="about")
    else:
        WebsocketGameRunner.send_reply(f"Game not found {game_name}", event="about")


@socketio.event
def join_game(message):
    """Takes a player name and game name. Joins the game. The game needs
    to be created with another API"""
    game_name = message["game"]
    player_name = message["player"]
    runner = WebsocketGameRunner.get_by_name(game_name)
    if runner:
        player = runner.game.player_set.where(Player.name == player_name).get()
        if player.client_id == request.sid:
            runner.send_reply(f"Already joined game {game_name}")
        player.client_id = request.sid
        player.save()
        join_room(game_name)
        runner.send_reply(f"Joined game {game_name}")
    else:
        WebsocketGameRunner.send_reply(f"Game not found {game_name}")


@socketio.event
def create_game(message):
    """Creates a game"""
    game_name = message["game"]
    players = message["players"]
    colors_filepath = message["colors_filepath"]
    topics_filepath = message["topics_filepath"]
    password = message["password"]
    draw_fn_name = message["draw_fn_name"]
    cards_filepath = message["cards_filepath"]
    try:
        runner = WebsocketGameRunner.create(
            name=game_name,
            players=players,
            colors_filepath=colors_filepath,
            topics_filepath=topics_filepath,
            cards_filepath=cards_filepath,
            password=password,
            draw_fn_name=draw_fn_name,
        )
        emit("text_response", {"data": f"Created game: {runner.name}"})
    except ValueError as exc:
        emit("text_response", {"data": str(exc)})


@socketio.event
def load_game(message):
    """Loads a game"""
    game_name = message["game"]
    password = message["password"]
    try:
        runner = WebsocketGameRunner.get(game_name)
        if runner.game.password != password:
            emit("text_response", {"data": "Incorrect password"})
            return

        emit("text_response", {"data": f"Loaded game: {runner.name}"})
    except ValueError as exc:
        emit("text_response", {"data": str(exc)})


@socketio.event
def get_queued_card(message):
    """Get the state given a player"""
    game_name = message["game"]
    player_name = message["player"]
    runner = WebsocketGameRunner.get_by_name(game_name)
    if runner:
        card = runner.get_queued_card(player_name)
        if card:
            runner.send_reply(model_to_dict(card))
            return
        runner.send_reply("No card")
    WebsocketGameRunner.send_reply("No Game found")


@socketio.event
def player_action(message):
    game_name = message["game"]
    player_name = message["player"]
    action = message["action"]
    kwargs = message["kwargs"]
    runner = WebsocketGameRunner.get_by_name(game_name)
    if runner:
        runner.perform_action(player_name, action, **kwargs)
        data = {"message": f"Performed action {action}", "original_data": message}
        emit(
            "text_response",
            data,
            to=request.sid,
        )
    else:
        # TODO add original message here
        emit(
            "text_response",
            {"data": "Failed to perform {action}"},
            to=request.sid,
        )


@socketio.event
def disconnect_request():
    @copy_current_request_context
    def can_disconnect():
        disconnect()

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
def my_ping():
    emit("my_pong")


@socketio.event
def my_echo(message):
    message["echo"] = True
    emit("text_response", message)


@socketio.event
def connect():
    global thread
    with thread_lock:
        if thread is None:
            thread = socketio.start_background_task(background_thread)
    emit("text_response", {"data": "Connected"})


@socketio.on("disconnect")
def test_disconnect():
    print("Client disconnected", request.sid)


def run():
    socketio.run(app)


if __name__ == "__main__":
    run()

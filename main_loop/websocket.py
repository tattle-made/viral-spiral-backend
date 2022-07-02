import os
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
from playhouse.shortcuts import model_to_dict

from models import Game, Player, Card

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


class WebsocketGameRunner(GameRunner):

    background_tasks = {}
    max_games = 3  # Allow maximum of 3 games to run in parallel

    def __init__(self, *args, name: str = None, **kwargs):
        self.thread = None
        super().__init__(*args, **kwargs)

    def send_to_room(self, data=None):
        emit(
            "text_response",
            {"data": data},
            to=self.game.name,
        )
        print(self.game.name, data)

    @classmethod
    def send_to_player(cls, player: Player, data=None):
        emit("text_response", {"data": data}, to=player.client_id)

    @classmethod
    def send_reply(cls, data=None):
        emit("text_response", {"data": data}, to=request.sid)

    def do_round(self, *args, **kwargs):
        """Sleeps socket things"""
        socketio.sleep(1)
        super().do_round(*args, **kwargs)
        self.send_to_room("Finished a round")

    def loop_async(self):
        """Runs the loop function in a thread"""
        self.thread = Thread(target=self.loop)
        self.thread.start()
        self.background_tasks[self.name] = self

    def exit(self):
        self.thread.join()
        self.background_tasks.pop(self.name)
        close_room(self.name)

    def perform_action(self, player_name, action):
        player = self.game.player_set.where(Player.name == player_name).get()
        player.perform_action(action)

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
    while True:
        socketio.sleep(10)
        count += 1
        socketio.emit(
            "text_response", {"data": "Server generated event", "count": count}
        )


@app.route("/")
def index():
    """Renders the main page of the game"""
    return render_template("index.html", async_mode=socketio.async_mode)


@socketio.event
def join_game(message):
    """Takes a player name and game room name. Joins the game. The game needs
    to be created with another API"""
    game_name = message["game"]
    player_name = message["player"]
    runner = WebsocketGameRunner.get_by_name(game_name)
    if runner:
        player = runner.game.player_set.where(Player.name == player_name).get()
        if player.client_id == request.client_id:
            runner.send_reply(f"Already joined game {game_name}")
        player.client_id = request.client_id
        player.save()
        join_room(game_name)
        runner.send_reply(f"Joined game {game_name}")
    else:
        runner.send_reply(f"Room not found {game_name}")


@socketio.event
def create_game(message):
    """Creates a game"""
    game_name = message["game"]
    players = message["players"]
    colors = message["colors"]
    topics = message["topics"]
    password = message["password"]
    draw_fn_name = message["draw_fn_name"]
    cards_filepath = message["cards_filepath"]
    try:
        runner = WebsocketGameRunner.create(
            name=game_name,
            players=players,
            colors=colors,
            topics=topics,
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


@socketio.event
def player_action(message):
    game_name = message["game"]
    player_name = message["player"]
    action = message["action"]
    runner = WebsocketGameRunner.get_by_name(game_name)
    if runner:
        runner.perform_action(player_name, action)
        emit(
            "text_response",
            {"data": f"Performed action {action}"},
            to=request.sid,
        )
    else:
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
    emit("text_response", {"data": "Connected", "count": 0})


@socketio.on("disconnect")
def test_disconnect():
    print("Client disconnected", request.sid)


def run():
    socketio.run(app)


if __name__ == "__main__":
    run()
